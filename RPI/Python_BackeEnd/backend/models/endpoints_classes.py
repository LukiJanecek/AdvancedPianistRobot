from pydantic import BaseModel, Field
from typing import List, Optional

class ConnectReq(BaseModel):
    ip: Optional[str] = None
    port: Optional[int] = None

class VarsReq(BaseModel):
    x: float = 0
    y: float = 0
    z: float = 0
    a: float = 0
    b: float = 0
    c: float = 0

class WriteVarReq(BaseModel):
    name: str = Field(..., examples=["PyX"])
    value: str | float | int | bool

class WordReq(BaseModel):
    text: str = Field(..., min_length=1, max_length=5)
    offsetDef: int = 70