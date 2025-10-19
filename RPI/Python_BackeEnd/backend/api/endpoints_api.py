from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/health" , tags=["General"])
def health():
    return {"status": "ok", "app": "Ahoj, klavirista!"}