# services/input_state.py

class InputState:
    def __init__(self):
        self.reset()
        self.reset_mode()

        self.mode_map = {
            1: "STAND BY",
            2: "STOP",
            3: "CHECKING",
            4: "POURING",
            5: "SERVICE",
            6: "UPDATING"
        }

    def reset(self):
        self.position_check = [False] * 6
        self.glass_done = [False] * 6
        self.empty_bottle = [False] * 6
        self.pouring_done = False
        self.mess_error = False
        self.cannot_process_position = False
        self.cannot_process_glass = False
        self.cannot_set_mode = False
        self.emergency_stop = False
    
    def reset_mode(self):
        self.current_mode = None
    
    def update_mode_from_json(self, msg: dict):
        mode_number = msg.get("State", None)

        if mode_number in self.mode_map:
            self.current_mode = self.mode_map[mode_number]
    
    def set_standby_mode(self):
        mode_number = 1

        if mode_number in self.mode_map:
            self.current_mode = self.mode_map[mode_number]

    def update_from_json(self, msg: dict):
        for i in range(6):
            self.position_check[i] = msg.get(f"position_{i}_check", self.position_check[i])
            self.glass_done[i] = msg.get(f"glassDone_{i}", self.glass_done[i])
            self.empty_bottle[i] = msg.get(f"emptyBottleAtPosition_{i}", self.empty_bottle[i])

        self.pouring_done = msg.get("pouringDone", self.pouring_done)
        self.mess_error = msg.get("messError", self.mess_error)
        self.cannot_process_position = msg.get("cannotProcessPosition", self.cannot_process_position)
        self.cannot_process_glass = msg.get("cannotProcessGlass", self.cannot_process_glass)
        self.cannot_set_mode = msg.get("cannotSetMode", self.cannot_set_mode)
        self.emergency_stop = msg.get("emergencyStopAppeared", self.emergency_stop)

    def mode_return(self):
        return self.current_mode

    def to_dict(self):
        return {
            "position_check": self.position_check,
            "glass_done": self.glass_done,
            "empty_bottle": self.empty_bottle,
            "pouring_done": self.pouring_done,
            "mess_error": self.mess_error,
            "cannot_process_position": self.cannot_process_position,
            "cannot_process_glass": self.cannot_process_glass,
            "cannot_set_mode": self.cannot_set_mode,
            "emergency_stop": self.emergency_stop
        }
