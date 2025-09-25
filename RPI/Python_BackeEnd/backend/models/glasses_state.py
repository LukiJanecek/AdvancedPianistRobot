# services/glasses_state.py
from typing import List, Optional
from models.endpoints_classes import Glass

class GlassesState:
    """
    Udržuje JSON strukturu pro odeslání do HW:
    {
      "glasses": {
        "pos_0": [ {"nm":"", "vol":0}, ... (6 položek) ],
        ...
        "pos_5": [ ... 6 položek ... ]
      }
    }
    Každý slot (pozice 0..5) má přesně 6 položek (max 6 ingrediencí).
    Prázdný slot = všech 6 položek {"nm":"", "vol":0}.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.glasses = {
            f"pos_{i}": [{"nm": "", "vol": 0} for _ in range(6)]
            for i in range(6)
        }

    def _is_pos_empty(self, pos: int) -> bool:
        key = f"pos_{pos}"
        return all((item["nm"] == "" and int(item["vol"]) == 0) for item in self.glasses[key])

    def _ensure_len6(self, arr: List, fill):
        """Vrátí kopii `arr` přesně délky 6, doplní hodnotou `fill` nebo ořízne."""
        out = list(arr[:6])
        while len(out) < 6:
            out.append(fill)
        return out

    def set_glass_full(self, pos: int, ingredients: List[str], volumes: List[int], drink_name: Optional[str] = None) -> None:
        """
        Naplní pozici `pos` (0..5) až 6 ingrediencemi a objemy.
        `drink_name` je volitelné; pokud ho nepotřebuješ v HW protokolu, ignoruje se.
        """
        if not (0 <= pos < 6):
            raise ValueError("pos mimo rozsah (0..5)")

        ing6 = self._ensure_len6(ingredients or [], "")
        vol6 = self._ensure_len6(volumes or [], 0)

        key = f"pos_{pos}"
        self.glasses[key] = [{"nm": ing6[i] or "", "vol": int(vol6[i] or 0)} for i in range(6)]

    def clear_pos(self, pos: int) -> None:
        """Vymaže jednu pozici (nastaví všech 6 položek na prázdno)."""
        if not (0 <= pos < 6):
            raise ValueError("pos mimo rozsah (0..5)")
        self.glasses[f"pos_{pos}"] = [{"nm": "", "vol": 0} for _ in range(6)]

    def set_from_slots(self, slots: List[Optional[Glass]]) -> None:
        """
        Přijme 6-slotové pole (Glass nebo None) a naplní self.glasses.
        Očekává, že Glass má vlastnosti: name, ingredients (List[str]), volumes (List[int]).
        """
        if len(slots) != 6:
            raise ValueError("slots musí mít délku 6")

        for pos, g in enumerate(slots):
            if g is None:
                self.clear_pos(pos)
                continue

            # Bezpečné vytažení atributů z Glass
            ingredients = getattr(g, "ingredients", None) or []
            volumes = getattr(g, "volumes", None) or []
            # drink_name = getattr(g, "name", None)  # pokud by se někdy hodilo

            self.set_glass_full(pos, ingredients, volumes)

    def to_glasses_json(self) -> dict:
        return {"glasses": self.glasses}

    def get_glasses_in_list(self) -> List[Optional[Glass]]:
        """
        Vrátí seznam 6 slotů jako Glass nebo None (pro frontend).
        Pokud je pozice prázdná, vrátí None.
        """
        result = []
        for pos in range(6):
            key = f"pos_{pos}"
            items = self.glasses[key]
            if all(item["nm"] == "" and int(item["vol"]) == 0 for item in items):
                result.append(None)
            else:
                ingredients = [item["nm"] for item in items if item["nm"] != ""]
                volumes = [int(item["vol"]) for item in items if int(item["vol"]) > 0]
                g = Glass(name="", ingredients=ingredients, volumes=volumes)  # name není v tomto kontextu znám
                result.append(g)
        return result