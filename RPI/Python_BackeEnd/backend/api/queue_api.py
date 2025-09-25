from fastapi import APIRouter
from typing import List
from fastapi import HTTPException

from models.endpoints_classes import Order
from models.endpoints_classes import DrinkName

import services.queue_service as queue_service

router_queue = APIRouter(prefix="/queue", tags=["Queue"])

#Queue
@router_queue.get("/queueList")
def get_queue_list():
    print(f"Požadavek na frontu drinků")
    return queue_service.get_queue()

@router_queue.get("/queueList4")
def get_queue_list_of_4():
    print(f"Požadavek na frontu drinků s maximálně 6 položkami")
    return queue_service.get_queue_of_4_only_name()

@router_queue.post("/addToQueue")
def add_to_queue(order: Order):
    queue_service.add_order(order)
    print(f"Přidání objednávky do fronty: {order}")
    return {"status": "ok", "message": "Přidáno do fronty"}

@router_queue.post("/deleteFullQueue")
def delete_full_queue():
    queue_service.clear_queue()
    print(f"Vymazání fronty drinků")
    return {"status": "ok", "message": "Fronta vymazána"}

@router_queue.get("/numberOfDrinks")
def number_of_drinks():
    number = queue_service.get_number_of_drinks()
    print(f"Počet drinků ve frontě: {number}")
    return {"status": "ok", "count": number}

@router_queue.post("/deleteItemFromQueue")
def delete_item_from_queue(payload: DrinkName):
      queue_service.delete_item_from_queue(payload.name)
      return {"status": "ok", "message": "Položka vymazána z fronty"}

@router_queue.post("/chooseItemFromQueue")
def choose_item_from_queue(payload: DrinkName):
      queue_service.choose_item_from_queue(payload.name)
      return {"status": "ok", "message": "Položka vybrána z fronty a přidána do sklenic"}