import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.ws_hub_service import hub, new_conn
from models.ws_message import WSIn

router_ws = APIRouter()

API_TOKEN = "demo-token"   # natvrdo

@router_ws.websocket("/ws")
async def ws_endpoint(
    ws: WebSocket,
    room: str = Query(...),
    token: str = Query(""),
    device: str = Query("web"),
    role: str = Query("performer"),
    echo_self: bool = Query(False),
):
    if token != API_TOKEN:
        await ws.close(code=4401)
        return

    conn = new_conn(ws, device, role)
    await hub.join(room, conn)
    try:
        while True:
            raw = await ws.receive_text()
            data = WSIn.model_validate_json(raw) if raw.startswith("{") else WSIn(type="event")
            if data.type == "ping":
                await ws.send_text('{"type":"pong"}')
                continue

            payload = {
                "type": data.type,
                "note": data.note,
                "vel": data.vel if data.type == "note_on" else None,
                "sustain": data.sustain,
                "ts": data.ts,
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
