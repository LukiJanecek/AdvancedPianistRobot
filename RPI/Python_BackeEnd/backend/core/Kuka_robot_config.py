# app/core/robot.py
from services.kuka_service import KUKA_Handler

robot = KUKA_Handler('192.168.1.152', 7000)
