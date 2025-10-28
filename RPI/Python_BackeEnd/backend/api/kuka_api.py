# api/service_api.py
from fastapi import APIRouter, Header, HTTPException, Query
from core.Kuka_robot_config import robot


router_kuka = APIRouter(prefix="/Kuka", tags=["Kuka"])


@router_kuka.get("/robot/status")
async def status():
    return {
        "connected": await robot.KUKA_IsConnected(),
        "ip": robot.ipAddress,
        "port": robot.port,
    }
    
@router_kuka.post("/robot/connect")
async def connect():
    try:
        ok = await robot.KUKA_Open()
        if not ok:
            raise HTTPException(500, "Open() failed")

        client = robot.client
        if not client or not client.can_connect:
            await robot.KUKA_Close()
            raise HTTPException(502, f"Cannot connect to KUKA at {robot.ipAddress}:{robot.port}")

        print(f"[KUKA] Connected to robot at {robot.ipAddress}:{robot.port}")
        return {"connected": True, "ip": robot.ipAddress, "port": robot.port}

    except Exception as e:
        await robot.KUKA_Close()
        raise HTTPException(500, f"Connect exception: {e}")


@router_kuka.post("/robot/disconnect")
async def disconnect():
    try:
        await robot.KUKA_Close()
        print(f"[KUKA] Disconnected from robot")
        return {"connected": False}
    
    except Exception as e:
        print(f"[KUKA] Disconnect failed: {e}")
        raise HTTPException(500, f"Disconnect exception: {e}")
    

@router_kuka.post("/robot/playSong")
async def play_song(song: int = Query(...)):
    if not await robot.KUKA_IsConnected():
        raise HTTPException(400, "Not connected")
    ok = await robot.play_song(song_number=song)
    if not ok:
        raise HTTPException(504, "Song play timeout")
    return {"ok": True}

@router_kuka.post("/robot/startShadowing")
async def start_shadowing():
    if not await robot.KUKA_IsConnected():
        raise HTTPException(400, "Not connected")
    ok = await robot.start_shadow_mode()
    if not ok:
        raise HTTPException(504, "Start shadowing timeout")
    return {"ok": True}

@router_kuka.post("/robot/stopShadowing")
async def stop_shadowing():
    if not await robot.KUKA_IsConnected():
        raise HTTPException(400, "Not connected")
    ok = await robot.stop_shadow_mode()
    if not ok:
        raise HTTPException(504, "Stop shadowing timeout")
    return {"ok": True}