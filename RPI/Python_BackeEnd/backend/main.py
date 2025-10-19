from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.kuka_service import KUKAHandler
from api.endpoints_api import router
from api.ws_api import router_ws
from api.kuka_api import router_kuka

from core.kuka_config import settings
robot = KUKAHandler()

app = FastAPI(
    title="Klavirista API",
    description="Ovládací REST API pro Rpi backend.",
    version="0.0.1",
    openapi_tags=[
        {"name": "General", "description": "Obecná funkce API"},
        {"name": "Kuka", "description": "Funkce pro ovládání KUKA robota"},
    ]
)

# Povolené originy
origins = [
    "http://localhost:5173",      
    "http://192.168.1.111:5173",
    "http://127.0.0.1:5173",      
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # seznam povolených originů
    allow_credentials=True,
    allow_methods=["*"],            # povol všechny metody (GET, POST, atd.)
    allow_headers=["*"],            # povol všechny hlavičky
)
app.include_router(router)
app.include_router(router_ws)
app.include_router(router_kuka)

# Přidání složky se statickými soubory
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def _autoconnect():
    try:
        robot.open(settings.ROBOT_IP, settings.ROBOT_PORT)
    except Exception as e:
        # necháme připojení i tak volitelné přes /connect
        print(f"[KUKA] Autoconnect failed: {e}")

@app.get("/")
def read_root():
    return {"message": "DrinkMaker backend běží!"}

@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/piano.ico")