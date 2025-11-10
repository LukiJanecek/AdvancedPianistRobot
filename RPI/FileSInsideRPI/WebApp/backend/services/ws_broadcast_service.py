# services/ws_broadcast_service.py
import asyncio
from core.Kuka_robot_config import robot
from services.ws_hub_service import hub

async def broadcast_robot_state_loop():
    """
    Globální loop: každých 5 sekund kontroluje stav robota.
    Pokud se změnil a existuje alespoň jeden připojený klient,
    pošle ho všem ve všech místnostech.
    """
    try:
        last_status = None
        print("[WS][GLOBAL] Spouštím broadcast_robot_state_loop...")

        while True:
            # 1) Získat snapshot aktivních místností
            async with hub.lock:
                active_rooms = {name: members for name, members in hub.rooms.items() if members}

            # 2) Pokud není žádná aktivní místnost, čekáme
            if not active_rooms:
                await asyncio.sleep(5)
                continue

            # 3) Získat stav robota (asynchronně)
            try:
                state = await robot.get_robot_state()
            except Exception as e:
                print(f"[WS][GLOBAL] Chyba při získávání stavu robota: {e}")
                await asyncio.sleep(5)
                continue

            # 4) Poslat jen pokud se stav změnil
            if state != last_status:
                payload = {
                    "type": "robot_state",
                    "state": state,
                    "ts": asyncio.get_event_loop().time(),
                }

                for room in active_rooms.keys():
                    await hub.send_room(room, payload)

                last_status = state  # zapamatuj nový stav
                print(f"[WS][GLOBAL] Odeslán nový stav robota: {state}")

            # 5) Pauza
            await asyncio.sleep(5)

    except asyncio.CancelledError:
        print("[WS][GLOBAL] broadcast_robot_state_loop ukončen (server shutdown).")
        return
