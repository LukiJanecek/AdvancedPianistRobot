# services/kuka_service.py
from __future__ import annotations
from typing import Optional, Tuple, Any
import sys
import struct
import random
import socket
import threading, time, sys

NOTE_MAP: dict[int, Tuple[str, str]] = {
    60: ("PyTone60Fb", "PyTone60"),
    61: ("PyTone61Fb", "PyTone61"),
    62: ("PyTone62Fb", "PyTone62"),
    # ...
}

SONG_MAP: dict[int, Tuple[str, str]] = {
    1: ("PyREGGAEFb", "PyREGGAE"),
    2: ("PySTUPNICEFb", "PySTUPNICE"),
    3: ("PyBEETHOVENFb", "PyBEETHOVEN"),
}

ENCODING = "UTF-8"
PY2 = sys.version_info[0] == 2

class openshowvar(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.msg_id = random.randint(1, 100)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.retry = 0
        self.retry_limit = 5
        try:
            self.sock.connect((self.ip, self.port))
        except socket.error:
            pass

    def test_connection(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            ret = sock.connect_ex((self.ip, self.port))
            return ret == 0
        except socket.error:
            print('socket error')
            return False

    can_connect = property(test_connection)

    def read(self, var, debug=True):
        try:
            if not isinstance(var, str):
                raise Exception('Var name is array string')
            else:
                self.varname = var if PY2 else var.encode(ENCODING)
            return self._read_var(debug)
        except:
            self.retry += 1
            if self.retry != self.retry_limit:
                print('read error, ' + str(self.retry) + ' - try')
                self.read(var)
            else:
                print('read error, socket closed')
                self.retry = 0
                self.close()
                return

    def KUKA_WriteVar(self, var, value, debug=False):
        if not (isinstance(var, str) and isinstance(value, str)):
            raise Exception('Var name and its value should be string')
        self.varname = var if PY2 else var.encode(ENCODING)
        self.value = value if PY2 else value.encode(ENCODING)
        return self._KUKA_WriteVar_var(debug)

    def _read_var(self, debug):
        req = self._pack_read_req()
        self._send_req(req)
        _value = self._read_rsp(debug)
        if debug:
            print(_value)
        return _value

    def _KUKA_WriteVar_var(self, debug):
        req = self._pack_KUKA_WriteVar_req()
        self._send_req(req)
        _value = self._read_rsp(debug)
        if debug:
            print(_value)
        return _value

    def _send_req(self, req):
        self.rsp = None
        self.sock.sendall(req)
        self.rsp = self.sock.recv(256)

    def _pack_read_req(self):
        var_name_len = len(self.varname)
        flag = 0
        req_len = var_name_len + 3

        return struct.pack(
            '!HHBH' + str(var_name_len) + 's',
            self.msg_id,
            req_len,
            flag,
            var_name_len,
            self.varname
        )

    def _pack_KUKA_WriteVar_req(self):
        var_name_len = len(self.varname)
        flag = 1
        value_len = len(self.value)
        req_len = var_name_len + 3 + 2 + value_len

        return struct.pack(
            '!HHBH' + str(var_name_len) + 's' + 'H' + str(value_len) + 's',
            self.msg_id,
            req_len,
            flag,
            var_name_len,
            self.varname,
            value_len,
            self.value
        )

    def _read_rsp(self, debug=False):
        if self.rsp is None: return None
        var_value_len = len(self.rsp) - struct.calcsize('!HHBH') - 3
        result = struct.unpack('!HHBH' + str(var_value_len) + 's' + '3s', self.rsp)
        _msg_id, body_len, flag, var_value_len, var_value, isok = result
        if debug:
            print('[DEBUG]', result)
        if result[-1].endswith(b'\x01') and _msg_id == self.msg_id:
            self.msg_id = (self.msg_id + 1) % 65536  # format char 'H' is 2 bytes long
            return var_value

    def close(self):
        self.sock.close()


class KUKA_Handler:
    def __init__(self, ipAddress, port):
        self.connected = False
        self.ipAddress = ipAddress
        self.port = port
        self.client = None
        self.lock = threading.Lock()

    def KUKA_Open(self):
        with self.lock:
            if self.connected == False:
                self.client = openshowvar(self.ipAddress, self.port)
                res = self.client.can_connect

                if res == True:
                    print('Connection is established!')
                    self.connected = True
                    return True
                else:
                    print('Connection is broken! Check configuration or restart C3_Server at KUKA side.')
                    self.connected = False
                    return False
            else:
                print('Connection is ready!')
    
    def KUKA_IsConnected(self):
        with self.lock:
            return self.connected

    def KUKA_ReadVar(self, var):
        if self.connected:
            res = self.client.read(var, debug=False)
            if res == b'TRUE':
                return True
            elif res == b'FALSE':
                return False
            else:
                return res
        else:
            return False

    def KUKA_WriteVar(self, var, value):
        if self.connected:
            self.client.KUKA_WriteVar(var, str(value))
            return True
        else:
            return False

    def KUKA_Close(self):
        with self._lock:
            if self.connected == True:
                self.client.close()
                self.connected = False
                return True

            else:
                return False

    def go_to_set_of_notes(self, poll_var_fb, cmd_var, timeout=10.0, period=0.2) -> bool:
        if not self.KUKA_IsConnected():
            return False
        self.KUKA_WriteVar(cmd_var, True)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.KUKA_ReadVar(poll_var_fb):
                break
            time.sleep(period)
        else:
            self.KUKA_WriteVar(cmd_var, False)
            return False
        # reset flags
        self.KUKA_WriteVar(cmd_var, False)
        self.KUKA_WriteVar(poll_var_fb, False)
        return True

    def play_note(self, note_number, duration=10000, timeout=10.0, period=0.2, ack_var: str = "PyGoToNoteFb") -> bool:
        if not self.KUKA_IsConnected():
            return False
        
        t0 = time.time()
        ok = False
        
        try:
            # Příprava a start
            self.KUKA_WriteVar("PyNoteNumber", int(note_number))
            self.KUKA_WriteVar("PyNoteDuration", int(duration))
            self.KUKA_WriteVar("PyGoToNote", True)

            # Čekání na potvrzení z KRL
            while time.time() - t0 < timeout:
                try:
                    if self.KUKA_ReadVar(ack_var):
                        ok = True
                        break
                except Exception:
                    pass
                time.sleep(period)
            return ok
        except Exception:
            return False
        finally:
            try: self.KUKA_WriteVar("PyGoToNote", False)
            except Exception: pass
            try: self.KUKA_WriteVar("PyNoteNumber", 0)
            except Exception: pass
            try: self.KUKA_WriteVar("PyNoteNumberFb", False)
            except Exception: pass


    def play_song(self, song_number, timeout=30.0, period=0.2) -> bool:
        if song_number not in SONG_MAP:
            raise ValueError(f"Unknown song number: {song_number}")
        poll_var_fb, cmd_var = SONG_MAP[song_number]
        if not self.KUKA_IsConnected():
            return False

        self.KUKA_WriteVar(cmd_var, True)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.KUKA_ReadVar(poll_var_fb):
                break
            time.sleep(period)
        else:
            self.KUKA_WriteVar(cmd_var, False)
            return False

        self.KUKA_WriteVar(cmd_var, False)
        self.KUKA_WriteVar(poll_var_fb, False)
        return True

    def start_shadowing(self, poll_var_fb="PyShadowFb", cmd_var="PyShadow", timeout=30.0, period=0.2) -> bool:
        if not self.KUKA_IsConnected():
            return False
        self.KUKA_WriteVar(cmd_var, True)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.KUKA_ReadVar(poll_var_fb):
                break
            time.sleep(period)
        else:
            self.KUKA_WriteVar(cmd_var, False)
            return False

        self.KUKA_WriteVar(cmd_var, False)
        self.KUKA_WriteVar(poll_var_fb, False)
        return True
