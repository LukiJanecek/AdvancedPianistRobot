# api/service_api.py
from fastapi import APIRouter, Header, HTTPException
from core.service_lock import acquire, release, heartbeat, get_status

router_service = APIRouter(prefix="/service", tags=["Service"])

def _client_id_or_400(x_client_id: str | None) -> str:
    if not x_client_id:
        raise HTTPException(status_code=400, detail="Missing X-Client-Id header")
    return x_client_id

@router_service.get("/status")
def service_status():
    return get_status()

@router_service.post("/acquire")
def service_acquire(x_client_id: str = Header(..., alias="X-Client-Id")):
    client_id = _client_id_or_400(x_client_id)
    res = acquire(client_id)
    if not res["ok"]:
        raise HTTPException(status_code=423, detail="Service is busy")
    return res

@router_service.post("/heartbeat")
def service_heartbeat(x_client_id: str = Header(..., alias="X-Client-Id")):
    client_id = _client_id_or_400(x_client_id)
    res = heartbeat(client_id)
    if not res["ok"]:
        raise HTTPException(status_code=409, detail=res.get("reason","not_owner"))
    return res

@router_service.post("/release")
def service_release(x_client_id: str = Header(..., alias="X-Client-Id")):
    client_id = _client_id_or_400(x_client_id)
    res = release(client_id)
    if not res["ok"]:
        raise HTTPException(status_code=409, detail=res.get("reason","not_owner"))
    return res
