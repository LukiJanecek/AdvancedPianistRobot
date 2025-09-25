from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from services.uart_service import uart_listener_loop
from services.uart_service import uart_JSON_listener_loop
import asyncio

from api.endpoints import router
from api.uart_test_api import router_UART
from api.queue_api import router_queue
from api.service_api import router_service
from api.glasses_api import router_glasses
from api.pouring_api import router_pouring

app = FastAPI(
    title="DrinkMaker API",
    description="Ovládací REST API pro DrinkMaker backend.",
    version="0.0.1",
    openapi_tags=[
        {"name": "General", "description": "Obecná funkce API"},
        {"name": "Queue", "description": "Správa fronty objednávek"},
        {"name": "Glasses", "description": "Správa sklenic"},
        {"name": "UART Tests", "description": "Odesílání zpráv na ESP32 přes UART"},
        {"name": "Bottles", "description": "Správa ingrediencí (láhví) pro drinky"},
        {"name": "Service", "description": "Správa zámku služby (service lock)"},
        {"name": "Pouring", "description": "Řízení procesu nalévání drinků"},
    ]
)

# Povolené originy
origins = [
    "http://localhost:5173",         # vývojové prostředí
    "http://192.168.1.111:5173",     # produkční frontend na RPi
    "http://127.0.0.1:5173",         # alternativa pro vývoj
    "http://100.115.134.119:5173",       # produkční frontend vzdálený přístup
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # seznam povolených originů
    allow_credentials=True,
    allow_methods=["*"],            # povol všechny metody (GET, POST, atd.)
    allow_headers=["*"],            # povol všechny hlavičky
)
app.include_router(router)
app.include_router(router_UART)
app.include_router(router_queue)
app.include_router(router_service)
app.include_router(router_glasses)
app.include_router(router_pouring)

# Přidání složky se statickými soubory
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    #asyncio.create_task(uart_listener_loop())
    asyncio.create_task(uart_JSON_listener_loop())

@app.get("/")
def read_root():
    return {"message": "DrinkMaker backend běží!"}

@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/favicon.ico")