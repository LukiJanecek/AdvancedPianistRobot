from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio

from api.endpoints_api import router
from api.ws_api import router_ws
from api.kuka_api import router_kuka

from core.Kuka_robot_config import robot

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
async def _autoconnect():
    async def _connect():
        try:
            print(f"[KUKA] Attempting to connect to robot at {robot.ipAddress}:{robot.port}...")
            ok = await robot.KUKA_Open()
            if ok:
                print(f"[KUKA] Connected to robot at {robot.ipAddress}:{robot.port}")
            else:
                print("[KUKA] Connect to robot failed")
        except Exception as e:
            print(f"[KUKA] Connect failed: {e}")

    asyncio.create_task(_connect())


@app.get("/")
def read_root():
    return {"message": "DrinkMaker backend běží!!! (Pro přístup k dokumentaci použij /docs)"}

@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/piano.ico")