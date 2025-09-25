import serial
import asyncio
import platform
import json
import time

from core.all_states import input_state

# Bufr pro vstup
uart_buffer = ""

# Nastavení UART portu (na Raspberry Pi obvykle /dev/serial0)
SERIAL_PORT = '/dev/serial0'
BAUDRATE = 9600

IS_LINUX = platform.system() == "Linux"
ser = None

if IS_LINUX:
    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            timeout=1        # timeout pro čtení v sekundách
        )
        print("[UART] UART inicializován (/dev/serial0)")
    except Exception as e:
        print(f"[UART] Chyba při inicializaci: {e}")
        ser = None
else:
    print("[UART] Není Linux → UART ignorován")


# Asynchronní funkce pro poslouchání UART
async def uart_listener_loop():
    if not ser:
        print("[UART ←] Není Linux → automatické přijímaní není spuštěno")
        return

    print("[UART ←] Přijímání spuštěno")
    while True:
        try:
            if ser.in_waiting:
                data = ser.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    print(f"[UART ←] Příchozí data: {data}")
        except Exception as e:
            print(f"[UART ←] Chyba při čtení: {e}")
        await asyncio.sleep(0.1)


# Asynchronní funkce pro poslouchání JSON zprávy po UARTu
last_state_time = time.time()  # čas posledního STATE

async def uart_JSON_listener_loop():
    global uart_buffer, last_state_time
    if not ser:
        print("[UART ←] Není k dispozici UART port")
        return

    print("[UART] Přijímání spuštěno")
    while True:
        try:
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
                uart_buffer += chunk

                # Zpracuj všechny kompletní bloky <JSON>...</JSON>
                while "<JSON>" in uart_buffer and "</JSON>" in uart_buffer:
                    start = uart_buffer.find("<JSON>") + len("<JSON>")
                    end = uart_buffer.find("</JSON>")
                    json_str = uart_buffer[start:end]
                    uart_buffer = uart_buffer[end + len("</JSON>"):]  # odstraněný zbytek

                    try:
                        msg = json.loads(json_str)
                        print("[UART ←]", msg)
                        input_state.update_from_json(msg)
                    except json.JSONDecodeError:
                        print("[UART JSON ERROR] Neplatný JSON:", json_str)

                # Zpracuj všechny kompletní bloky <STATE>...</STATE>
                while "<STATE>" in uart_buffer and "</STATE>" in uart_buffer:
                    start = uart_buffer.find("<STATE>") + len("<STATE>")
                    end = uart_buffer.find("</STATE>")
                    json_str = uart_buffer[start:end]
                    uart_buffer = uart_buffer[end + len("</STATE>"):]  # odstraněný zbytek

                    try:
                        msg = json.loads(json_str)
                        print("[UART ← STATE]", msg)
                        input_state.update_mode_from_json(msg)
                        last_state_time = time.time()  # aktualizace času
                    except Exception:
                        print("[UART STATE ERROR] Neplatný JSON:", json_str)

            # Kontrola timeoutu (5 sekund)
            if time.time() - last_state_time > 5:
                print("[UART STATE TIMEOUT] Žádný STATE >5s")
                input_state.reset_mode()
                last_state_time = time.time()  # reset, aby se neposílalo pořád dokola

        except Exception as e:
            print(f"[UART ← ERROR] Chyba při čtení: {e}")

        await asyncio.sleep(0.1)

#################################################
# Funkce pro odesílání zpráv přes UART
def send_uart_command(msg: str):
    if ser:
        try:
            msg = msg + '\n'
            ser.write(msg.encode('utf-8'))
            print(f"[UART →] Odesláno: {msg}")
        except Exception as e:
            print(f"[UART → ERROR] Chyba při odesílání: {e}")
    else:
        print(f"[UART →] Není Linux → odesílání ignorováno")
        

def send_json(json_obj):
    if ser:
        try:
            data = "<JSON>" + json.dumps(json_obj) + "</JSON>"
            ser.write(data.encode("utf-8"))
            print(f"[UART →] Odesláno", data.strip())
        except Exception as e:
            print(f"[UART → ERROR] Chyba při odesílání: {e}")
    else:
        print(f"[UART →] Není Linux → odesílání ignorováno")