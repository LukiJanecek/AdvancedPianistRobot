# services/shadow_watchdog.py
from typing import Optional
import asyncio

from core.Kuka_robot_config import robot

INACTIVITY_TIMEOUT = 60  # sekund bez note_on/note_off/song_button

inactivity_task: Optional[asyncio.Task] = None
shadow_active: bool = False
shadow_lock = asyncio.Lock()

_shadow_auto_stopped: bool = False

def get_shadow_auto_stopped() -> bool:
    """
    True, pokud byl shadow mode naposledy ukončen AUTOMATICKY
    kvůli neaktivitě (timeout). Resetuje se při další aktivitě.
    """
    return _shadow_auto_stopped

async def _read_shadow_flag_from_robot() -> Optional[bool]:
    """
    Přečte z robota, jestli je aktuálně zapnutý shadow mode.
    Vrací:
      - True  -> shadow zapnutý
      - False -> shadow vypnutý
      - None  -> nepodařilo se zjistit (chyba / odpojeno)
    """
    if not await robot.KUKA_IsConnected():
        print("[WATCHDOG] _read_shadow_flag_from_robot: robot není připojen")
        return None

    try:
        val = await robot.KUKA_ReadVar("PyShadow")
        #print(f"[WATCHDOG] _read_shadow_flag_from_robot: PyShadow={val!r}")

        # robustní normalizace
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            v = val.strip().lower()
            if v in ("true", "1", "yes", "on"):
                return True
            if v in ("false", "0", "no", "off"):
                return False
        if isinstance(val, (int, float)):
            return bool(val)

        #print("[WATCHDOG] _read_shadow_flag_from_robot: neznámý typ hodnoty")
        return None

    except Exception as e:
        #print(f"[WATCHDOG] Chyba při čtení PyShadowFb: {e}")
        return None


async def start_shadow_if_needed():
    """
    Spustí shadow mode, pokud ještě neběží.
    Nejprve si přečte stav z robota, teprve pak případně zapisuje.
    Používá se z WS i z REST endpointů.
    """
    global shadow_active
    async with shadow_lock:
        #print("[WATCHDOG] Požadavek na START shadowingu")

        # 1) sync s reálným stavem na robotovi
        remote_state = await _read_shadow_flag_from_robot()
        if remote_state is not None:
            shadow_active = remote_state

        if shadow_active:
            #print("[WATCHDOG] Shadow už běží (podle robota) - nic nedělám")
            return

        if not await robot.KUKA_IsConnected():
            #print("[WATCHDOG] Robot není připojen, shadowing nezačínám")
            return

        # 2) skutečný start
        #print("[WATCHDOG] Posílám start_shadow_mode() do robota...")
        ok = await robot.start_shadow_mode()

        if ok:
            shadow_active = True
            #print("[WATCHDOG] ✔ Shadow mode STARTED")
        else:
            print("[WATCHDOG] ✖ Nepodařilo se spustit shadow mode")


async def stop_shadow():
    """
    Zastaví shadow mode, pokud běží.
    Nejprve si přečte stav z robota, teprve pak případně zapisuje.
    Používá se z WS i z REST endpointů.
    """
    global shadow_active
    async with shadow_lock:
        print("[WATCHDOG] Požadavek na STOP shadowingu")

        # 1) sync s reálným stavem na robotovi
        remote_state = await _read_shadow_flag_from_robot()
        if remote_state is not None:
            shadow_active = remote_state

        if not shadow_active:
            #print("[WATCHDOG] Shadow už je vypnutý (podle robota) - nic nedělám")
            return

        if not await robot.KUKA_IsConnected():
            print("[WATCHDOG] Robot není připojen - nemůžu stopnout shadowing")
            return

        # 2) skutečný stop
        #print("[WATCHDOG] Posílám stop_shadow_mode() do robota...")
        ok = await robot.stop_shadow_mode()

        if ok:
            shadow_active = False
            #print("[WATCHDOG] ✔ Shadow mode STOPPED")
        else:
            print("[WATCHDOG] ✖ NEPODAŘILO se zastavit shadow mode")

async def _auto_stop_shadow():
    """
    Interní helper, který se používá POUZE při automatickém stopu
    kvůli neaktivitě (timeout). Nastaví flag _shadow_auto_stopped.
    """
    global _shadow_auto_stopped
    await stop_shadow()
    _shadow_auto_stopped = True

async def _inactivity_watchdog():
    """
    Task, který čeká INACTIVITY_TIMEOUT sekund.
    Pokud není zrušen, po uplynutí času zastaví shadowing.
    """
    #print(f"[WATCHDOG] Inactivity task START - čekám {INACTIVITY_TIMEOUT} s")

    try:
        await asyncio.sleep(INACTIVITY_TIMEOUT)
        #print("[WATCHDOG] Inactivity TIMEOUT - spouštím stop_shadow()")
        await _auto_stop_shadow()

    except asyncio.CancelledError:
        print("[WATCHDOG] Inactivity task CANCELLED - aktivita resetovala timer")

def _reset_inactivity_timer():
    """
    Resetne globální timer. Volat při každé aktivitě (note_on/off, song_button,
    nebo manuální start z FE).
    """
    global inactivity_task

    if inactivity_task and not inactivity_task.done():
        #print("[WATCHDOG] Ruším předchozí inactivity_task")
        inactivity_task.cancel()

    loop = asyncio.get_running_loop()
    inactivity_task = loop.create_task(_inactivity_watchdog())

    #print("[WATCHDOG] Reset a nový start inactivity timeru")


async def register_activity():
    """
    Zavolat při každé MIDI aktivitě (nebo manuálním startu z FE):
    - resetne timer
    - zajistí, že shadow mode běží
    """
    global _shadow_auto_stopped
    print("[WATCHDOG] Registruji aktivitu -> reset timeru + start shadowingu")

    # jakmile je aktivita, auto-stop už není aktuální
    _shadow_auto_stopped = False

    _reset_inactivity_timer()
    await start_shadow_if_needed()