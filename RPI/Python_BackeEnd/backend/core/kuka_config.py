# app/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ROBOT_IP: str = os.getenv("ROBOT_IP", "192.168.1.152")
    ROBOT_PORT: int = int(os.getenv("ROBOT_PORT", "7000"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")  # pro tvůj frontend

settings = Settings()
