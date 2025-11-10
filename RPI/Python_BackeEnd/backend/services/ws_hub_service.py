# services/ws_hub_service.py
import json, uuid, asyncio
from dataclasses import dataclass
from typing import Dict, Set, Optional
from fastapi import WebSocket
from dataclasses import replace

@dataclass(frozen=True, eq=True)
class Conn:
    ws: WebSocket
    client_id: str
    device: str
    role: str

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

            # 2) Zákaz více spojení se stejným device
            same_device = [m for m in members if m.device == c.device]
            for old in same_device:
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
                {"client_id": c.client_id, "device": c.device, "role": c.role}
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

hub = RoomHub()

def new_conn(ws: WebSocket, device: str, role: str) -> Conn:
    return Conn(ws=ws, client_id=str(uuid.uuid4()), device=device, role=role)
