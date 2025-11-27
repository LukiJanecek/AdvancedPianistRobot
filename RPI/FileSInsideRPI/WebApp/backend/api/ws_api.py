# api/ws_api
import json
from dataclasses import replace
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from services.ws_hub_service import hub, new_conn
from models.ws_message import WSIn
from datetime import datetime
from typing import Optional

from services.shadow_watchdog import register_activity

import asyncio

router_ws = APIRouter(tags=["WebSocket"])

from core.Kuka_robot_config import robot

@router_ws.get("/WS/performer")
async def get_performer():
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
                    })

    return {"watchers": watchers}

@router_ws.post("/WS/performers/clear")
async def clear_all_performers():
    """
    Admin endpoint pro odpojení všech performerů ve všech místnostech.
    (ws spojení se zavře, ve ws_endpoint se pak provede leave a presence.)
    """
    dropped = await hub.drop_all_performers()
    return {
        "status": "ok",
        "dropped_performers": dropped,
    }

@router_ws.post("/WS/{room}/takeover")
async def takeover_performer(
    room: str,
    client_id: str = Query(..., description="client_id spojení, které má převzít roli performera"),
):
    """
    Admin endpoint pro převzetí role performera v dané místnosti.
    - klient s daným client_id se stane performerem
    - pokud existoval jiný performer, je přeřazen na watcher
    """
    ok = await hub.force_takeover(room, client_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Místnost nebo client_id nenalezen (nebo klient už je performerem)."
        )

    return {
        "status": "ok",
        "room": room,
        "new_performer": client_id,
    }


API_TOKEN = "demo-token"
VALID_ROLES = {"watcher", "performer"}

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

    # 2) Normalizace/validace role
    role = role.lower().strip()
    if role not in VALID_ROLES:
        await ws.close(code=4400)  # Bad Request
        return
    
    print(f"[WS][{client_ip}][{datetime.now().strftime('%H:%M:%S')}] Připojování k místnosti '{room}' jako '{role}' z zařízení '{device}'")

    # 3) Vytvoř připojení a pokus se přidat do místnosti
    base_conn = new_conn(ws, device, role, client_ip)
    active_conn = base_conn

    joined = await hub.join(room, active_conn)  # False = např. performer už existuje

    # 3a) Fallback: performer → watcher (pokud performer už existuje)
    if not joined and role == "performer":
        
        try:
            active_conn = replace(base_conn, role="watcher")
        except TypeError:
            # Kdyby to nebyl dataclass (okrajový případ), vytvoř nové připojení jako watcher
            active_conn = new_conn(ws, device, "watcher")

        joined = await hub.join(room, active_conn)


    if not joined:
        # Nepodařilo se připojit ani po fallbacku
        try:
            await ws.send_text(json.dumps({
                "type": "error",
                "reason": "join_failed",
                "message": "Nelze se připojit do místnosti.",
            }, separators=(",", ":")))
        except Exception:
            pass
        await ws.close(code=4403)  # Forbidden
        return
    
    if active_conn.role == "performer":
        print(f"[WS][{client_ip}] Novy performer") 
    else:
        print(f"[WS][{client_ip}] Performer obsazen.. prirazena role watcher")
        
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
