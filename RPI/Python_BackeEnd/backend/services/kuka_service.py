# app/robot_driver.py
from __future__ import annotations
import sys, struct, random, socket, threading, time
from typing import Callable, Dict, Optional

ENCODING = "UTF-8"
PY2 = sys.version_info[0] == 2

class OpenShowVar:
    def __init__(self, ip: str, port: int, timeout: float = 3.0):
        self.ip = ip
        self.port = port
        self.msg_id = random.randint(1, 100)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self._lock = threading.Lock()
        self.sock.connect((self.ip, self.port))

    def can_connect(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            ok = s.connect_ex((self.ip, self.port)) == 0
            s.close()
            return ok
        except socket.error:
            return False

    def read(self, var: str, debug: bool = False) -> Optional[bytes]:
        if not isinstance(var, str):
            raise ValueError("Var name must be string")
        varname = var if PY2 else var.encode(ENCODING)
        req = self._pack_read_req(varname)
        with self._lock:
            self.sock.sendall(req)
            rsp = self.sock.recv(256)
        return self._parse_rsp(rsp, debug)

    def write(self, var: str, value: str, debug: bool = False) -> Optional[bytes]:
        if not (isinstance(var, str) and isinstance(value, str)):
            raise ValueError("Var name and value must be strings")
        varname = var if PY2 else var.encode(ENCODING)
        val = value if PY2 else value.encode(ENCODING)
        req = self._pack_write_req(varname, val)
        with self._lock:
            self.sock.sendall(req)
            rsp = self.sock.recv(256)
        return self._parse_rsp(rsp, debug)

    def _pack_read_req(self, varname: bytes) -> bytes:
        var_name_len = len(varname)
        flag = 0
        req_len = var_name_len + 3
        return struct.pack(
            f"!HHBH{var_name_len}s",
            self.msg_id, req_len, flag, var_name_len, varname
        )

    def _pack_write_req(self, varname: bytes, value: bytes) -> bytes:
        var_name_len = len(varname)
        flag = 1
        value_len = len(value)
        req_len = var_name_len + 3 + 2 + value_len
        return struct.pack(
            f"!HHBH{var_name_len}sH{value_len}s",
            self.msg_id, req_len, flag, var_name_len, varname, value_len, value
        )

    def _parse_rsp(self, rsp: bytes, debug: bool = False) -> Optional[bytes]:
        if not rsp:
            return None
        var_value_len = len(rsp) - struct.calcsize("!HHBH") - 3
        result = struct.unpack(f"!HHBH{var_value_len}s3s", rsp)
        _msg_id, _body_len, _flag, _vlen, var_value, isok = result
        if debug:
            print("[DEBUG]", result)
        if isok.endswith(b"\x01") and _msg_id == self.msg_id:
            self.msg_id = (self.msg_id + 1) % 65536
            return var_value
        return None

    def close(self):
        try:
            self.sock.close()
        except:
            pass


class KUKAHandler:
    """Thread-safe wrapper s jednoduchými helpery."""
    def __init__(self):
        self._client: Optional[OpenShowVar] = None
        self._lock = threading.Lock()
        self._connected = False
        self._ip = None
        self._port = None

    def open(self, ip: str, port: int) -> bool:
        with self._lock:
            if self._connected:
                return True
            self._client = OpenShowVar(ip, port)
            self._connected = True
            self._ip, self._port = ip, port
            return True

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected and self._client is not None

    def close(self) -> bool:
        with self._lock:
            if self._client:
                self._client.close()
            self._client = None
            self._connected = False
            return True

    def read_bool(self, var: str) -> bool:
        res = self._read(var)
        if res is None:
            return False
        return res == b"TRUE"

    def read_raw(self, var: str) -> Optional[str]:
        res = self._read(var)
        return res.decode(ENCODING) if res else None

    def write(self, var: str, value) -> bool:
        if not self.is_connected():
            return False
        val_str = str(value)
        with self._lock:
            self._client.write(var, val_str, debug=False)
        return True

    def _read(self, var: str) -> Optional[bytes]:
        if not self.is_connected():
            return None
        with self._lock:
            return self._client.read(var, debug=False)

    # helpers
    def go_home(self, poll_var_fb="PyDomuFb", cmd_var="PyDomu", timeout=30.0, period=0.2) -> bool:
        """Sepne PyDomu=TRUE, čeká na PyDomuFb, potom oboje shodí na FALSE."""
        if not self.is_connected():
            return False
        self.write(cmd_var, True)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.read_bool(poll_var_fb):
                break
            time.sleep(period)
        else:
            # timeout
            self.write(cmd_var, False)
            return False
        # reset flags
        self.write(cmd_var, False)
        self.write(poll_var_fb, False)
        return True
