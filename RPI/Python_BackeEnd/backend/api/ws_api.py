# api/ws_api
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.ws_hub_service import hub, new_conn
from models.ws_message import WSIn

router_ws = APIRouter()

API_TOKEN = "demo-token"   # natvrdo

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
    # 1) Auth
    if token != API_TOKEN:
        await ws.close(code=4401)  # Unauthorized
        return

    # 2) Normalizace/validace role
    role = role.lower().strip()
    if role not in VALID_ROLES:
        # Špatná role -> zavřít
        await ws.close(code=4400)  # Bad Request
        return

    # 3) Vytvoř připojení a pokus se přidat do místnosti s pravidly pro role
    conn = new_conn(ws, device, role)
    joined = await hub.join(room, conn)  # vrací False, pokud už je v room performer

    if not joined:
        # V místnosti už je performer -> odmítnout
        # (volitelně můžeš poslat krátkou zprávu před close)
        try:
            await ws.send_text(json.dumps({
                "type": "error",
                "reason": "performer_exists",
                "message": "V místnosti už je aktivní performer."
            }, separators=(",", ":")))
        except Exception:
            pass
        await ws.close(code=4403)  # Forbidden
        print("HERE")
        return

    # 4) Hlavní smyčka
    try:
        while True:
            raw = await ws.receive_text()
            print("[WS]Přijatý raw:", raw)

            # Parsování příchozí zprávy
            if raw.startswith("{"):
                data = WSIn.model_validate_json(raw)
            else:
                data = WSIn(type="event")

            # Keepalive
            if data.type == "ping":
                await ws.send_text('{"type":"pong"}')
                print("[WS]Odesílám pong")
                continue

            payload = {
                "type": data.type,
                "note": getattr(data, "note", None),
                "vel": data.vel if getattr(data, "type", None) == "note_on" else None,
                "sustain": getattr(data, "sustain", None),
                "ts": getattr(data, "ts", None),
                "duration": getattr(data, "duration", None),
                "from_id": conn.client_id,
                "device": conn.device,
                "role": conn.role,
                "room": room,
            }

            await hub.send_room(room, payload, skip=None if echo_self else conn.client_id)

    except WebSocketDisconnect:
        pass
    finally:
        await hub.leave(room, conn)
