# routers/pour.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from services.pouring_process_service import PourOrchestrator, PourError

router_pouring = APIRouter(tags=["Pouring"])
service = PourOrchestrator()

def notify(stage: str, data: dict):
    # nahraď vlastním logem / WS broadcastem
    print(f"[{stage}] {data}")

@router_pouring.post("/pour/start")
async def pour_start(background: BackgroundTasks, pour_height: int = 150):
    try:
        # nespouštět paralelně dvakrát
        if service.running():
            raise HTTPException(status_code=409, detail="Proces již běží.")
        background.add_task(service.start, pour_height, notify)
        return {"status": "started", "height": pour_height}
    except PourError as e:
        raise HTTPException(status_code=409, detail={"stage": e.stage, "msg": str(e), "snapshot": e.snapshot})

@router_pouring.post("/pour/cancel")
async def pour_cancel():
    service.cancel()
    return {"status": "cancelling"}

@router_pouring.get("/pour/state")
async def pour_state():
    return {"running": service.running()}
