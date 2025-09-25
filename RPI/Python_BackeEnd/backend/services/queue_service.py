from models.endpoints_classes import Order
from typing import List, Optional

from core.all_states import glasses_state

order_queue: List[Order] = []

def add_order(order: Order):
    order_queue.append(order)

def get_queue() -> List[Order]:
    return order_queue

def get_queue_of_4_only_name() -> List[Order]:
    return [order.name for order in order_queue[:4]]

def clear_queue():
    order_queue.clear()

def get_number_of_drinks() -> int:
    return len(order_queue)

def delete_item_from_queue(name: str):
    global order_queue
    order_queue = [order for order in order_queue if order.name != name]
    if not order_queue:
        print("Fronta je nyní prázdná.")
    else:
        print(f"Zbývající položky ve frontě: {[order.name for order in order_queue]}")


def choose_item_from_queue(name: str, preferred_pos: Optional[int] = None):
    global order_queue
    # najdi první objednávku se jménem
    for idx, order in enumerate(order_queue):
        if order.name == name:
            pos_used = glasses_state.set_glass_from_order(order, preferred_pos=preferred_pos)
            if pos_used is not None:
                # úspěch → odeber z fronty
                removed = order_queue.pop(idx)
                print(f"Položka '{removed.name}' byla přidána do sklenice pos_{pos_used} a odebrána z fronty.")
            else:
                print(f"Fronta je, ale žádná volná sklenice pro '{order.name}'.")
            break
    else:
        print(f"Položka '{name}' nebyla nalezena ve frontě.")
    
    if not order_queue:
        print("Fronta je prázdná.")
    else:
        print(f"Zbývající položky ve frontě: {[order.name for order in order_queue]}")