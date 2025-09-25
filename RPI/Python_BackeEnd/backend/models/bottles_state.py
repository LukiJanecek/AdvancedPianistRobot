from typing import List
from models.endpoints_classes import BottleAssignment

class BottlesState:
    def __init__(self):
        self.bottles = [""] * 6

    def set_bottles(self, assignments: List[BottleAssignment]):
        for item in assignments:
            if 0 <= item.position < 6:
                self.bottles[item.position] = item.bottle

    def get_bottles(self) -> List[str]:
        return self.bottles

    def get_bottle_assignments(self) -> List[BottleAssignment]:
        return [
            BottleAssignment(position=i, bottle=b)
            for i, b in enumerate(self.bottles)
        ]
    
    def to_position_json(self) -> dict:
        return {
            "bottOnPos": [
                {f"pos_{i}": b for i, b in enumerate(self.bottles)}
            ]
        }
