# -*- coding: utf-8 -*-
import os, time, random

PIPE_PATH = "/tmp/ledpipe"

if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)

print("LED pipe ready. Zadejte cislo a potvrd 'y', aby se odeslalo.")

while True:
    try:
        num_input = input("Zadejte cislo: ").strip()
        if not num_input.isdigit():
            print("Chyba: zadejte cislo!")
            continue

        number = int(num_input)
        if not (1 <= number <= 22):
            print("Cislo musi byt mensi nez 23 vetsi nez 1!")
            continue

        confirm = input("Odeslat cislo? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Zruseno, zadejte znovu.")
            continue

        # Odeslat číslo do FIFO
        with open(PIPE_PATH, "w") as fifo:
            fifo.write(f"{number}\n")
        print(f"Odeslano cislo {number} do LED pipe")

    except KeyboardInterrupt:
        print("\nKonec skriptu.")
        break
