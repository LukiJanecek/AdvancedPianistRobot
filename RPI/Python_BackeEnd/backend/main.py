from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

import asyncio
import threading

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
    "http://localhost:8081",      
    "http://127.0.0.1:8081",      
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
async def startup_event():
    #asyncio.create_task(robot.autoconnecting_loop())
    #asyncio.create_task(robot.key_listener_loop())
    print("API server started.")


@app.get("/", include_in_schema=False)
def root_redirect():
    # 302 redirect na /docs (swagger UI)
    return RedirectResponse(url="/docs")

@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/piano.ico")