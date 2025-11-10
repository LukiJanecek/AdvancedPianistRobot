# services/kuka_service.py
from __future__ import annotations
from typing import Optional, Tuple, Any
import sys
import struct
import random
import socket
import threading, time, sys
import asyncio

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
                return self.read(var)
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
        self.lock = asyncio.Lock()
        self.connected = False
        self.ipAddress = ipAddress
        self.port = port
        self.client = None
        
    async def KUKA_Open(self):
        async with self.lock:
            if self.connected == False:
                print(f"[KUKA] Attempting to connect to robot at {self.ipAddress}:{self.port}...")
                self.client = await asyncio.to_thread(openshowvar, self.ipAddress, self.port)
                res = await asyncio.to_thread(self.client.test_connection)

                if res == True:
                    print('[KUKA] Connection is established!')
                    self.connected = True
                    return True
                else:
                    print('[KUKA] Connection is broken! Check configuration or restart C3_Server at KUKA side.')
                    self.connected = False
                    return False
            else:
                print('[KUKA] Connection is ready!')
                return True
    
    async def KUKA_IsConnected(self):
        async with self.lock:
            return self.connected

    async def KUKA_ReadVar(self, var):
        if await self.KUKA_IsConnected():
            res = await asyncio.to_thread(self.client.read, var, False)
            if res == b'TRUE':
                return True
            elif res == b'FALSE':
                return False
            return res
        return False  
        
    async def KUKA_WriteVar(self, var, value):
        if await self.KUKA_IsConnected():
            await asyncio.to_thread(self.client.KUKA_WriteVar, var, str(value))
            return True
        return False

    async def KUKA_Close(self):
        async with self.lock:
            if self.connected:
                self.client.close()
                self.connected = False
                return True
            else:
                return False

    async def go_to_set_of_notes(self, poll_var_fb, cmd_var, timeout=10.0, period=0.2) -> bool:
        if not await self.KUKA_IsConnected():
            return False
        await self.KUKA_WriteVar(cmd_var, True)

        t0 = time.time()
        while time.time() - t0 < timeout:
            if await self.KUKA_ReadVar(poll_var_fb):
                break
            await asyncio.sleep(period)
        else:
            await self.KUKA_WriteVar(cmd_var, False)
            return False
        # reset flags
        await self.KUKA_WriteVar(cmd_var, False)
        await self.KUKA_WriteVar(poll_var_fb, False)
        return True

    async def play_note(self, note_number, duration=10000, timeout=10.0, period=0.2, ack_var: str = "PyGoToNoteFb") -> bool:
        if not await self.KUKA_IsConnected():
            return False
        
        t0 = time.time()
        ok = False
        try:
            await self.KUKA_WriteVar("PyNoteNumber", int(note_number))
            await self.KUKA_WriteVar("PyNoteDuration", int(duration))
            await self.KUKA_WriteVar("PyGoToNote", True)

            while time.time() - t0 < timeout:
                try:
                    if await self.KUKA_ReadVar(ack_var):
                        ok = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(period)
            return ok
        except Exception:
            return False
        finally:
            try: await self.KUKA_WriteVar("PyGoToNote", False)
            except Exception: pass
            try: await self.KUKA_WriteVar("PyNoteNumber", 0)
            except Exception: pass
            try: await self.KUKA_WriteVar("PyNoteNumberFb", False)
            except Exception: pass


    async def play_song(self, song_number, timeout=30.0, period=0.2) -> bool:
        if song_number not in SONG_MAP:
            raise ValueError(f"Unknown song number: {song_number}")
        song = SONG_MAP[song_number]

        if not await self.KUKA_IsConnected():
            return False

        await self.KUKA_WriteVar(song, True)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if await self.KUKA_ReadVar("PyPlayingSong"):
                break
            await asyncio.sleep(period)
        else:
            await self.KUKA_WriteVar(song, False)
            return False

        await self.KUKA_WriteVar(song, False)
        return True


    async def start_shadow_mode(self, timeout=30.0, period=0.2) -> bool:
        if not await self.KUKA_IsConnected():
            return False
        
        await self.KUKA_WriteVar("PyShadow", True)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if await self.KUKA_ReadVar("PyShadowFb") == True:
                break
            await asyncio.sleep(period)
        else:
            await self.KUKA_WriteVar("PyShadow", False)
            await self.KUKA_WriteVar("PyShadowFb", False)
            return False
        return True
    

    async def stop_shadow_mode(self, timeout=30.0, period=0.2) -> bool:
        if not await self.KUKA_IsConnected():
            return False
        
        await self.KUKA_WriteVar("PyShadow", False)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if await self.KUKA_ReadVar("PyShadowFb") != True:
                break
            await asyncio.sleep(period)
        else:
            await self.KUKA_WriteVar("PyShadow", False)
            await self.KUKA_WriteVar("PyShadowFb", False)
            return False
        return True
    
    async def get_robot_state(self):
        """
        Zjistí aktuální stav robota podle proměnných PyShadow a PySong.
        Vrací dict např. {"status": "shadow"} nebo {"status": "song"} nebo {"status": "idle"}.
        """
        if not await self.KUKA_IsConnected():
            return {"status": "error", "detail": "Not connected"}
        
        try:
            is_shadow = await self.KUKA_ReadVar("PyShadowFb")
            is_song = await self.KUKA_ReadVar("PyPlayingSong")

            if is_shadow is True:
                return {"status": "shadow"}
            elif is_song is True:
                return {"status": "song"}
            else:
                return {"status": "idle"}

        except Exception as e:
            print(f"[KUKA] Chyba při čtení statusu: {e}")
            return {"status": "error", "detail": str(e)}
    

    # Asynchronní smyčka pro čtení klávesy a pozice (spojení obou předchozích)
    async def key_and_position_loop_for_CPP(self):
        """
        Nekonečná smyčka pro periodické čtení hodnoty PyKey a Z pozice robota.
        Lze spustit přes: asyncio.create_task(robot.key_and_position_loop()).
        """
        print("[KUKA] Spouštím key_and_position_loop...")

        key_last = None

        try:
            while True:
                # 1) Ověřit připojení
                if not await self.KUKA_IsConnected():
                    print("[KUKA] Není připojení - čekám na reconnect...")
                    await asyncio.sleep(2)
                    continue

                try:
                    # 2) Čtení klávesy
                    key = await self.KUKA_ReadVar("PyKey")
                    if key != key_last:
                        print(f"[KUKA] Hodnota key: {key}")
                        key_last = key

                    # 3) Čtení Z pozice
                    z_pos = await self.KUKA_ReadVar("PyZposFb")  # nebo "Z_posFb" podle toho, co máš v KRL

                    if isinstance(z_pos, (int, float)):
                        # můžeš si zvolit podmínku – např. > 0 nebo vždy logovat
                        if z_pos > 0:
                            print(f"[KUKA] Z position: {z_pos}")
                        # jinak klidně:
                        # print(f"[KUKA] Z position: {z_pos}")
                    else:
                        # volitelný debug, když přijde něco divného
                        # print(f"[KUKA] Neočekávaný typ Z pozice: {z_pos}")
                        pass

                except Exception as inner_e:
                    print(f"[KUKA] Chyba při čtení PyKey/Zpos: {inner_e}")

                # 4) Interval mezi čteními
                await asyncio.sleep(0.12)

        except asyncio.CancelledError:
            print("[KUKA] key_and_position_loop ukončena (Cancelled).")
        except Exception as e:
            print(f"[KUKA] Neočekávaná chyba v key_and_position_loop: {e}")

    # Asynchronní smyčka pro připojení k robotu
    async def autoconnecting_loop(self):
        print("[KUKA] Spuštím autoconnecting loop...")
        while True:
            try:
                if not await self.KUKA_IsConnected():
                    ok = await self.KUKA_Open()
                    if ok:
                        print(f"[KUKA] Connected to robot at {self.ipAddress}:{self.port}")
                    else:
                        print("[KUKA] Connect to robot failed.. retrying in 10s")
                        await asyncio.sleep(10)
                        continue
                    
                await asyncio.sleep(10)

            except Exception as e:
                print(f"[KUKA] Connect failed: {e}")