# app/config.py
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ROBOT_IP: str = os.getenv("ROBOT_IP", "192.168.1.152")
    ROBOT_PORT: int = int(os.getenv("ROBOT_PORT", "7000"))

settings = Settings()
