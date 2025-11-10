import os
import time

fifo_path = "/tmp/ledpipe"

# vytvoříme pipe jen pokud ještě neexistuje
if not os.path.exists(fifo_path):
    os.mkfifo(fifo_path)

while True:
    try:
        idx = input("Zadej LED index pro spawn hada (0-29): ")
        with open(fifo_path, "w") as f:
            f.write(str(idx))
    except KeyboardInterrupt:
        break


# navod od bota:
# ✅ Jak to použít:

# Spusť na RPi C++ program:
# sudo ./piano_snakes_rpi

# V jiném terminálu spusť Python skript:
# python3 test_pipe.py

# Zadávej čísla 0–29 → hady se spawnují v odpovídajícím indexu, červené odstíny.