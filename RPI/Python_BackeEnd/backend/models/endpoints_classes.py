from pydantic import BaseModel, conint
from typing import List, Optional

class Order(BaseModel):
    name: str
    ingredients: List[str]
    volumes: List[int]

class Glass(BaseModel):
    name: str
    ingredients: List[str]
    volumes: List[int]

class GlassAtPosition(BaseModel):
    position: conint(ge=0, le=5)
    glass: Glass

class DeleteGlassPayload(BaseModel):
    position: conint(ge=0, le=5)
    name: Optional[str] = None

class BottleAssignment(BaseModel):
    position: int
    bottle: str

class DrinkName(BaseModel):
    name: str
    position: int

class ChoosedDrink(BaseModel):
    name: str
    position: int