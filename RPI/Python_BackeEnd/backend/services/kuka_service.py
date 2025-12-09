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
import select

from core.PipeLine_config import PIPE_PATH, OFFSET, ACK_PIPE_PATH


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

    async def _detect_song_from_krl(self) -> int | None:
        """
        Nová verze – čte jedinou KRL proměnnou PySongNumber,
        která obsahuje číslo aktuálně hrané skladby (1–3).
        Pokud je hodnota mimo rozsah nebo se nepodaří načíst, vrací None.
        """
        try:
            raw = await self.KUKA_ReadVar("PySongNumber")
            #print(f"[KUKA][SONG-DETECT] PySongNumber = {raw!r}")
        except Exception as e:
            print(f"[KUKA][SONG-DETECT] Chyba při čtení PySongNumber: {e}")
            return None

        # ---- parsování výsledku ----
        # může to být int, str, bytes; ochotně to převedeme
        num = None

        if isinstance(raw, int):
            num = raw

        elif isinstance(raw, (bytes, bytearray)):
            try:
                num = int(raw.decode("utf-8", errors="ignore").strip())
            except:
                return None

        elif isinstance(raw, str):
            try:
                num = int(raw.strip())
            except:
                return None

        # ---- validace hodnoty ----
        if num in SONG_MAP:   # např. 1–3
            return num

        return None


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
            shadow_start_raw = await self.KUKA_ReadVar("PyShadowStart")
            shadow_start = (shadow_start_raw is True)

            current_song_num: int | None = None

            # Pokud KUKA říká, že hraje song, zkusíme zjistit, KTERÝ
            if is_song is True:
                current_song_num = await self._detect_song_from_krl()

            if is_shadow is True:
                new_state = {"status": "shadow"}
            elif is_song is True:
                new_state = {"status": "song"}
            else:
                new_state = {"status": "idle"}

            new_state["shadow_start"] = shadow_start

        except Exception as e:
            print(f"[KUKA] Chyba při čtení statusu (poll): {e}")
            new_state = {"status": "error", "detail": str(e)}
            current_song_num = None

        async with self.state_lock:
            prev_status = self._state.get("status")
            self._state = new_state
            self._state_updated_at = time.time()

        # --- práce s current_song_number podle zjištěného stavu ---
        if new_state.get("status") == "song":
            # pokud víme konkrétní song, nastav ho
            await self.set_current_song(current_song_num)
        elif prev_status == "song" and new_state.get("status") != "song":
            # přechod ze stavu "song" do jiného → vynulujeme
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


    @staticmethod
    def ensure_fifos():
        """Vytvoří FIFO soubory, pokud neexistují (jen na POSIX systémech)."""
        if os.name == "nt":
            print("[KUKA][KEYPOSLOOP] Windows detected -> FIFOs not created (skipping mkfifo).")
            return

        try:
            if not os.path.exists(PIPE_PATH):
                os.mkfifo(PIPE_PATH, 0o666)
                print(f"[KUKA][KEYPOSLOOP] Created FIFO: {PIPE_PATH}")
        except FileExistsError:
            pass
        except OSError as e:
            print(f"[KUKA][KEYPOSLOOP] mkfifo {PIPE_PATH} failed: {e}")

        try:
            if not os.path.exists(ACK_PIPE_PATH):
                os.mkfifo(ACK_PIPE_PATH, 0o666)
                print(f"[KUKA][KEYPOSLOOP] Created ACK FIFO: {ACK_PIPE_PATH}")
        except FileExistsError:
            pass
        except OSError as e:
            print(f"[KUKA][KEYPOSLOOP] mkfifo {ACK_PIPE_PATH} failed: {e}")

    @staticmethod
    def try_open_ack_pipe():
        """Zkusí otevřít ACK pipe pro čtení non-blocking. Vrací fd nebo None."""
        if os.name == "nt":
            return None
        try:
            fd = os.open(ACK_PIPE_PATH, os.O_RDONLY | os.O_NONBLOCK)
            print("[KUKA][KEYPOSLOOP] Opened ACK pipe for reading.")
            return fd
        except OSError as e:
            print(f"[KUKA][KEYPOSLOOP] Could not open ACK pipe for read now: {e}. Will retry later.")
            return None

    @staticmethod
    def try_open_write_nb():
        """Zkusí otevřít write-end DATA pipe non-blocking. Vrací fd nebo None."""
        try:
            fd = os.open(PIPE_PATH, os.O_WRONLY | os.O_NONBLOCK)
            return fd
        except OSError as e:
            if e.errno in (errno.ENXIO, errno.ENOENT):
                # nikdo nečte, nebo pipe ještě není
                return None
            else:
                print(f"[KUKA][KEYPOSLOOP] open write error: {e}")
                return None

    @staticmethod
    def drain_ack_for_seq(ack_fd, expected_seq: int) -> bool:
        """
        Zkusí non-blocking z ACK fifo vytáhnout ACK:<seq>.
        Jednoduchá verze: přečte až 1024 B, hledá řádky "ACK:<číslo>".
        """
        if ack_fd is None:
            return False

        try:
            rlist, _, _ = select.select([ack_fd], [], [], 0.0)
        except Exception:
            return False

        if not rlist:
            return False

        try:
            data = os.read(ack_fd, 1024)
        except BlockingIOError:
            return False
        except OSError as e:
            print(f"[KUKA][KEYPOSLOOP] ACK read error: {e}")
            return False

        if not data:
            # writer na druhé straně skončil
            return False

        text = data.decode("utf-8", errors="ignore")
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith("ACK:"):
                try:
                    got = int(line.split(":", 1)[1])
                    if got == expected_seq:
                        return True
                except Exception:
                    pass
        return False


    async def send_with_ack(
        self,
        seq: int,
        value: int,
        ack_fd,
        *,
        open_retry_delay: float = 0.05,
        write_retry_delay: float = 0.05,
        ack_timeout: float = 1.0,
        max_retries: int = 3,
    ) -> bool:
        """
        Jednoduchý handshake:
          - pošli 'seq:value\\n' do PIPE_PATH (non-blocking open)
          - čekej na 'ACK:seq' z ACK_PIPE_PATH (přes ack_fd) s timeoutem
          - max_retries opakování
        Vrací True/False podle toho, zda přišel ACK.
        """
        msg = f"{seq}:{value}\n".encode("utf-8")

        attempt = 0
        while attempt < max_retries:
            attempt += 1

            # 1) otevřít write-end neblokující (pokud nikdo nečte, vrátí None)
            wfd = self.try_open_write_nb()
            if wfd is None:
                print(f"[KUKA][KEYPOSLOOP][PIPELINE] No reader for DATA pipe, retry open... (attempt {attempt})")
                await asyncio.sleep(open_retry_delay)
                continue

            try:
                os.write(wfd, msg)
            except Exception as e:
                print(f"[KUKA][KEYPOSLOOP][PIPELINE] write failed (attempt {attempt}): {e}")
            finally:
                try:
                    os.close(wfd)
                except Exception:
                    pass

            # 2) čekání na ACK
            start_wait = time.time()
            while time.time() - start_wait < ack_timeout:
                if self.drain_ack_for_seq(ack_fd, seq):
                    print(f"[KUKA][KEYPOSLOOP][PIPELINE] ACK for seq={seq}, val={value} received (attempt {attempt})")
                    return True
                await asyncio.sleep(0.01)

            print(f"[KUKA][KEYPOSLOOP][PIPELINE] No ACK for seq={seq} (attempt {attempt}), retrying...")
            await asyncio.sleep(write_retry_delay)

        print(f"[KUKA][KEYPOSLOOP][PIPELINE] FAILED to get ACK after {max_retries} attempts for seq={seq}, val={value}")
        return False



    # Asynchronní smyčka pro čtení klávesy a pozice + odesílání do FIFO
    async def key_and_position_loop_for_CPP(self):
        """
        Async loop:
          - vytváří FIFO (DATA + ACK)
          - drží ACK pipe otevřenou pro čtení (non-blocking)
          - při přechodu Z z >=0 na <0 pošle:
              * pokud je status="song" -> číslo aktuálního songu (current_song_number)
              * jinak -> vypočtenou hodnotu klávesy (shifted)
          - při přechodu Z z <0 na >=0 pošle 0
          - každý send jde přes jednoduchý handshake seq:value + ACK:seq
        """
        print("[KUKA] Spouštím key_and_position_loop...")

        # parametry
        HEARTBEAT_INTERVAL = 5.0
        POSE_SLEEP_ON_NONE = 0.12
        POSE_SLEEP_IF_EMPTY = 0.30
        MAIN_CYCLE_SLEEP = 0.15

        last_alive = time.time()
        seq_counter = 0
        was_down = False  # edge detection: jestli byl robot v minulém cyklu dole

        # vytvořit FIFOs
        self.ensure_fifos()

        # otevřít ACK pipe (non-blocking)
        ack_fd = self.try_open_ack_pipe()

        try:
            while True:
                # heartbeat (volitelně)
                # if time.time() - last_alive >= HEARTBEAT_INTERVAL:
                #     print("[KUKA][KEYPOSLOOP] Keyposloop stále běží...")
                #     last_alive = time.time()

                # pokud se ACK pipe zavřela, zkus ji znovu otevřít
                if ack_fd is None and os.name != "nt":
                    ack_fd = self.try_open_ack_pipe()

                # 1) kontrola připojení robota
                if not await self.KUKA_IsConnected():
                    print("[KUKA][KEYPOSLOOP] Není připojení - čekám na reconnect...")
                    await asyncio.sleep(2.0)
                    was_down = False  # bezpečně resetujeme edge stav
                    continue

                try:
                    # čtení aktuální pozice
                    pos_raw = await self.KUKA_ReadVar("$POS_ACT")
                    if pos_raw is None:
                        await asyncio.sleep(POSE_SLEEP_ON_NONE)
                        continue

                    if isinstance(pos_raw, bool):
                        print(f"[KUKA][KEYPOSLOOP] VAROVÁNÍ: $POS_ACT vrátil bool: {pos_raw} -> přeskočeno")
                        await asyncio.sleep(POSE_SLEEP_ON_NONE)
                        continue

                    if not pos_raw:
                        await asyncio.sleep(POSE_SLEEP_IF_EMPTY)
                        continue

                    pose = self.extract_pose(pos_raw)
                    if pose is None:
                        print(f"[KUKA][KEYPOSLOOP] Nelze parsovat pozici z: {pos_raw}")
                        await asyncio.sleep(MAIN_CYCLE_SLEEP)
                        continue

                    z_pos = pose.get("Z")
                    if z_pos is None:
                        print(f"[KUKA][KEYPOSLOOP] V parsed pose chybí Z: {pose}")
                        await asyncio.sleep(MAIN_CYCLE_SLEEP)
                        continue

                    is_down = z_pos < -2

                    # -------------------------------
                    # 1) PŘECHOD NA "DOLŮ"
                    # -------------------------------
                    if is_down and not was_down:
                        print(f"[KUKA][KEYPOSLOOP] -----------------------------------> Robot šel DOLŮ (Z={z_pos:.3f})")

                        # zjistíme, jestli se hraje song z cache
                        state = await self.get_robot_state()
                        playing_song = state.get("status") == "song"

                        if playing_song:
                            # využij číslo songu z WebSocketu / cache
                            song_number = await self.get_current_song()
                            if song_number is None:
                                print("[KUKA][KEYPOSLOOP] status='song', ale current_song_number=None -> neodesílám")
                            else:
                                seq_counter += 1
                                seq = seq_counter
                                value = int(song_number)

                                if ack_fd is None:
                                    print("[KUKA][KEYPOSLOOP][PIPELINE] ACK pipe není otevřená, posílám SONG bez kontroly ACK.")
                                    wfd = self.try_open_write_nb()
                                    if wfd is not None:
                                        try:
                                            os.write(wfd, f"{seq}:{value}\n".encode("utf-8"))
                                            print(f"[KUKA][KEYPOSLOOP][PIPELINE] Odeslán song (bez ACK): {value} (seq={seq})")
                                        except Exception as e:
                                            print(f"[KUKA][KEYPOSLOOP][PIPELINE] write SONG bez ACK selhalo: {e}")
                                        finally:
                                            try:
                                                os.close(wfd)
                                            except Exception:
                                                pass
                                    else:
                                        print("[KUKA][KEYPOSLOOP][PIPELINE] Nikdo nečte DATA pipe, song se neodeslal.")
                                else:
                                    await self.send_with_ack(
                                        seq,
                                        value,
                                        ack_fd,
                                        open_retry_delay=0.05,
                                        write_retry_delay=0.05,
                                        ack_timeout=1.0,
                                        max_retries=3,
                                    )
                                    print(f"[KUKA][KEYPOSLOOP][PIPELINE] Odeslán song přes ACK-pipeline: {value} (seq={seq})")

                        else:
                            # --- LOGIKA PRO KLÁVESY, když song NEhraje ---
                            key = await self.KUKA_ReadVar("PyKey")
                            print(f"[KUKA][KEYPOSLOOP] Hodnota key: {key}")

                            if key is None:
                                print("[KUKA][KEYPOSLOOP] PyKey je None -> přeskočeno (žádná klávesa?)")
                            elif isinstance(key, str) and key.strip() == "":
                                print("[KUKA][KEYPOSLOOP] PyKey je prázdný string -> přeskočeno")
                            elif isinstance(key, bool):
                                print(f"[KUKA][KEYPOSLOOP] PyKey je bool ({key}) -> neočekávané, přeskočeno")
                            else:
                                try:
                                    if isinstance(key, (bytes, bytearray)):
                                        key_str = key.decode().strip()
                                    else:
                                        key_str = str(key).strip()

                                    if "." in key_str:
                                        key_int = int(float(key_str))
                                    else:
                                        key_int = int(key_str)

                                    if not (1 <= key_int <= 23):
                                        print(f"[KUKA][KEYPOSLOOP] PyKey ({key_int}) mimo rozsah -> přeskočeno")
                                        key_int = None
                                except (ValueError, TypeError) as e:
                                    print(f"[KUKA][KEYPOSLOOP] Neplatná hodnota PyKey ({key}): {e}")
                                    key_int = None

                                if key_int is not None:
                                    shifted = ((key_int + (key_int - 1)) * 1.15) + OFFSET

                                    seq_counter += 1
                                    seq = seq_counter

                                    if ack_fd is None:
                                        print("[KUKA][KEYPOSLOOP][PIPELINE] ACK pipe není otevřená, posílám KLÁVESU bez kontroly ACK.")
                                        wfd = self.try_open_write_nb()
                                        if wfd is not None:
                                            try:
                                                os.write(wfd, f"{seq}:{shifted}\n".encode("utf-8"))
                                                print(f"[KUKA][KEYPOSLOOP][PIPELINE] Odesílám klávesu (bez ACK): {shifted} (seq={seq})")
                                            except Exception as e:
                                                print(f"[KUKA][KEYPOSLOOP][PIPELINE] write KLÁVESY bez ACK selhalo: {e}")
                                            finally:
                                                try:
                                                    os.close(wfd)
                                                except Exception:
                                                    pass
                                        else:
                                            print("[KUKA][KEYPOSLOOP][PIPELINE] Nikdo nečte DATA pipe, klávesa se neodeslala.")
                                    else:
                                        await self.send_with_ack(
                                            seq,
                                            int(shifted),
                                            ack_fd,
                                            open_retry_delay=0.05,
                                            write_retry_delay=0.05,
                                            ack_timeout=1.0,
                                            max_retries=3,
                                        )
                                        print(f"[KUKA][KEYPOSLOOP][PIPELINE] Odesílám klávesu přes ACK-pipeline: {shifted} (seq={seq})")

                    # -------------------------------
                    # 2) PŘECHOD NA "NAHORU"
                    # -------------------------------
                    elif (not is_down) and was_down:
                        print(f"[KUKA][KEYPOSLOOP] Robot šel NAHORU (Z={z_pos:.3f}) -> posílám 0")

                        seq_counter += 1
                        seq = seq_counter
                        value = 0

                        if ack_fd is None:
                            print("[KUKA][KEYPOSLOOP][PIPELINE] ACK pipe není otevřená, posílám 0 bez kontroly ACK.")
                            wfd = self.try_open_write_nb()
                            if wfd is not None:
                                try:
                                    os.write(wfd, f"{seq}:{value}\n".encode("utf-8"))
                                    print(f"[KUKA][KEYPOSLOOP][PIPELINE] Odesláno 0 (bez ACK) seq={seq}")
                                except Exception as e:
                                    print(f"[KUKA][KEYPOSLOOP][PIPELINE] write(0) bez ACK selhalo: {e}")
                                finally:
                                    try:
                                        os.close(wfd)
                                    except Exception:
                                        pass
                            else:
                                print("[KUKA][KEYPOSLOOP][PIPELINE] Nikdo nečte DATA pipe, 0 se neodeslala.")
                        else:
                            await self.send_with_ack(
                                seq,
                                value,
                                ack_fd,
                                open_retry_delay=0.05,
                                write_retry_delay=0.05,
                                ack_timeout=1.0,
                                max_retries=3,
                            )
                            print(f"[KUKA][KEYPOSLOOP][PIPELINE] Odesláno 0 přes ACK-pipeline (seq={seq})")

                    # aktualizace edge stavu
                    was_down = is_down

                except Exception as inner_e:
                    print(f"[KUKA][KEYPOSLOOP] Chyba při čtení PyKey/Zpos: {inner_e}")

                # hlavní delay smyčky
                await asyncio.sleep(MAIN_CYCLE_SLEEP)

        except asyncio.CancelledError:
            print("[KUKA][KEYPOSLOOP] key_and_position_loop ukončena (Cancelled).")
        except Exception as e:
            print(f"[KUKA][KEYPOSLOOP] Neočekávaná chyba v key_and_position_loop: {e}")
        finally:
            try:
                if ack_fd is not None:
                    os.close(ack_fd)
            except Exception:
                pass



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