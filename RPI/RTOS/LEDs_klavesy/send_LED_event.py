# -*- coding: utf-8 -*-
import os, time, random

PIPE_PATH = "/tmp/ledpipe"

if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)

while True:
    with open(PIPE_PATH, "w") as pipe:
        val = random.randint(1, 22)
        print(f"Sending {val}")
        pipe.write(f"{val}\n")
    time.sleep(1)
