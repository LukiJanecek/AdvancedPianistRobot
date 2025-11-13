from pydantic import BaseModel
from typing import Optional, Literal

MsgType = Literal["note_on", "note_off", "event", "ping", "pong", "shadow_mode", "song_button"]

class WSIn(BaseModel):
    type: MsgType
    note: Optional[int] = None
    vel: Optional[int] = None
    sustain: Optional[bool] = None
    ts: Optional[int] = None
    duration: Optional[int] = None
    button: Optional[int] = None

class WSOut(BaseModel):
    type: MsgType
    note: Optional[int] = None
    vel: Optional[int] = None
    sustain: Optional[bool] = None
    ts: Optional[int] = None
    duration: Optional[int] = None
    room: Optional[str] = None
    device: Optional[str] = None
    role: Optional[str] = None
    from_id: Optional[str] = None
