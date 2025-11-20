# api/service_api.py
from fastapi import APIRouter, Header, HTTPException, Query
from typing import Literal
from core.Kuka_robot_config import robot
import asyncio

router_kuka = APIRouter(prefix="/Kuka", tags=["Kuka"])


@router_kuka.get("/status")
async def status():
    state = await robot.get_robot_state()

    # odvozene booly
    in_shadow = state.get("status") == "shadow"
    playing_song = state.get("status") == "song"

    return {
        "connected": await robot.KUKA_IsConnected(),
        "ip": robot.ipAddress,
        "port": robot.port,
        "status": state.get("status"),
        "detail": state.get("detail"),
        "in_shadow_mode": in_shadow,
        "playing_song": playing_song,
    }


@router_kuka.post("/connect")
async def connect():
    try:
        ok = await robot.KUKA_Open()
        if not ok:
            raise HTTPException(500, "[KUKA] Open() failed")

        client = robot.client
        if not client or not client.can_connect:
            await robot.KUKA_Close()
            raise HTTPException(502, f"[KUKA] Cannot connect to KUKA at {robot.ipAddress}:{robot.port}")

        print(f"[KUKA] Connected to robot at {robot.ipAddress}:{robot.port}")
        return {"connected": True, "ip": robot.ipAddress, "port": robot.port}

    except Exception as e:
        await robot.KUKA_Close()
        raise HTTPException(500, f"Connect exception: {e}")


@router_kuka.post("/disconnect")
async def disconnect():
    try:
        await robot.KUKA_Close()
        print(f"[KUKA] Disconnected from robot")
        return {"connected": False}
    
    except Exception as e:
        print(f"[KUKA] Disconnect failed: {e}")
        raise HTTPException(500, f"Disconnect exception: {e}")
    

@router_kuka.post("/playSong")
async def play_song(song: int = Query(...)):
    if not await robot.KUKA_IsConnected():
        raise HTTPException(400, "Not connected")
    ok = await robot.play_song(song_number=song)
    if not ok:
        raise HTTPException(504, "Song play timeout")
    return {"ok": True}

@router_kuka.post("/startShadowing")
async def start_shadowing():
    if not await robot.KUKA_IsConnected():
        print("[KUKA] Not connected, cannot start shadowing")
        raise HTTPException(400, "Not connected")
    ok = await robot.start_shadow_mode()
    if not ok:
        raise HTTPException(504, "Start shadowing timeout")
    return {"ok": True}

@router_kuka.post("/stopShadowing")
async def stop_shadowing():
    if not await robot.KUKA_IsConnected():
        print("[KUKA] Not connected, cannot stop shadowing")
        raise HTTPException(400, "Not connected")
    ok = await robot.stop_shadow_mode()
    if not ok:
        raise HTTPException(504, "Stop shadowing timeout")
    return {"ok": True}


@router_kuka.get("/test/writeRead")
async def test_write_read(
    var: Literal[
        "PyShadow",
        "PyShadowFb",
        "PyGoToNote",
        "PyNoteDuration",
        "PyKey",
        "PyPlayingSong",
        "PyREGGAE",
        "PySTUPNICE",
        "PyBEETHOVEN",
        "PyMAX_VOLUME",
        "PyEND",
        "PyACK",
        "PyWait"
    ] = Query(..., description="Název KUKA proměnné"),
    value: str = Query(..., description="Hodnota jako string, např. 'true', 'false', '123'")
):
    if not await robot.KUKA_IsConnected():
        raise HTTPException(400, "Not connected to KUKA")

    # Normalizace bool hodnot pro KUKA (True/False)
    v = value.strip()
    if v.lower() == "true":
        norm = "True"
    elif v.lower() == "false":
        norm = "False"
    else:
        norm = v

    ok = await robot.KUKA_WriteVar(var, norm)
    if not ok:
        raise HTTPException(500, f"Write to var '{var}' failed")

    await asyncio.sleep(0.1)

    read_back = await robot.KUKA_ReadVar(var)
    if isinstance(read_back, bytes):
        read_back = read_back.decode("utf-8", errors="ignore")

    return {
        "var": var,
        "written": norm,
        "read_back": read_back,
        "note": "Používej 'true/false' pro Bool nebo číslo pro Int proměnné."
    }

@router_kuka.get("/test/readVar")
async def test_read_var(
    var: str = Query(..., description=(
        "Název proměnné, kterou chceš přečíst z KUKA robota. "
        "Např. PyShadowFb, PyKey, PyZposFb, PyNotePlayed, $POS_ACT"
    ))
):
    """
    Čte hodnotu z libovolné proměnné na straně KUKA.
    Vhodné pro ruční testování konkrétní proměnné podle názvu.
    """
    if not await robot.KUKA_IsConnected():
        raise HTTPException(400, "Not connected to KUKA")

    try:
        value = await robot.KUKA_ReadVar(var)
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        return {
            "var": var,
            "value": value,
            "note": "Pokud proměnná neexistuje nebo je jiného typu, zkontroluj název v KRL programu."
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to read variable '{var}': {e}")


@router_kuka.get("/test/note")
async def test_note(
    note: int = Query(..., description="Číslo noty 1-23"),
    duration: int = Query(5000, description="Délka noty v ms")
):
    if not await robot.KUKA_IsConnected():
        raise HTTPException(400, "Not connected to KUKA")

    await robot.KUKA_WriteVar("PyGoToNote", note)
    await asyncio.sleep(2)
    await robot.KUKA_WriteVar("PyNoteDuration", duration)

    note_fb = await robot.KUKA_ReadVar("PyGoToNote")
    duration_fb = await robot.KUKA_ReadVar("PyNoteDuration")

    return {
        "PyGoToNote_written": note,
        "PyNoteDuration_written": duration,
        "PyGoToNote_fb": note_fb,
        "PyNoteDuration_fb": duration_fb,
    }


@router_kuka.get("/test/allVars")
async def test_all_vars():
    if not await robot.KUKA_IsConnected():
        raise HTTPException(400, "Not connected to KUKA")

    # ===== Seznam proměnných =====
    vars = [
        "PyShadow",
        "PyShadowFb",
        "PyGoToNote",
        "PyNoteDuration",
        "PyREGGAE",
        "PySTUPNICE",
        "PyBEETHOVEN",
        "PyMAX_VOLUME",
        "PyKey",
        "PyPlayingSong",
        "PyEND",
        "PyACK",
        "PyWait",
        "$POS_ACT",
    ]

    results = {}

    for v in vars:
        try:
            val = await robot.KUKA_ReadVar(v)
            if isinstance(val, bytes):
                val = val.decode("utf-8", errors="ignore")
            results[v] = val
        except Exception as e:
            results[v] = f"Error: {e}"


    return {
        "robot_ip": robot.ipAddress,
        "port": robot.port,
        "connected": await robot.KUKA_IsConnected(),
        "variables": results,
    }
