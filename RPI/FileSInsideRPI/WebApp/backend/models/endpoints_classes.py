from pydantic import BaseModel, Field
from typing import List, Optional

    
class WriteVarReq(BaseModel):
    name: str = Field(..., examples=["PyX"])
    value: str | float | int | bool

class WordReq(BaseModel):
    text: str = Field(..., min_length=1, max_length=5)
    offsetDef: int = 70