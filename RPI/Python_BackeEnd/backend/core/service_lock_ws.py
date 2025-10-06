# core/service_lock_ws.py
from __future__ import annotations
import asyncio, json, time
from typing import Optional, Set
from fastapi import WebSocket, WebSocketDisconnect

class ServiceLockWS:
    """
    Jeden globální “service lock” řízený přes WebSocket.
    - Lock drží vždy právě jeden klient (owner). Držení == otevřené WS spojení ownera.
    - Pokud je služba obsazená, další klient dostane "busy" a spojení ukončíme.
    - Volitelně udržujeme sadu "watchers" (read-only posluchači statusů).
    """
    def __init__(self, ttl_seconds: int = 70, enable_ttl: bool = False):
        self.owner_id: Optional[str] = None
        self.owner_ws: Optional[WebSocket] = None
        self.last_seen: float = 0.0
        self.ttl_seconds = ttl_seconds
        self.enable_ttl = enable_ttl
        self.watchers: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    def status_dict(self) -> dict:
        return {
            "type": "status",
            "busy": self.owner_id is not None,
            "owner": self.owner_id,
        }

    async def _broadcast_status(self):
        dead = []
        msg = json.dumps(self.status_dict())
        for ws in list(self.watchers):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.watchers.discard(ws)

    async def connect_as_watcher(self, ws: WebSocket):
        await ws.accept()
        self.watchers.add(ws)
        await ws.send_json(self.status_dict())

    async def acquire_or_reject(self, ws: WebSocket, client_id: str):
        await ws.accept()
        async with self._lock:
            if self.owner_id is None:
                # udělujeme lock
                self.owner_id = client_id
                self.owner_ws = ws
                self.last_seen = time.time()
                await ws.send_json({"type": "granted", "owner": client_id})
                await self._broadcast_status()
                return True
            else:
                # zamítneme
                await ws.send_json({"type": "denied", "reason": "busy", "owner": self.owner_id})
                await ws.close(code=1013)  # Try again later
                return False

    async def release_if_owner(self, client_id: str):
        async with self._lock:
            if self.owner_id == client_id:
                try:
                    if self.owner_ws:
                        await self.owner_ws.send_json({"type": "lost", "reason": "released"})
                        await self.owner_ws.close(code=1000)
                except Exception:
                    pass
                self.owner_id = None
                self.owner_ws = None
                await self._broadcast_status()

    async def handle_owner(self, ws: WebSocket, client_id: str):
        """
        Smyčka pro majitele locku — čteme zprávy (např. release, ping).
        Při chybě/odpojení lock padá.
        """
        try:
            while True:
                raw = await ws.receive_text()
                self.last_seen = time.time()
                try:
                    msg = json.loads(raw)
                except Exception:
                    await ws.send_json({"type": "error", "error": "invalid_json"})
                    continue

                t = msg.get("type")
                if t == "release":
                    await ws.send_json({"type": "bye"})
                    await ws.close(code=1000)
                    break
                elif t == "ping":
                    await ws.send_json({"type": "pong"})
                elif t == "status":
                    await ws.send_json(self.status_dict())
                else:
                    # případné domain-specific příkazy (pour, stop, …) si můžeš doplnit zde
                    await ws.send_json({"type": "ack", "cmd": t})
        except WebSocketDisconnect:
            pass
        finally:
            # odpojení = ztráta locku
            async with self._lock:
                if self.owner_id == client_id:
                    self.owner_id = None
                    self.owner_ws = None
            await self._broadcast_status()

    async def ttl_guard(self):
        """
        (Volitelné) TTL hlídač — pokud bys chtěl pořád heartbeat, hlídej last_seen.
        Když vyprší, zabij spojení a uvolni lock.
        """
        if not self.enable_ttl:
            return
        while True:
            await asyncio.sleep(5)
            async with self._lock:
                if self.owner_id and (time.time() - self.last_seen > self.ttl_seconds):
                    try:
                        if self.owner_ws:
                            await self.owner_ws.send_json({"type": "lost", "reason": "timeout"})
                            await self.owner_ws.close(code=1001)
                    except Exception:
                        pass
                    self.owner_id = None
                    self.owner_ws = None
            await self._broadcast_status()
