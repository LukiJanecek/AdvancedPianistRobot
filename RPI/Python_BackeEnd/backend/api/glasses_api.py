from fastapi import APIRouter, HTTPException
from typing import List,Optional

from models.endpoints_classes import Glass, GlassAtPosition, DeleteGlassPayload
import services.glasses_service as glasses_service


router_glasses = APIRouter(prefix="/glasses", tags=["Glasses"])


@router_glasses.get("/glasses", response_model=List[Optional[Glass]])
def get_glasses():
    print("Požadavek na sklenice")
    return glasses_service.get_glasses()

@router_glasses.get("/count")
def get_glasses_count():
    return {"count": glasses_service.get_number_of_drinks()}

@router_glasses.get("/freePositions")
def get_free_slots():
    return {"free_positions": glasses_service.get_free_positions()}

@router_glasses.post("/addGlassToPosition")
def add_glass(payload: GlassAtPosition):
    try:
        glasses_service.add_glass_to_position(payload.glass, payload.position)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    print(f"Přidání sklenice '{payload.glass.name}' na pozici: {payload.position}")
    return {"status": "ok", "message": "Sklenice uložena", "position": payload.position}

@router_glasses.post("/deleteAllGlasses")
def delete_full_glasses():
    glasses_service.clear_glasses()
    print("Vymazání všech sklenic")
    return {"status": "ok", "message": "Sklenice vymazány"}

@router_glasses.post("/deleteGlassOnPosition")
def delete_item_from_glasses(payload: DeleteGlassPayload):
    try:
        deleted = glasses_service.delete_glass(payload.name or "", payload.position)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not deleted:
        print(f"Na pozici {payload.position} nebylo co mazat.")
        return {"status": "ok", "message": "Na pozici nic nebylo", "position": payload.position}

    print(f"Sklenice na pozici {payload.position} smazána.")
    return {"status": "ok", "message": "Sklenice smazána", "position": payload.position}


@router_glasses.post("/addGlassToHWState")
def add_glass_to_HW_state():
    try:
        glasses_service.sync_to_hw_state()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    print("Synchronizace sklenic do HW stavu")
    return {"status": "ok", "message": "Sklenice synchronizovány do HW stavu"}
