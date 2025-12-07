#!/usr/bin/env python3
import os
import time
import sys

PIPE_PATH = "/tmp/led/pipe"
ACK_PIPE_PATH = "/tmp/led/pipe_ack"


def wait_for_pipes():
    """Počká, než existují FIFO soubory vytvořené backendem / dockerem."""
    print(f"[DAEMON] Čekám na FIFO {PIPE_PATH} a {ACK_PIPE_PATH}...")
    while not (os.path.exists(PIPE_PATH) and os.path.exists(ACK_PIPE_PATH)):
        print("[DAEMON] FIFO zatím nejsou, spím 0.5 s...")
        time.sleep(0.5)
    print("[DAEMON] FIFO existují, pokračuju.")


def open_pipes():
    """
    Otevře:
      - data_pipe pro ČTENÍ z /tmp/led/pipe
      - ack_pipe pro ZÁPIS do /tmp/led/pipe_ack
    Pozor: open() na pojmenovaném pipe může blokovat, dokud není druhá strana.
    """
    # otevřít data pipe (backend už do ní bude psát)
    print(f"[DAEMON] Otevírám DATA FIFO {PIPE_PATH} pro čtení...")
    data_fd = os.open(PIPE_PATH, os.O_RDONLY)
    data_pipe = os.fdopen(data_fd, "r", buffering=1)
    print("[DAEMON] DATA FIFO otevřeno.")

    # otevřít ACK pipe pro zápis (backend má otevřeno pro čtení)
    print(f"[DAEMON] Otevírám ACK FIFO {ACK_PIPE_PATH} pro zápis...")
    ack_fd = os.open(ACK_PIPE_PATH, os.O_WRONLY)
    ack_pipe = os.fdopen(ack_fd, "w", buffering=1)
    print("[DAEMON] ACK FIFO otevřeno.")

    return data_pipe, ack_pipe


def main():
    print("[DAEMON] Startuji Python kontrolní daemon pro /tmp/led/pipe")

    # 1) Počkat, než backend/docker vytvoří FIFO
    wait_for_pipes()

    while True:
        try:
            data_pipe, ack_pipe = open_pipes()

            # 2) Hlavní smyčka – čteme řádky z pipeline
            while True:
                line = data_pipe.readline()
                if not line:
                    # EOF = writer zavřel pipe (backend restart?)
                    print("[DAEMON] EOF na DATA FIFO, zkusím znovu otevřít za 0.5 s...")
                    time.sleep(0.5)
                    break  # vyskočíme do outer while a znovu otevřeme

                line = line.strip()
                if not line:
                    continue

                print(f"[DAEMON] Přijatá zpráva: '{line}'")

                # Očekáváme formát "seq:value"
                try:
                    seq_str, val_str = line.split(":", 1)
                    seq = int(seq_str)
                    value = int(val_str)
                except Exception as e:
                    print(f"[DAEMON] !!! Neplatný formát zprávy '{line}': {e}")
                    # Neposíláme ACK, backend to podle seq/timeoutu případně retryne
                    continue

                # Tady můžeš dělat, co chceš – např. simulovat úhoz klávesy
                print(f"[DAEMON] >>> seq={seq}, value={value}")

                # Odeslat ACK zpět backendu
                try:
                    ack_line = f"ACK:{seq}\n"
                    ack_pipe.write(ack_line)
                    ack_pipe.flush()
                    print(f"[DAEMON] Odeslán ACK: {ack_line.strip()}")
                except BrokenPipeError:
                    print("[DAEMON] !!! BrokenPipe na ACK FIFO, zkusím znovu otevřít...")
                    time.sleep(0.5)
                    break  # zkusíme to celé otevřít znovu
                except Exception as e:
                    print(f"[DAEMON] !!! Chyba při zápisu ACK: {e}")
                    time.sleep(0.5)
                    break

        except KeyboardInterrupt:
            print("[DAEMON] CTRL+C – ukončuji.")
            sys.exit(0)
        except Exception as e:
            print(f"[DAEMON] Neočekávaná chyba: {e}")
            time.sleep(1.0)  # malá pauza, a zkusí to znovu


if __name__ == "__main__":
    main()
