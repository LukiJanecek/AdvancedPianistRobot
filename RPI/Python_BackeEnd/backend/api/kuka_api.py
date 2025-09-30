# api/service_api.py
from fastapi import APIRouter, Header, HTTPException, Query
from services.kuka_service import KUKAHandler
from models.endpoints_classes import ConnectReq
from core.kuka_config import settings

router_kuka = APIRouter(prefix="/Kuka", tags=["Kuka"])

robot = KUKAHandler()

@router_kuka.get("/status")
def status():
    return {
        "connected": robot.is_connected(),
        "ip": getattr(robot, "_ip", None),
        "port": getattr(robot, "_port", None),
    }

@router_kuka.post("/connect")
def connect(req: ConnectReq):
    ip = req.ip or settings.ROBOT_IP
    port = req.port or settings.ROBOT_PORT
    try:
        ok = robot.open(ip, port)
        if not ok:
            raise HTTPException(500, "Connect failed")
        return {"connected": True, "ip": ip, "port": port}
    except Exception as e:
        raise HTTPException(500, f"Connect exception: {e}")

@router_kuka.post("/disconnect")
def disconnect():
    robot.close()
    return {"connected": False}

@router_kuka.post("/home")
def go_home(timeout: float = Query(30.0, ge=1.0, le=120.0)):
    if not robot.is_connected():
        raise HTTPException(400, "Not connected")
    ok = robot.go_home(timeout=timeout)
    if not ok:
        raise HTTPException(504, "Home timeout")
    return {"ok": True}
