# api/ws_api
import json
from dataclasses import replace
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, Path
from services.ws_hub_service import hub, new_conn
from models.ws_message import WSIn
from datetime import datetime
from enum import Enum

from services.shadow_watchdog import register_activity

import asyncio

API_TOKEN = "demo-token"
VALID_ROLES = {"watcher", "performer"}

class RoomName(str, Enum):
    kuka_pianist = "kuka_pianist"


router_ws = APIRouter(tags=["WebSocket"])

from core.Kuka_robot_config import robot


@router_ws.get("/WS/clients")
async def get_clients():
    clients = []

    async with hub.lock:
        for room_name, members in hub.rooms.items():
            for conn in members:
                clients.append({
                    "room": room_name,
                    "client_id": conn.client_id,
                    "device": conn.device,
                    "ip": conn.ip,
                    "role": conn.role,
                })

    return {"clients": clients}


@router_ws.get("/WS/performer")
async def get_performers():
    performer = []

    # Uzamkneme hub, abychom měli konzistentní přístup k rooms
    async with hub.lock:
        for room_name, members in hub.rooms.items():
            for conn in members:
                if conn.role == "performer":
                    performer.append({
                        "room": room_name,
                        "client_id": conn.client_id,
                        "device": conn.device,
                        "ip": conn.ip,
                    })

    return {"performer": performer}


@router_ws.get("/WS/watchers")
async def get_watchers():
    watchers = []

    # Uzamkneme hub, abychom měli konzistentní přístup k rooms
    async with hub.lock:
        for room_name, members in hub.rooms.items():
            for conn in members:
                if conn.role == "watcher":
                    watchers.append({
                        "room": room_name,
                        "client_id": conn.client_id,
                        "device": conn.device,
                        "ip": conn.ip,
                    })

    return {"watchers": watchers}


@router_ws.post("/WS/kickAll")
async def drop_everyone():
    """
    Admin endpoint pro odpojení všech performerů ve všech místnostech.
    (ws spojení se zavře, ve ws_endpoint se pak provede leave a presence.)
    """
    dropped = await hub.drop_everyone()
    return {
        "status": "ok",
        "dropped": dropped,
    }

@router_ws.post("/WS/{room}/takeover")
async def takeover_performer(
    room: RoomName = Path(
        ...,
    ),
    client_id: str = Query(..., description="client_id spojení, které má převzít roli performera"),
):
    ok = await hub.force_takeover(room.value, client_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Místnost nebo client_id nenalezen (nebo klient už je performerem)."
        )

    return {
        "status": "ok",
        "room": room.value,
        "new_performer": client_id,
    }



@router_ws.post("/WS/{room}/request-performer")
async def request_performer(
    room: RoomName = Path(
        ...,
    ),
    client_id: str = Query(..., description="client_id spojení, které žádá roli performera"),
):
    """
    Uživatelský endpoint:
    - pokud v room není performer -> requester se stane performerem
    - pokud performer je, ale je neaktivní (15+ s) -> role se mu vezme a requester ji dostane
    - pokud performer je a aktivní -> 409
    """
    ok = await hub.request_performer(room, client_id)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail="Performer už existuje a je aktivní, nebo klient/místnost neexistuje.",
        )

    return {
        "status": "ok",
        "room": room,
        "new_performer": client_id,
    }

@router_ws.post("/WS/{room}/release-performer")
async def release_performer(
    room: RoomName = Path(
        ...,
    ),
):
    """
    Admin/utility endpoint:
    - najde v místnosti aktuálního performera
    - změní mu roli zpět na "watcher"
    - tím se uvolní performer role pro dalšího klienta
    """
    released_id = await hub.release_performer(room.value)

    if released_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"V místnosti '{room.value}' není žádný performer."
        )

    return {
        "status": "ok",
        "room": room.value,
        "released_client_id": released_id,
        "new_role": "watcher",
    }


