# services/kuka_service.py
from __future__ import annotations
from typing import Optional, Tuple, Any
import sys
import struct
import random
import socket
import threading, time, sys
import asyncio
import re
import os
import errno

from core.PipeLine_config import PIPE_PATH, OFFSET


SONG_MAP: dict[int, str] = {
    1: "PyREGGAE",
    2: "PySTUPNICE",
    3: "PyBEETHOVEN",
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
        self.io_lock = asyncio.Lock()
        self.connected = False
        self.ipAddress = ipAddress
        self.port = port
        self.client = None

        # --- CACHE STAVU ROBOTA ---
        self.state_lock = asyncio.Lock()
        self._state: dict[str, Any] = {
            "status": "error",
            "detail": "Not connected",
        }
        self._state_updated_at: float | None = None
        
        # --- INFO O AKTUÁLNÍ PÍSNI (z WebSocketu) ---
        self.song_lock = asyncio.Lock()
        self.current_song_number: int | None = None
        
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
        

    # --- Helper: log fronty čtení/zápisu ---
    async def _queue_log(self, action: str, var: str):
        """
        Vypíše informaci o frontě:
        - zda čekáme na io_lock
        - zda nyní probíhá akce
        """
        locked = self.io_lock.locked()
        if locked:
            print(f"[KUKA][QUEUE] {action} {var}: čekám ve frontě (io_lock = BUSY)")
        #else:
            #print(f"[KUKA][QUEUE] {action} {var}: zámek volný, provádím hned")


    async def KUKA_ReadVar(self, var: str, retries: int = 3, delay: float = 0.05):
        if not self.connected:
            print(f"[KUKA][READ] Robot není připojený, nemůžu číst {var}")
            return None

        await self._queue_log("ČTENÍ", var)

        last_exc: Exception | None = None

        # FRONTOVANÉ — čeká na io_lock
        async with self.io_lock:
            #print(f"[KUKA][READ] >>> Začínám čtení {var}")

            for attempt in range(1, retries + 1):

                try:
                    res = await asyncio.to_thread(self.client.read, var, False)

                    if res is not None:
                        #print(f"[KUKA][READ] <<< HOTOVO {var} = {res}")
                        return True if res == b"TRUE" else False if res == b"FALSE" else res

                except Exception as e:
                    print(f"[KUKA][READ] Výjimka při čtení {var}: {e}")
                    last_exc = e

                await asyncio.sleep(delay)

        print(f"[KUKA][READ] !!! SELHÁNÍ čtení {var} po {retries} pokusech")
        return None

 
        
    async def KUKA_WriteVar(self, var: str, value, retries: int = 3) -> bool:
        if not self.connected:
            print(f"[KUKA][WRITE] Není připojeno, nemůžu zapisovat {var}={value}")
            return False

        value_str = str(value)
        await self._queue_log("ZÁPIS", var)

        last_exc = None

        # FRONTOVANÉ — čeká na io_lock
        async with self.io_lock:
            #print(f"[KUKA][WRITE] >>> Začínám zápis {var} = {value_str}")

            for attempt in range(1, retries + 1):

                try:
                    res = await asyncio.to_thread(self.client.KUKA_WriteVar, var, value_str)

                    if res is not None:
                        #print(f"[KUKA][WRITE] <<< HOTOVO {var}={value_str}")
                        return True

                except Exception as e:
                    print(f"[KUKA][WRITE] Výjimka při zápisu {var}: {e}")
                    last_exc = e

                await asyncio.sleep(0.05)

        print(f"[KUKA][WRITE] !!! SELHÁNÍ zápisu {var}={value_str} po {retries} pokusech")
        return False


  
    async def KUKA_Close(self):
        async with self.lock:
            if self.connected:
                self.client.close()
                self.connected = False
                return True
            else:
                return False


    async def play_note(self, note_number=-256, duration=7000, timeout=10.0, period=0.2, ack_var: str = "PyGoToNoteFb") -> bool:
        if not await self.KUKA_IsConnected():
            return False
        
        t0 = time.time()
        ok = False
        try:
            await self.KUKA_WriteVar("PyGoToNote", int(note_number))
            await self.KUKA_WriteVar("PyNoteDuration", int(duration))

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
            return False
        return True
    

    async def stop_shadow_mode(self, timeout=30.0, period=0.2) -> bool:
        if not await self.KUKA_IsConnected():
            return False
        
        await self.KUKA_WriteVar("PyShadow", False)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if await self.KUKA_ReadVar("PyShadowFb") == False:
                break
            await asyncio.sleep(period)
        else:
            return False
        return True
    
    async def play_and_track(self, song_num: int):
        # uložíme číslo aktuálního songu
        await self.set_current_song(song_num)
        await self.play_song(song_number=song_num)

    async def set_current_song(self, song_number: int | None):
        async with self.song_lock:
            self.current_song_number = song_number

    async def get_current_song(self) -> int | None:
        async with self.song_lock:
            return self.current_song_number

    
    async def _update_state_from_robot(self):
        """
        Interní helper – jednorázově načte stav z robota a uloží ho do cache.
        Volá se jen z periodické smyčky (status_poll_loop), ne z REST endpointu.
        """
        if not await self.KUKA_IsConnected():
            async with self.state_lock:
                prev_status = self._state.get("status")
                self._state = {"status": "error", "detail": "Not connected"}
                self._state_updated_at = time.time()
            # když ztratíme spojení, vynuluj song
            if prev_status == "song":
                await self.set_current_song(None)
            return

        try:
            is_shadow = await self.KUKA_ReadVar("PyShadowFb")
            is_song = await self.KUKA_ReadVar("PyPlayingSong")

            if is_shadow is True:
                new_state = {"status": "shadow"}
            elif is_song is True:
                new_state = {"status": "song"}
            else:
                new_state = {"status": "idle"}

        except Exception as e:
            print(f"[KUKA] Chyba při čtení statusu (poll): {e}")
            new_state = {"status": "error", "detail": str(e)}

        async with self.state_lock:
            prev_status = self._state.get("status")
            self._state = new_state
            self._state_updated_at = time.time()

        # pokud jsme byli "song" a už nejsme -> vynulovat current_song_number
        if prev_status == "song" and new_state.get("status") != "song":
            await self.set_current_song(None)
    
    async def get_robot_state(self):
        """
        NEVOLÁ přímo robota – jen vrací poslední známý stav,
        který si pravidelně aktualizuje status_poll_loop().
        """
        async with self.state_lock:
            state_copy = dict(self._state)
            ts = self._state_updated_at

        if ts is not None:
            state_copy["updated_at"] = ts
        else:
            state_copy.setdefault("detail", "State not yet polled")

        return state_copy


    @staticmethod
    def extract_pose(pos_value: Any) -> Optional[dict[str, float]]:
        """
        Z hodnoty E6POS (string/bytes) vytáhne X, Y, Z, A, B, C jako dict.
        Např.:
          b"{E6POS: X 281.27, Y -107.82, Z 624.03, A -16.37, B -44.12, C 173.61, ...}"
        → {"X": 281.27, "Y": -107.82, "Z": 624.03, "A": -16.37, "B": -44.12, "C": 173.61}
        """
        if isinstance(pos_value, (bytes, bytearray)):
            pos_str = pos_value.decode(ENCODING, errors="ignore")
        else:
            pos_str = str(pos_value)

        axes = ("X", "Y", "Z", "A", "B", "C")
        pose: dict[str, float] = {}

        for axis in axes:
            m = re.search(rf"{axis}\s*([-+]?\d*\.?\d+)", pos_str)
            if m:
                try:
                    pose[axis] = float(m.group(1))
                except ValueError:
                    # ignoruj tuto osu, ale nevyhoď celou pozici
                    pass

        return pose or None

    # Asynchronní smyčka pro čtení klávesy a pozice (spojení obou předchozích)
    async def key_and_position_loop_for_CPP(self):

        print("[KUKA][KEYPOSLOOP] Spouštím key_and_position_loop...")
        
        last_alive = time.time()

        try:
            # ------------------------------------------------------------
            #  MKFIFO vytvoř jen na Linuxu
            #  (Windows mkfifo NEumí → jen přeskočit, smyčka normálně běží)
            # ------------------------------------------------------------
            if os.name != "nt":   # nt = Windows, posix = Linux/macOS
                if not os.path.exists(PIPE_PATH):
                    try:
                        os.mkfifo(PIPE_PATH)
                        print(f"[KUKA][KEYPOSLOOP] Vytvořeno FIFO: {PIPE_PATH}")
                    except FileExistsError:
                        pass
                    except OSError as e:
                        print(f"[KUKA][KEYPOSLOOP] mkfifo selhalo: {e}")
            else:
                print("[KUKA][KEYPOSLOOP] Windows detekován → mkfifo se přeskočí (OK).")

            while True:
                
                '''
                # --- každých 5 sekund vypiš hlášku ---
                if time.time() - last_alive >= 5:
                    print("[KUKA][KEYPOSLOOP] Keyposloop stále běží...")
                    last_alive = time.time()
                # -------------------------------------¨
                '''
                
                # 1) Ověřit připojení
                if not await self.KUKA_IsConnected():
                    print("[KUKA][KEYPOSLOOP] Robot není připojený - čekám na reconnect...")
                    await asyncio.sleep(2)
                    continue

                try:
                    # --- TADY: čtení $POS_ACT s retriem uvnitř KUKA_ReadVar ---
                    pos_raw = await self.KUKA_ReadVar("$POS_ACT")

                    # Když se to ani po retriích nepovedlo, KUKA_ReadVar už zalogoval detail
                    if pos_raw is None:
                        # jen pauza a další pokus v další iteraci smyčky
                        await asyncio.sleep(0.12)
                        continue

                    # Pokud je to bool (True/False), není to platný string s pozicí
                    if isinstance(pos_raw, bool):
                        print(f"[KUKA][KEYPOSLOOP] VAROVÁNÍ: $POS_ACT vrátil bool: {pos_raw} -> přeskočeno")
                        await asyncio.sleep(0.12)
                        continue

                    # prázdný string / nesmysl
                    if not pos_raw:
                        await asyncio.sleep(0.30)
                        continue

                    pose = self.extract_pose(pos_raw)
                    
                    if pose is not None:
                        z_pos = pose.get("Z")
                        if z_pos is not None:
                            #print(f"[KUKA][KEYPOSLOOP] Z position: {z_pos:.3f}")
                            if z_pos < 0:
                                print(f"[KUKA][KEYPOSLOOP] Robot je dole (Z={z_pos:.3f})")

                                # --- NOVĚ: nejdřív zjistíme, jestli se hraje song z naší cache ---
                                state = await self.get_robot_state()
                                playing_song = state.get("status") == "song"

                                if playing_song:
                                    # využij číslo songu z WebSocketu
                                    song_number = await self.get_current_song()

                                    if song_number is None:
                                        print("[KUKA][KEYPOSLOOP] status='song', ale current_song_number=None -> nic neposílám")
                                        await asyncio.sleep(0.12)
                                        continue

                                    try:
                                        fd = os.open(PIPE_PATH, os.O_WRONLY | os.O_NONBLOCK)
                                        with os.fdopen(fd, "w") as pipe:
                                            print(f"[KUKA][KEYPOSLOOP][PIPELINE] Odesílám ČÍSLO SONGU z WS: {song_number}")
                                            pipe.write(f"{song_number}\n")
                                    except OSError as e:
                                        if e.errno == errno.ENXIO:
                                            print("[KUKA][KEYPOSLOOP][PIPELINE] Nikdo nečte FIFO (daemon asi neběží), song se neodeslal.")
                                        else:
                                            print(f"[KUKA][KEYPOSLOOP][PIPELINE] Chyba při zápisu songu do FIFO: {e}")

                                    await asyncio.sleep(0.12)
                                    continue  # při songu už neřešíme klávesy

                                # --- PŮVODNÍ LOGIKA PRO KLÁVESY, když song NEhraje ---
                                key = await self.KUKA_ReadVar("PyKey")
                                print(f"[KUKA][KEYPOSLOOP] Hodnota key: {key}")

                                # 1) Když je None → nic neposílej, jen log
                                if key is None:
                                    print("[KUKA][KEYPOSLOOP] PyKey je None -> přeskočeno (žádná klávesa?)")
                                    await asyncio.sleep(0.12)
                                    continue

                                # 2) Když je to prázdný string
                                if isinstance(key, str) and key.strip() == "":
                                    print("[KUKA][KEYPOSLOOP] PyKey je prázdný string -> přeskočeno")
                                    await asyncio.sleep(0.12)
                                    continue

                                # 3) Když je to bool (true/false z KRL)
                                if isinstance(key, bool):
                                    print(f"[KUKA][KEYPOSLOOP] PyKey je bool ({key}) -> neočekávané, přeskočeno")
                                    await asyncio.sleep(0.12)
                                    continue

                                try:
                                    if isinstance(key, (bytes, bytearray)):
                                        key_str = key.decode().strip()
                                    else:
                                        key_str = str(key).strip()

                                    if "." in key_str:
                                        key_int = int(float(key_str))   # např. "12.0000" -> 12
                                    else:
                                        key_int = int(key_str)

                                    if not (1 <= key_int <= 22):
                                        print(f"[KUKA][KEYPOSLOOP] PyKey ({key_int}) mimo rozsah -> přeskočeno")
                                        await asyncio.sleep(0.12)
                                        continue

                                    shifted = key_int + (key_int-1) + OFFSET

                                except (ValueError, TypeError) as e:
                                    print(f"[KUKA][KEYPOSLOOP] Neplatná hodnota PyKey ({key}): {e}")
                                    shifted = None

                                if shifted is not None:
                                    try:
                                        fd = os.open(PIPE_PATH, os.O_WRONLY | os.O_NONBLOCK)
                                        with os.fdopen(fd, "w") as pipe:
                                            print(f"[KUKA][KEYPOSLOOP][PIPELINE] Odesílání klávesy: {shifted}")
                                            pipe.write(f"{shifted}\n")
                                    except OSError as e:
                                        if e.errno == errno.ENXIO:
                                            print("[KUKA][KEYPOSLOOP][PIPELINE] Nikdo nečte FIFO (daemon asi neběží), klávesa se neodeslala.")
                                        else:
                                            print(f"[KUKA][KEYPOSLOOP][PIPELINE] Chyba při zápisu do FIFO: {e}")

                        else:
                            print(f"[KUKA][KEYPOSLOOP] V parsed pose chybí Z: {pose}")
                    else:
                        print(f"[KUKA][KEYPOSLOOP] Nelze parsovat pozici z: {pos_raw}")

                except Exception as inner_e:
                    print(f"[KUKA][KEYPOSLOOP] Chyba při čtení PyKey/Zpos: {inner_e}")

                # 4) Interval mezi čteními
                await asyncio.sleep(0.30)

        except asyncio.CancelledError:
            print("[KUKA][KEYPOSLOOP] key_and_position_loop ukončena (Cancelled).")
        except Exception as e:
            print(f"[KUKA][KEYPOSLOOP] Neočekávaná chyba v key_and_position_loop: {e}")


    # Asynchronní smyčka pro připojení k robotu
    async def autoconnecting_loop(self):
        print("[KUKA][AUTOCONNECT] Spuštím autoconnecting loop...")
        while True:
            try:
                if not await self.KUKA_IsConnected():
                    ok = await self.KUKA_Open()
                    if ok:
                        print(f"[KUKA][AUTOCONNECT] Připojeno k robotovi na {self.ipAddress}:{self.port}")
                    else:
                        print("[KUKA][AUTOCONNECT] Připojení selhalo.. opakuju za 10s")
                        await asyncio.sleep(10)
                        continue
                    
                await asyncio.sleep(10)

            except Exception as e:
                print(f"[KUKA][AUTOCONNECT] Connect failed: {e}")


    async def status_poll_loop(self, interval: float = 0.5):
        """
        Periodicky tahá stav z robota a ukládá ho do cache.
        REST /Kuka/status pak vrací jen tuto cache, nekomunikuje přímo s robotem.
        """
        print("[KUKA][STATUS-POLL] Spouštím status_poll_loop...")
        while True:
            try:
                await self._update_state_from_robot()
            except Exception as e:
                print(f"[KUKA][STATUS-POLL] Neočekávaná chyba při polling stavu: {e}")
                # při chybě aspoň zapíšeme něco do cache
                async with self.state_lock:
                    self._state = {"status": "error", "detail": str(e)}
                    self._state_updated_at = time.time()

            await asyncio.sleep(interval)