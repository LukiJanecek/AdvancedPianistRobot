# api/kuka_api.py
from fastapi import APIRouter, HTTPException, Query
from typing import Literal
from core.Kuka_robot_config import robot
import asyncio

from services.kuka_service import SONG_MAP  # přidej nahoře import SONG_MAP

from services.shadow_watchdog import register_activity, stop_shadow

router_kuka = APIRouter(prefix="/Kuka", tags=["Kuka"])


async def _ensure_connected() -> None:
    """
    Helper – zkontroluje připojení robota.
    Pokud není připojen, vyhodí HTTP 503.
    """
    if not await robot.KUKA_IsConnected():
        raise HTTPException(
            status_code=503,
            detail="[KUKA] Robot is not connected",
        )

@router_kuka.get("/status")
async def status():
    state = await robot.get_robot_state()

    in_shadow = state.get("status") == "shadow"
    playing_song = state.get("status") == "song"
    song_number = await robot.get_current_song()
    song_name = SONG_MAP.get(song_number) if song_number is not None else None

    # nově – vyčtená hodnota PyShadowStart z cache
    shadow_start = state.get("shadow_start")

    return {
        "connected": await robot.KUKA_IsConnected(),
        "ip": robot.ipAddress,
        "port": robot.port,
        "status": state.get("status"),
        "detail": state.get("detail"),
        "in_shadow_mode": in_shadow,
        "playing_song": playing_song,
        "song_number": song_number,
        "song_name": song_name,
        "shadow_start": shadow_start,   # <-- pro frontend
        "updated_at": state.get("updated_at"),
    }


@router_kuka.post("/connect")
async def connect():
    try:
        ok = await robot.KUKA_Open()
        if not ok:
            raise HTTPException(500, "[KUKA] Open() failed")

        client = robot.client
        if not client or not client.can_connect:
            # nepodařilo se navázat spojení – uklidíme a vrátíme 502
            await robot.KUKA_Close()
            raise HTTPException(
                status_code=502,
                detail=f"[KUKA] Cannot connect to KUKA robot at {robot.ipAddress}:{robot.port}",
            )

        print(f"[KUKA] Connected to robot at {robot.ipAddress}:{robot.port}")
        return {"connected": True, "ip": robot.ipAddress, "port": robot.port}

    except HTTPException:
        # už správně zabalená HTTP chyba – jen ji přeposíláme dál
        raise
    except Exception as e:
        # jakákoli jiná výjimka – zavřeme a vrátíme 500
        await robot.KUKA_Close()
        raise HTTPException(500, f"[KUKA] Connect exception: {e}")


@router_kuka.post("/disconnect")
async def disconnect():
    try:
        await robot.KUKA_Close()
        print("[KUKA] Disconnected from robot")
        return {"connected": False}

    except Exception as e:
        print(f"[KUKA] Disconnect failed: {e}")
        raise HTTPException(500, f"[KUKA] Disconnect exception: {e}")


@router_kuka.post("/playSong")
async def play_song(song: int = Query(..., description="Čísla písniček 1-3")):
    await _ensure_connected()

    ok = await robot.play_song(song_number=song)
    if not ok:
        raise HTTPException(504, "[KUKA] Song play timeout")

    return {"ok": True}


@router_kuka.post("/startShadowing")
async def start_shadowing():
    await _ensure_connected()

    print("[KUKA] /startShadowing - calling register_activity()")
    try:
        await register_activity()
    except Exception as e:
        print(f"[KUKA] /startShadowing - register_activity ERROR: {e}")
        raise HTTPException(500, f"[KUKA] Failed to start shadowing: {e}")

    return {"ok": True}


@router_kuka.post("/stopShadowing")
async def stop_shadowing():
    await _ensure_connected()

    print("[KUKA] /stopShadowing - calling stop_shadow()")
    try:
        await stop_shadow()
    except Exception as e:
        print(f"[KUKA] /stopShadowing - stop_shadow ERROR: {e}")
        raise HTTPException(500, f"[KUKA] Failed to stop shadowing: {e}")

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
        "PyWait",
        "PyShadowStart",
    ] = Query(..., description="Název KUKA proměnné"),
    value: str = Query(..., description="Hodnota jako string, např. 'true', 'false', '123'"),
):
    await _ensure_connected()

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
        raise HTTPException(500, f"[KUKA] Write to var '{var}' failed")

    await asyncio.sleep(0.1)

    read_back = await robot.KUKA_ReadVar(var)
    if isinstance(read_back, bytes):
        read_back = read_back.decode("utf-8", errors="ignore")

    return {
        "var": var,
        "written": norm,
        "read_back": read_back,
        "note": "Používej 'true/false' pro Bool nebo číslo pro Int proměnné.",
    }


@router_kuka.get("/test/readVar")
async def test_read_var(
    var: str = Query(
        ...,
        description=(
            "Název proměnné, kterou chceš přečíst z KUKA robota. "
            "Např. PyShadowFb, PyKey, PyZposFb, PyNotePlayed, $POS_ACT"
        ),
    )
):
    """
    Čte hodnotu z libovolné proměnné na straně KUKA.
    Vhodné pro ruční testování konkrétní proměnné podle názvu.
    """
    await _ensure_connected()

    try:
        value = await robot.KUKA_ReadVar(var)
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        return {
            "var": var,
            "value": value,
            "note": "Pokud proměnná neexistuje nebo je jiného typu, zkontroluj název v KRL programu.",
        }
    except Exception as e:
        raise HTTPException(500, f"[KUKA] Failed to read variable '{var}': {e}")


@router_kuka.get("/test/note")
async def test_note(
    note: int = Query(..., description="Číslo noty 1-22"),
    duration: int = Query(2000, description="Délka noty v ms"),
):
    await _ensure_connected()

    print("[KUKA] /test/note - calling register_activity()")
    try:
        await register_activity()
    except Exception as e:
        print(f"[KUKA] /test/note - register_activity ERROR: {e}")
        raise HTTPException(500, f"[KUKA] register_activity failed: {e}")

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
    await _ensure_connected()

    variable_names = [
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
        "PyShadowStart",
    ]

    results = {}

    for name in variable_names:
        try:
            val = await robot.KUKA_ReadVar(name)
            if isinstance(val, bytes):
                val = val.decode("utf-8", errors="ignore")
            results[name] = val
        except Exception as e:
            results[name] = f"Error: {e}"

    return {
        "robot_ip": robot.ipAddress,
        "port": robot.port,
        "connected": await robot.KUKA_IsConnected(),
        "variables": results,
    }
