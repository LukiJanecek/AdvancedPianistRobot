from fastapi import APIRouter

from services.uart_service import send_json
from services.uart_service import send_uart_command

from core.all_states import system_state, glasses_state, bottles_state

router_UART = APIRouter(prefix="/uart", tags=["UART Tests"])

#UART Tests
@router_UART.post("/sendMess")
def send_command(mess: str):
    send_uart_command(mess)
    return {"status": "ok"}


@router_UART.post("/sendInfo")
def send_info():
    system_state.set_state(start=True, openValve3=True, pouringHeight=150)
    send_json(system_state.to_info_json())
    return {"status": "ok", "message": "Informace odeslána přes UART"}

@router_UART.get("/previewInfo")
def preview_info():
    msg = system_state.to_info_json()
    return msg



@router_UART.post("/sendGlasses")
def send_glasses():
    glasses_state.set_glass(pos=1, index=0, name="Rum", volume=100)
    glasses_state.set_glass(pos=2, index=1, name="Cola", volume=150)
    send_json(glasses_state.to_glasses_json())
    return {"status": "ok", "message": "Stav sklenic odeslán přes UART"}

@router_UART.get("/previewGlasses")
def preview_glasses():
    msg = glasses_state.to_glasses_json()
    return msg



@router_UART.post("/sendBottles")
def send_bottles():
    send_json(bottles_state.to_position_json())
    return {"status": "ok", "message": "Stav pozic odeslán přes UART"}

@router_UART.get("/previewBottles")
def preview_bottles():
    msg = bottles_state.to_position_json()
    return msg