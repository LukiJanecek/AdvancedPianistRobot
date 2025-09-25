# PoweringProcessSimple.py
# Jednoduchý orchestrátor: SYNC -> CHECK -> POUR -> WAIT DONE -> WAIT PICKUP
# Vysoká čitelnost, defenzivní kontroly, bez zbytečných abstrakcí.

from __future__ import annotations
import asyncio
from typing import Optional, Callable, Dict, Any

# --- Sdílené stavy a util funkce z tvého projektu ---
from core.all_states import system_state, input_state, glasses_state
import services.glasses_service as glasses_service

from services.uart_service import send_json

# --- API pro logování / notifikace (volitelné) ---
NotifyFn = Callable[[str, Dict[str, Any]], None]


class PourError(RuntimeError):
    def __init__(self, stage: str, message: str, snapshot: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.stage = stage
        self.snapshot = snapshot or {}


class PourOrchestrator:
    """
    Minimalistická třída s jedním veřejným vstupem .start(...).
    - Žádné složité dědění ani vnořené datové třídy.
    - Vše běží async, ale lze spustit i na pozadí metodou start_bg().
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

        # Nastavitelné timeouty (v sekundách) – uprav podle reálu:
        self.timeout_check = 20.0
        self.timeout_pour = 600.0
        self.timeout_pickup = 120.0

        # Poll perioda, ať nezatěžujeme CPU/serial
        self.poll_dt = 0.05

    # --------- Guard / background ----------

    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def cancel(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()

    def start_bg(self, glass_slots: dict, pouring_height: int = 150, notify: Optional[NotifyFn] = None) -> None:
        if self.running():
            raise PourError("guard", "Proces již běží.", self._snapshot())
        self._task = asyncio.create_task(self.start(pouring_height, notify))

    # --------- Hlavní scénář ----------

    async def start(self, glass_slots: dict, pouring_height: int = 150, notify: Optional[NotifyFn] = None) -> Dict[str, Any]:
        """
        Jednoduchý scénář:
          1) SYNC sklenic do HW (GlassesState) a odeslat
          2) CHECK: zapnout kontrolu a počkat na potvrzení
          3) POUR: poslat start + výšku nalévání a počkat na dokončení
          4) PICKUP: počkat, až obsluha vyzvedne sklenice
        Vrací závěrečný snapshot stavů (pro log nebo HTTP odpověď).
        """
        if notify is None:
            notify = lambda stage, data: None

        async with self._lock:
            notify("init", {"msg": "Zahajuji proces nalévání.", "pourH": pouring_height})

            # 1) SYNC -> odeslat seznam sklenic/ingrediencí na ESP
            await self._sync_glasses_and_send(notify)

            # 2) CHECK -> požádat ESP o kontrolu (senzory, bezpečnost)
            await self._send_check(True, notify)
            await self._wait_for_check_ok("check", self.timeout_check, notify)

            # 3) POUR -> nastavit výšku + start
            await self._send_start_pouring(pouring_height, notify)
            await self._wait_for_pouring_done("pour", self.timeout_pour, notify)

            # 4) PICKUP -> počkat na vyzvednutí (sklenice nejsou na místě)
            await self._wait_for_pickup("pickup", self.timeout_pickup, notify)

            result = {"ok": True, "stage": "done", "snapshot": self._snapshot()}
            notify("done", {"msg": "Hotovo.", **result})
            return result

    # --------- Kroky – čisté a krátké ----------

    async def _sync_glasses_and_send(self, notify: NotifyFn) -> None:
        """
        Propsat slots -> GlassesState, poslat JSON na ESP.
        """
        glasses_service.sync_to_hw_state()
        payload = glasses_state.to_glasses_json()
        if payload:
            # -> např. send_json(glasses_state.to_info_json())
            send_json(payload)
        notify("uart", {"msg": "Odeslán seznam sklenic do ESP.", "slots": list(glasses_state.get_glasses_in_list())})

    async def _send_check(self, enabled: bool, notify: NotifyFn) -> None:
        """
        Nastaví příznak 'check' a odešle info rámec.
        """
        system_state.set_state(check=True)
        send_json(system_state.to_info_json())
        notify("uart", {"msg": f"CHECK => {enabled}"})

    async def _send_start_pouring(self, pouring_height: int, notify: NotifyFn) -> None:
        """
        Nastaví 'start' + 'pouringHeight' a odešle info rámec.
        """
        system_state.set_state(start=True, pouringHeight=int(pouring_height))
        send_json(system_state.to_info_json())
        notify("uart", {"msg": "START POUR", "pourH": pouring_height})

    # --------- Čekací podmínky ----------

    async def _wait_for_check_ok(self, stage: str, timeout: float, notify: NotifyFn) -> None:
        notify("wait", {"stage": "check", "msg": "Čekám na dokončení CHECK..."})
        await self._wait_until(self._check_ok_condition, timeout, stage)

    async def _wait_for_pouring_done(self, stage: str, timeout: float, notify: NotifyFn) -> None:
        notify("wait", {"stage": "pour", "msg": "Čekám na dokončení nalévání..."})
        await self._wait_until(lambda: bool(input_state.pouring_done), timeout, stage)

    async def _wait_for_pickup(self, stage: str, timeout: float, notify: NotifyFn) -> None:
        """
        Podmínky:
          - pokud máš dedikovaný příznak (např. všechny position_check == False)
          - nebo (alternativa) všechny glass_done == True
        Zvol jednodušší pravidlo: sklenice nejsou na místě => vyzvednuto.
        """
        notify("wait", {"stage": "pickup", "msg": "Čekám na vyzvednutí sklenic..."})

        def pickup_cond() -> bool:
            # varianta A: všechny pozice prázdné (position_check False)
            if isinstance(input_state.position_check, list) and len(input_state.position_check) == 6:
                if all(not bool(p) for p in input_state.position_check):
                    return True
            # varianta B: všechny sklenice označeny jako hotové
            if isinstance(input_state.glass_done, list) and len(input_state.glass_done) == 6:
                if all(bool(g) for g in input_state.glass_done):
                    return True
            return False

        await self._wait_until(pickup_cond, timeout, stage)

    # --------- Defenzivní kontroly + společná wait smyčka ----------

    def _have_errors(self) -> Optional[str]:
        """
        Max. jednoduché: čteme příznaky chyb z InputState.
        (Používáme přesně názvy, které máš ve třídě.)
        """
        if input_state.emergency_stop:
            return "EMERGENCY STOP"
        if input_state.mess_error:
            return "MECHANICAL/PROCESS ERROR"
        if input_state.cannot_process_position:
            return "CANNOT PROCESS POSITION"
        if input_state.cannot_process_glass:
            return "CANNOT PROCESS GLASS"
        if input_state.cannot_set_mode:
            return "CANNOT SET MODE"
        # prázdná láhev = business rule: ukončit s chybou hned
        if isinstance(input_state.empty_bottle, list) and any(input_state.empty_bottle):
            return "EMPTY BOTTLE"
        return None

    def _check_ok_condition(self) -> bool:
        """
        Jednoduché pravidlo:
         - aspoň jedna pozice hlásí přítomnost sklenice (position_check[i] == True)
         - zároveň nejsou hlášeny chyby
        """
        if isinstance(input_state.position_check, list) and any(bool(p) for p in input_state.position_check):
            return self._have_errors() is None
        return False

    async def _wait_until(self, predicate, timeout: float, stage: str) -> None:
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            # 1) nejdřív chyby
            err = self._have_errors()
            if err:
                raise PourError(stage, f"Chyba z ESP: {err}", self._snapshot())

            # 2) splněná podmínka?
            try:
                if predicate():
                    return
            except Exception as e:
                raise PourError(stage, f"Chyba evaluace podmínky: {e!r}", self._snapshot())

            # 3) timeout?
            if asyncio.get_event_loop().time() > deadline:
                raise PourError(stage, f"Timeout {timeout:.0f}s ve fázi '{stage}'.", self._snapshot())

            await asyncio.sleep(self.poll_dt)

    # --------- Snapshots pro log/debug ----------

    def _snapshot(self) -> Dict[str, Any]:
        return {
            "input": {
                "position_check": getattr(input_state, "position_check", None),
                "glass_done": getattr(input_state, "glass_done", None),
                "empty_bottle": getattr(input_state, "empty_bottle", None),
                "pouring_done": getattr(input_state, "pouring_done", None),
                "mess_error": getattr(input_state, "mess_error", None),
                "cannot_process_position": getattr(input_state, "cannot_process_position", None),
                "cannot_process_glass": getattr(input_state, "cannot_process_glass", None),
                "cannot_set_mode": getattr(input_state, "cannot_set_mode", None),
                "emergency_stop": getattr(input_state, "emergency_stop", None),
                "mode": getattr(input_state, "current_mode", None),
            }
        }
