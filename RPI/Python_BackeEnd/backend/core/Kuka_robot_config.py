# app/core/robot.py
from services.kuka_service import KUKA_Handler

#192.168.1.152

robot = KUKA_Handler('192.168.1.15', 7000)
