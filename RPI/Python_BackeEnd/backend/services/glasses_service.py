# services/glasses_service.py
from typing import List, Optional

from models.endpoints_classes import Glass
from core.all_states import glasses_state  # pokud používáš pro předání do HW

# Pevné „stojany“ pro 6 sklenic; prázdné sloty = None
glass_glasses: List[Optional[Glass]] = [None] * 6


def _check_pos(position: int) -> int:
    """Normalizace a kontrola rozsahu pozice (0..5). Povolí i stringy s číslem."""
    try:
        p = int(position)
    except (TypeError, ValueError):
        raise ValueError("position musí být celé číslo 0..5")
    if not 0 <= p < 6:
        raise ValueError("position mimo rozsah (0..5)")
    return p


def add_glass_to_position(glass: Glass, position: int) -> None:
    """
    Vloží/nahraje sklenici na danou pozici (0..5).
    Pokud tam něco je, přepíše se.
    """
    p = _check_pos(position)
    glass_glasses[p] = glass


def get_glasses() -> List[Optional[Glass]]:
    """
    Vrátí seznam 6 slotů (Glass nebo None) pro snadný render na frontendu.
    """
    return glass_glasses


def clear_glasses() -> None:
    """Vymaže všechny pozice (nastaví None)."""
    for i in range(6):
        glass_glasses[i] = None


def get_number_of_drinks() -> int:
    """Počet skutečně zadaných sklenic (ne-None)."""
    return sum(1 for g in glass_glasses if g is not None)


def delete_glass(name: str, position: int) -> bool:
    """
    Smaže sklenici na dané pozici. Pokud je na pozici jiné jméno,
    smaže i tak (API předává jméno jen informativně).
    Vrací True, pokud na pozici něco bylo a bylo smazáno.
    """
    p = _check_pos(position)
    if glass_glasses[p] is None:
        # už prázdné
        return False

    # Volitelně můžeš hlídat shodu jména:
    # if glass_glasses[p].name != name:
    #     return False

    glass_glasses[p] = None
    return True

def get_free_positions() -> List[int]:
    """Vrať indexy pozic (0..5), které jsou volné (None)."""
    return [i for i, g in enumerate(glass_glasses) if g is None]


def sync_to_hw_state() -> dict:
    """
    Propíše aktuální 6 slotů do GlassesState (JSON pro HW) a vrátí výsledek.
    Použij po každé změně slotů, těsně před odesláním na ESP32.
    """
    glasses_state.set_from_slots(glass_glasses)
    #return glasses_state.to_glasses_json()