@router_ws.websocket("/ws")
async def ws_endpoint(
    ws: WebSocket,
    room: str = Query(...),
    token: str = Query(""),
    device: str = Query("web"),
    role: str = Query("watcher"),
    echo_self: bool = Query(False),
):
    client_ip = ws.client.host if ws.client else "unknown"

    # 1) Auth
    if token != API_TOKEN:
        await ws.close(code=4401)  # Unauthorized
        return

    # 2) Vždy watcher při připojení
    role = "watcher"
    
    print(f"[WS][{client_ip}][{datetime.now().strftime('%H:%M:%S')}] Připojování k místnosti '{room}' jako '{role}' z zařízení '{device}'")

    # 3) Vytvoř připojení a pokus se přidat do místnosti
    base_conn = new_conn(ws, device, role, client_ip)
    active_conn = base_conn
    
    joined = await hub.join(room, active_conn)

    if not joined:
        try:
            await ws.send_text(json.dumps({
                "type": "error",
                "reason": "join_failed",
                "message": "Nelze se připojit do místnosti.",
            }, separators=(",", ":")))
        except Exception:
            pass
        await ws.close(code=4403)
        return

    print(f"[WS][{client_ip}] Připojen jako watcher (client_id={active_conn.client_id})")

    try:
        await ws.send_text(json.dumps({
            "type": "info",
            "event": "role_assigned",
            "role": active_conn.role,
            "device": active_conn.device,
            "room": room,
            "client_id": active_conn.client_id,
            "message": f"Vaše role je {active_conn.role}.",
        }, separators=(",", ":")))
    except Exception:
        pass
    

    # 4) Hlavní smyčka
    try:
        while True:
            raw = await ws.receive_text()
            #print(f"[WS][{client_ip}] Přijatý raw:", raw)
            await hub.mark_activity(room, active_conn.client_id)

            # Parsování příchozí zprávy
            if raw.startswith("{"):
                data = WSIn.model_validate_json(raw)
            else:
                data = WSIn(type="event")

            # Keepalive
            if data.type == "ping":
                await ws.send_text('{"type":"pong"}')
                print(f"[WS][{client_ip}] Odesílám pong")
                continue

            if data.type == "note_on":
                await register_activity()
                print(f"[WS][{client_ip}] Note ON - note:{data.note} velocity:{data.vel}")
                # Zde můžete přidat další logiku pro note_on
                asyncio.create_task(robot.play_note(data.note))

            if data.type == "note_off":
                print(f"[WS][{client_ip}] Note OFF - note:{data.note} duration:{data.duration}ms")
                # Zde můžete přidat další logiku pro note_off
                asyncio.create_task(robot.play_note(data.note, data.duration))

            if data.type == "song_button":
                print(f"[WS][{client_ip}] Play song - number:{data.button}")
                # Zde můžete přidat další logiku pro note_off
                asyncio.create_task(robot.play_song(song_number=data.button))

            #[WS][127.0.0.1] Přijatý raw: {"type":"note_on","note":8,"vel":100,"ts":1761211930005}
            #[WS][127.0.0.1] Přijatý raw: {"type":"note_off","note":8,"ts":1761211930539,"duration":534}
          

            payload = {
                "type": data.type,
                "note": getattr(data, "note", None),
                "vel": data.vel if getattr(data, "type", None) == "note_on" else None,
                "sustain": getattr(data, "sustain", None),
                "ts": getattr(data, "ts", None),
                "duration": getattr(data, "duration", None),
                "mode": getattr(data, "mode", None),
                "from_id": active_conn.client_id,
                "device": active_conn.device,
                "role": active_conn.role,
                "room": room,
            }

            await hub.send_room(room, payload, skip=None if echo_self else active_conn.client_id)

    except WebSocketDisconnect:
        print(f"[WS][{client_ip}][{datetime.now().strftime('%H:%M:%S')}] Odpojeno")
        pass
    finally:
        await hub.leave(room, active_conn)
