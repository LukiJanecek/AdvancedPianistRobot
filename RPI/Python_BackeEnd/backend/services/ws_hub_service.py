# services/ws_hub_service.py
import json
import uuid
import asyncio
import time
from dataclasses import dataclass, replace
from typing import Dict, Set, Optional, List
from fastapi import WebSocket


@dataclass(frozen=True, eq=True)
class Conn:
    ws: WebSocket
    client_id: str
    device: str
    role: str
    ip: str
    last_activity: float = 0.0   # unix time poslední aktivity
    inactive: bool = False       # true = 15+ s bez zprávy


class RoomHub:
    INACTIVITY_TIMEOUT = 15  # sekund

    def __init__(self):
        self.rooms: Dict[str, Set[Conn]] = {}
        self.lock = asyncio.Lock()
        # per-client watchdog task pro performery
        self.activity_tasks: Dict[str, asyncio.Task] = {}

    # ---------- interní pomocné věci ----------

    async def _start_inactivity_watchdog(self, room: str, conn: Conn):
        """
        Spustí (nebo restartuje) watchdog pro daného performera.
        """
        # zruš starý task, pokud existuje
        old = self.activity_tasks.get(conn.client_id)
        if old:
            old.cancel()

        task = asyncio.create_task(self._watch_inactivity(room, conn.client_id))
        self.activity_tasks[conn.client_id] = task

    async def _stop_inactivity_watchdog(self, client_id: str):
        task = self.activity_tasks.pop(client_id, None)
        if task:
            task.cancel()

    async def _watch_inactivity(self, room: str, client_id: str):
        """
        Periodicky kontroluje aktivitu performera.
        Pokud 15+ s nic nepřišlo, nastaví inactive=True a zaloguje.
        Roli necháváme, jen flag.
        """
        try:
            while True:
                await asyncio.sleep(self.INACTIVITY_TIMEOUT)

                async with self.lock:
                    members = self.rooms.get(room)
                    if not members:
                        # místnost zanikla
                        return

                    current: Optional[Conn] = None
                    for m in members:
                        if m.client_id == client_id:
                            current = m
                            break

                    if not current:
                        # klient už tam není
                        return

                    # pokud už není performer, nemá smysl ho dál hlídat
                    if current.role != "performer":
                        return

                    now = time.time()
                    idle = now - current.last_activity

                    if idle >= self.INACTIVITY_TIMEOUT and not current.inactive:
                        # přepneme flag na inactive=True
                        new_members: Set[Conn] = set()
                        for m in members:
                            if m.client_id == client_id:
                                updated = replace(m, inactive=True)
                                new_members.add(updated)
                                print(
                                    f"[WS][{updated.ip}] Performer {updated.client_id} "
                                    f"je NEAKTIVNÍ (>{self.INACTIVITY_TIMEOUT}s bez zprávy)."
                                )
                            else:
                                new_members.add(m)
                        self.rooms[room] = new_members
                    # pokud je už inactive=True, jen dál běžíme; můžeme logovat jen jednou
        except asyncio.CancelledError:
            # watchdog ukončen (např. při odpojení)
            return

    async def mark_activity(self, room: str, client_id: str):
        """
        Zavolej vždy, když přijde zpráva od daného klienta.
        Pokud je performer, resetuje last_activity + inactive=False a restartuje watchdog.
        """
        async with self.lock:
            members = self.rooms.get(room)
            if not members:
                return

            new_members: Set[Conn] = set()
            updated_conn: Optional[Conn] = None

            now = time.time()

            for m in members:
                if m.client_id == client_id:
                    # reset activity (pro všechny role),
                    # performer navíc dostane watchdog
                    updated_conn = replace(m, last_activity=now, inactive=False)
                    new_members.add(updated_conn)
                else:
                    new_members.add(m)

            if updated_conn is None:
                return

            self.rooms[room] = new_members

            # pokud je performer, restartuj watchdog
            if updated_conn.role == "performer":
                await self._start_inactivity_watchdog(room, updated_conn)

    # ---------- join / leave / send / presence ----------

    async def join(self, room: str, c: Conn) -> bool:
        """
        Přidá klienta do místnosti jako watcher (performer řešíme zvlášť).
        Zakazuje víc spojení ze stejného device/IP (staré kopy vyhodí).
        """
        async with self.lock:
            members = self.rooms.setdefault(room, set())

            # Zákaz více spojení se stejným device nebo IP
            same_device_or_ip = [
                m for m in members
                if (m.device == c.device) or (m.ip == c.ip)
            ]

            for old in same_device_or_ip:
                try:
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
                # pro jistotu zabij i watchdog
                await self._stop_inactivity_watchdog(old.client_id)

            members.add(c)

        # WS accept až po zapsání do struktury
        await c.ws.accept()
        await self._presence(room)
        return True

    async def leave(self, room: str, c: Conn):
        async with self.lock:
            if room in self.rooms:
                self.rooms[room].discard(c)
                # vždy ukončit watchdog pro daného klienta
                await self._stop_inactivity_watchdog(c.client_id)

                performer_gone = c.role == "performer"
                if not self.rooms[room]:
                    del self.rooms[room]
                else:
                    if performer_gone:
                        # povýš prvního watcher-a na performera
                        for member in self.rooms[room]:
                            if member.role == "watcher":
                                upgraded = replace(
                                    member,
                                    role="performer",
                                    last_activity=time.time(),
                                    inactive=False,
                                )
                                self.rooms[room].discard(member)
                                self.rooms[room].add(upgraded)

                                # začni hlídat aktivitu nového performera
                                await self._start_inactivity_watchdog(room, upgraded)

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
        async with self.lock:
            targets = list(self.rooms.get(room, []))

        text = json.dumps(msg, separators=(",", ":"))
        dead: List[Conn] = []

        for c in targets:
            if skip and c.client_id == skip:
                continue
            try:
                await c.ws.send_text(text)
            except Exception:
                dead.append(c)

        for d in dead:
            await self.leave(room, d)

    async def _presence(self, room: str):
        async with self.lock:
            members_list = list(self.rooms.get(room, []))
            members = [
                {
                    "client_id": c.client_id,
                    "device": c.device,
                    "role": c.role,
                    "inactive": c.inactive,
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

    # ---------- admin drop_everyone (opraveno) ----------

    async def drop_everyone(self) -> int:
        """
        Odpojí všechny klienty ve všech místnostech.
        Používá se z admin endpointu.
        """
        async with self.lock:
            allmembers: List[Conn] = [
                c for members in self.rooms.values() for c in members
            ]
            # vyčisti místnosti
            self.rooms.clear()

            # zruš všechny watchdogy
            for task in self.activity_tasks.values():
                task.cancel()
            self.activity_tasks.clear()

        for c in allmembers:
            try:
                await c.ws.send_text(json.dumps({
                    "type": "info",
                    "event": "kicked",
                    "reason": "admin_drop_all",
                    "message": "Byl jsi odpojen administrativním zásahem.",
                }, separators=(",", ":")))
            except Exception:
                pass

            try:
                await c.ws.close(code=4404)
            except Exception:
                pass

        return len(allmembers)

    # ---------- uživatelský „request performer“ ----------

    async def request_performer(self, room: str, client_id: str) -> bool:
        """
        Uživatelský požadavek na roli performera.

        - pokud v místnosti NENÍ performer -> klient se stane performerem
        - pokud performer JE, ale je neaktivní (15+ s bez zprávy nebo inactive=True),
          vezmeme mu roli a nový se stane performerem
        - pokud performer JE a je aktivní -> vrací False
        """
        async with self.lock:
            members = self.rooms.get(room)
            if not members:
                return False

            # najdi žadatele
            requester: Optional[Conn] = None
            for m in members:
                if m.client_id == client_id:
                    requester = m
                    break

            if requester is None:
                return False

            now = time.time()
            current_performer: Optional[Conn] = None
            for m in members:
                if m.role == "performer":
                    current_performer = m
                    break

            new_members: Set[Conn] = set()

            if current_performer is None:
                # žádný performer -> žadatel se stává performerem
                for m in members:
                    if m.client_id == client_id:
                        upgraded = replace(
                            m,
                            role="performer",
                            last_activity=now,
                            inactive=False,
                        )
                        new_members.add(upgraded)
                        requester = upgraded
                    else:
                        new_members.add(m)
                self.rooms[room] = new_members

                # nový performer -> watchdog
                await self._start_inactivity_watchdog(room, requester)
            else:
                # performer existuje -> ověř jeho aktivitu
                idle = now - current_performer.last_activity
                performer_inactive = current_performer.inactive or idle >= self.INACTIVITY_TIMEOUT

                if not performer_inactive:
                    # performer je aktivní -> zamítnout
                    return False

                # performer je neaktivní -> seber roli a dej ji žadateli
                for m in members:
                    if m.client_id == current_performer.client_id:
                        demoted = replace(m, role="watcher")
                        new_members.add(demoted)
                    elif m.client_id == client_id:
                        upgraded = replace(
                            m,
                            role="performer",
                            last_activity=now,
                            inactive=False,
                        )
                        new_members.add(upgraded)
                        requester = upgraded
                    else:
                        new_members.add(m)

                self.rooms[room] = new_members

                # stop watchdog starého performera, start pro nového
                await self._stop_inactivity_watchdog(current_performer.client_id)
                await self._start_inactivity_watchdog(room, requester)

        # mimo lock pošli info dotčeným a presence
        try:
            await requester.ws.send_text(json.dumps({
                "type": "info",
                "event": "role_changed",
                "role": "performer",
                "reason": "request_performer",
                "message": "Byl jsi nastaven jako performer.",
            }, separators=(",", ":")))
        except Exception:
            pass

        if current_performer is not None:
            try:
                await current_performer.ws.send_text(json.dumps({
                    "type": "info",
                    "event": "role_changed",
                    "role": "watcher",
                    "reason": "request_performer",
                    "message": "Byl jsi přeřazen na watcher, protože jiný klient převzal roli performera.",
                }, separators=(",", ":")))
            except Exception:
                pass

        await self._presence(room)
        return True

    # ---------- původní admin force_takeover necháme (beze změny logiky) ----------

    async def force_takeover(self, room: str, new_performer_id: str) -> bool:
        """
        ADMIN: nastaví client_id jako performera bez ohledu na aktivitu.
        """
        async with self.lock:
            members = self.rooms.get(room)
            if not members:
                return False

            target = None
            for m in members:
                if m.client_id == new_performer_id:
                    target = m
                    break

            if target is None:
                return False

            new_members: Set[Conn] = set()
            demoted: List[Conn] = []
            upgraded: Optional[Conn] = None

            now = time.time()

            for m in members:
                if m.client_id == new_performer_id:
                    upgraded = replace(
                        m,
                        role="performer",
                        last_activity=now,
                        inactive=False,
                    )
                    new_members.add(upgraded)
                elif m.role == "performer":
                    dem = replace(m, role="watcher")
                    new_members.add(dem)
                    demoted.append(dem)
                else:
                    new_members.add(m)

            if upgraded is None:
                return False

            self.rooms[room] = new_members

            # watchdogy: starým performerům stop, nový start
            for d in demoted:
                await self._stop_inactivity_watchdog(d.client_id)
            await self._start_inactivity_watchdog(room, upgraded)

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
    now = time.time()
    return Conn(
        ws=ws,
        client_id=str(uuid.uuid4()),
        device=device,
        role=role,
        ip=ip,
        last_activity=now,
        inactive=False,
    )
