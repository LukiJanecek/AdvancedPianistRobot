# services/ws_hub_service.py
import json, uuid, asyncio
from dataclasses import dataclass, replace 
from typing import Dict, Set, Optional
from fastapi import WebSocket
from dataclasses import replace

@dataclass(frozen=True, eq=True)
class Conn:
    ws: WebSocket
    client_id: str
    device: str
    role: str
    ip: str  

class RoomHub:
    def __init__(self):
        self.rooms: Dict[str, Set[Conn]] = {}
        self.lock = asyncio.Lock()

    async def join(self, room: str, c: Conn) -> bool:
        """
        Přidá klienta do místnosti.
        - Pokud chce vstoupit `performer` a už tam performer je, vrátí False (nepřidá).
        - Jinak přidá, provede ws.accept() a pošle presence a vrátí True.
        """
        async with self.lock:
            members = self.rooms.setdefault(room, set())

            # 1) Zákaz >1 performera (už máš)
            if c.role == "performer":
                if any(m.role == "performer" for m in members):
                    return False

            # 2) Zákaz více spojení se stejným device NEBO IP (můžeš si vybrat politiku)
            # aktuálně: podle device (co už máš) + navíc podle IP
            same_device_or_ip = [
                m for m in members
                if (m.device == c.device) or (m.ip == c.ip)  # <<< tady můžeš omezit jen na IP/jen na device
            ]

            for old in same_device_or_ip:
                try:
                    # pošli info starému spojení, že bude nahrazeno
                    await old.ws.send_text(json.dumps({
                        "type": "info",
                        "event": "replaced",
                        "reason": "same_device_or_ip",
                        "message": "Byl jsi odpojen, protože se připojilo nové spojení ze stejného zařízení/IP.",
                    }, separators=(",", ":")))
                except Exception:
                    pass
                try:
                    await old.ws.close(code=4400)
                except Exception:
                    pass
                members.discard(old)

            members.add(c)

        # Accept až po zapsání do struktury (aby presence viděla i jeho)
        await c.ws.accept()
        await self._presence(room)
        return True

    async def leave(self, room: str, c: Conn):
        async with self.lock:
            if room in self.rooms:
                self.rooms[room].discard(c)
                # Zjisti, jestli performer odešel
                performer_gone = c.role == "performer"
                if not self.rooms[room]:
                    del self.rooms[room]
                else:
                    # Pokud performer odešel, povyš jednoho watcher-a
                    if performer_gone:
                        for member in self.rooms[room]:
                            if member.role == "watcher":
                                # Změň roli na performer
                                upgraded = replace(member, role="performer")
                                self.rooms[room].discard(member)
                                self.rooms[room].add(upgraded)
                                try:
                                    await upgraded.ws.send_text(json.dumps({
                                        "type": "info",
                                        "event": "role_upgraded",
                                        "role": "performer",
                                        "message": "Byl jsi povýšen na performera.",
                                    }, separators=(",", ":")))
                                except Exception:
                                    pass
                                break
        await self._presence(room)

    async def send_room(self, room: str, msg: dict, skip: Optional[str] = None):
        # Snapshot příjemců (bez dlouhého držení locku během await send_text)
        async with self.lock:
            targets = list(self.rooms.get(room, []))

        text = json.dumps(msg, separators=(",", ":"))
        dead: list[Conn] = []

        for c in targets:
            if skip and c.client_id == skip:
                continue
            try:
                await c.ws.send_text(text)
            except Exception:
                dead.append(c)

        # Úklid mrtvých spojení
        for d in dead:
            await self.leave(room, d)

    async def _presence(self, room: str):
        async with self.lock:
            members_list = list(self.rooms.get(room, []))
            members = [
                {"client_id": c.client_id, 
                 "device": c.device, 
                 "role": c.role
                }

                for c in members_list
            ]
            has_performer = any(c.role == "performer" for c in members_list)
            watchers = sum(1 for c in members_list if c.role == "watcher")

        await self.send_room(room, {
            "type": "presence",
            "members": members,
            "has_performer": has_performer,
            "watchers": watchers
        })
    
    async def drop_all_performers(self) -> int:
        """
        Zavře všechna WebSocket spojení s rolí 'performer' ve všech místnostech.
        Vrací počet odpojených performerů.
        """
        performers: list[Conn] = []

        # 1) Nasbírat seznam performerů (bez close/await uvnitř locku)
        async with self.lock:
            for room, members in self.rooms.items():
                for c in list(members):
                    if c.role == "performer":
                        performers.append(c)

        # 2) Mimo lock – poslat zprávu a zavřít WS
        for c in performers:
            try:
                await c.ws.send_text(json.dumps({
                    "type": "info",
                    "event": "kicked",
                    "reason": "admin_drop_all_performers",
                    "message": "Byl jsi odpojen jako performer administrativním zásahem.",
                }, separators=(",", ":")))
            except Exception:
                pass

            try:
                # Zavření spojení – ve ws_endpoint to chytí WebSocketDisconnect
                # a v finally zavolá hub.leave(room, active_conn)
                await c.ws.close(code=4404)
            except Exception:
                pass

        return len(performers)

    # ------------------- NOVÁ FUNKCE: převzetí role performera -------------------
    async def force_takeover(self, room: str, new_performer_id: str) -> bool:
        """
        V dané místnosti `room` nastaví klienta s client_id == new_performer_id jako 'performer'.
        Dosavadní performer(y) se shodí na 'watcher'.
        Vrací True pokud se povedlo, False pokud místnost nebo client_id neexistuje.
        """
        async with self.lock:
            members = self.rooms.get(room)
            if not members:
                return False

            # najdi cílového klienta
            target = None
            for m in members:
                if m.client_id == new_performer_id:
                    target = m
                    break

            if target is None:
                return False  # client_id v místnosti není

            if target.role == "performer":
                # už performer je, jen pošleme presence mimo lock
                upgraded = target
                demoted: list[Conn] = []
                # drop lock a pošleme presence níž
            else:
                new_members: Set[Conn] = set()
                demoted: list[Conn] = []
                upgraded: Optional[Conn] = None

                for m in members:
                    if m.client_id == new_performer_id:
                        # upgradujeme na performera
                        upgraded = replace(m, role="performer")
                        new_members.add(upgraded)
                    elif m.role == "performer":
                        # původní performer -> watcher
                        dem = replace(m, role="watcher")
                        new_members.add(dem)
                        demoted.append(dem)
                    else:
                        new_members.add(m)

                if upgraded is None:
                    return False

                # přepíšeme obsah místnosti
                self.rooms[room] = new_members

        # --- Mimo lock pošleme info všem dotčeným a presence ---
        try:
            await upgraded.ws.send_text(json.dumps({
                "type": "info",
                "event": "role_changed",
                "role": "performer",
                "reason": "admin_takeover",
                "message": "Byl jsi nastaven jako performer (admin takeover).",
            }, separators=(",", ":")))
        except Exception:
            pass

        for d in demoted:
            try:
                await d.ws.send_text(json.dumps({
                    "type": "info",
                    "event": "role_changed",
                    "role": "watcher",
                    "reason": "admin_takeover",
                    "message": "Byl jsi přeřazen na watcher, protože jiný klient převzal roli performera.",
                }, separators=(",", ":")))
            except Exception:
                pass

        await self._presence(room)
        return True

hub = RoomHub()

def new_conn(ws: WebSocket, device: str, role: str, ip: str) -> Conn:
    return Conn(ws=ws, client_id=str(uuid.uuid4()), device=device, role=role, ip=ip)