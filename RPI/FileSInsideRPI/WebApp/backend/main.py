from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

import asyncio
import threading

from api.endpoints_api import router
from api.ws_api import router_ws
from api.kuka_api import router_kuka
from fastapi.openapi.docs import get_swagger_ui_html

from core.Kuka_robot_config import robot

app = FastAPI(
    title="Klavirista API",
    description="Ovládací REST API pro Rpi backend.",
    version="0.0.1",
    openapi_tags=[
        {"name": "General", "description": "Obecná funkce API"},
        {"name": "Kuka", "description": "Funkce pro ovládání KUKA robota"},
        {"name": "WebSocket", "description": "WebSocket komunikace"},
    ],
    docs_url=None, 
    redoc_url=None,
)

# Povolené originy
origins = [
    "http://localhost:8081",
    "http://localhost:80",       
    "http://127.0.0.1:8081",
    "http://192.168.1.104",
    "http://100.105.234.91",      
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


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="Klavirista API - Docs",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",     
        swagger_favicon_url="/static/piano.ico",      
    )


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(robot.autoconnecting_loop())
    asyncio.create_task(robot.key_and_position_loop_for_CPP())

    print("API server started.")


@app.get("/", include_in_schema=False)
def root_redirect():
    return RedirectResponse(url="/docs")

@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/piano.ico")