#!/bin/bash

mkdir -p /tmp/led

if [ ! -p /tmp/led/pipe ]; then
  mkfifo -m 666 /tmp/led/pipe
  echo "[ENTRYPOINT] Vytvarim FIFO /tmp/led/pipe"
else
  echo "[ENTRYPOINT] FIFO /tmp/led/pipe uz existuje"
fi

if [ ! -p /tmp/led/pipe_ack ]; then
  mkfifo -m 666 /tmp/led/pipe_ack
  echo "[ENTRYPOINT] Vytvarim FIFO /tmp/led/pipe_ack"
else
  echo "[ENTRYPOINT] FIFO /tmp/led/pipe_ack uz existuje"
fi

echo "[ENTRYPOINT] Spoustim LED aplikaci..."
exec /app/pianist_LED_top
# nebo v btm verzi exec /app/pianist_LED_btm
