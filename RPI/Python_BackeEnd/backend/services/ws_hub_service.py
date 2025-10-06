import json, uuid, asyncio
from dataclasses import dataclass
from typing import Dict, Set, Optional
from fastapi import WebSocket

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

    async def join(self, room: str, c: Conn):
        await c.ws.accept()
        async with self.lock:
            self.rooms.setdefault(room, set()).add(c)
        await self._presence(room)

    async def leave(self, room: str, c: Conn):
        async with self.lock:
            if room in self.rooms:
                self.rooms[room].discard(c)
                if not self.rooms[room]:
                    del self.rooms[room]
        await self._presence(room)

    async def send_room(self, room: str, msg: dict, skip: Optional[str] = None):
        targets = list(self.rooms.get(room, []))
        text = json.dumps(msg, separators=(",", ":"))
        dead = []
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
        members = [
            {"client_id": c.client_id, "device": c.device, "role": c.role}
            for c in self.rooms.get(room, [])
        ]
        await self.send_room(room, {"type": "presence", "members": members})

hub = RoomHub()

def new_conn(ws: WebSocket, device: str, role: str) -> Conn:
    return Conn(ws=ws, client_id=str(uuid.uuid4()), device=device, role=role)
