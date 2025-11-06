import os
import requests
import socket
import socketserver
import json
import csv
import pandas as pd
from pathlib import Path
import threading
import time
from datetime import datetime 
from dataclasses import dataclass, field
from queue import Queue, Empty
import psycopg2
from psycopg2.extras import execute_values
import re
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

import IOT_parameters as iotparam

import KUKA_parameters as kp
import KUKA_functions as kf
import KUKA_master 

import MiR_parameters as mirparam
import MiR_functions as mirfce
import MiR_localtesting as mirtest
import MiR_master as mirmaster

import DB_functions as dbfc
import DB_parameters as dbparam

#############################################################################################

@dataclass
class Session:
    id: int
    name: str
    in_q: Queue = field(default_factory=Queue)

_sessions = {}
_sessions_lock = threading.Lock()
_next_id = 0

#############################################################################################

def log(msg):
    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{now}] {msg}")

def get_user_choice(prompt, options):
    while True:
        choice = input(f"{prompt} ({'/'.join(options)}): ").strip().lower()
        if choice in options:
            return choice
        else:
            print(f"Invalid choice. Available options: {', '.join(options)}.")    

def new_session(name: str) -> Session:
    global _next_id
    with _sessions_lock:
        _next_id += 1
        s = Session(id=_next_id, name=name)
        _sessions[s.id] = s
        return s

def end_session(session_id: int):
    with _sessions_lock:
        _sessions.pop(session_id, None)

def list_sessions():
    with _sessions_lock:
        return [(sid, s.name) for sid, s in _sessions.items()]
    
def make_ask_fn(session: Session):
    """
    Vrátí funkci ask(prompt) -> str, kterou může vlákno volat místo input().
    Vypíše dotaz a počká na odpověď v session.in_q (kterou do něj pošle menu).
    """
    tag = f"[{session.name}-{session.id}]"
    def ask(prompt: str) -> str:
        log(f"{tag} {prompt} (odpověz: :{session.id} <text>)")
        # Blokuj, dokud menu neposune odpověď
        ans = session.in_q.get()
        log(f"{tag} Odpověď přijata: {ans}")
        return ans
    return ask

def process_KUKA(session: Session):
    tag = f"[KUKA-{session.id}]"
    log("[KUKA] Process KUKA started")
    ask = make_ask_fn(session)
    try:
        KUKA_master.kuka_master(ask)
    finally:
        log(f"{tag} Hotovo")
        end_session(session.id)

def process_MiR(session: Session):
    tag = f"[MiR-{session.id}]"
    log("[MiR] Process MiR started")
    ask = make_ask_fn(session)
    try:
        mirmaster.MIR_master(ask)
    finally:
        log(f"{tag} Hotovo")
        end_session(session.id)
    
def process_Config(session: Session):
    tag = f"[Config-{session.id}]"
    log("[Config] Process Config started")
    ask = make_ask_fn(session)
    try:
        print("Tady přečteme konfigurační soubor a spustíme příslušné měření")
    finally:
        log(f"{tag} Hotovo")
        end_session(session.id)

def console_loop():
    """
    Hlavní smyčka, která se zeptá uživatele na příkaz a spustí vybrané vlákno.
    """
    log("Console loop started")
    while True:
        cmd = input("'kuka', 'mir', 'config', ':ID odpověď', 'exit', 'quit', 'q'").strip()
        
        #get_user_choice(
        #    "Enter what do u wanna measure", 
        #    ["kuka", "mir", "config", "exit", "quit", "q"]
        #)
        
        if cmd == "kuka":
            s = new_session("KUKA")
            t = threading.Thread(target=process_KUKA, args=(s,), daemon=True)
            t.start()
            print(f"Spustil jsem proces KUKA-{s.id}")
        elif cmd == "mir":
            s = new_session("MiR")
            t = threading.Thread(target=process_MiR, args=(s,), daemon=True)
            t.start()
            print(f"Spustil jsem proces MiR-{s.id}")
        elif cmd == "config":
            s = new_session("CONFIG")
            t = threading.Thread(target=process_Config, args=(s,), daemon=True)
            t.start()
            print(f"Spustil jsem proces CONFIG-{s.id}")
        elif cmd.startswith(":"):
            parts = cmd[1:].split(maxsplit=1)
            if not parts:
                print("Použij tvar :ID odpověď")
                continue
            try:
                sid = int(parts[0])
            except ValueError:
                print("ID musí být číslo, např. :2 ano")
                continue
            answer = parts[1] if len(parts) > 1 else ""
            with _sessions_lock:
                s = _sessions.get(sid)
            if not s:
                print(f"Session {sid} neexistuje")
                continue
            s.in_q.put(answer)
            continue
        elif cmd in ("exit", "quit", "q"):
            print("Ukončuji aplikaci...")
            break
        else:
            print("Neznámý příkaz, zadejte 'kuka', 'mir', 'config', ':ID odpověď', 'exit', 'quit' nebo 'q'.")

#############################################################################################

def cmd_input(ask, prompt: str, default: str | None = None) -> str:
    """
    Textový vstup přes ask(). Vrátí stripnutý řetězec, případně default, když uživatel zadá prázdno.
    """
    ans = ask(prompt).strip()
    if ans == "" and default is not None:
        return default
    return ans

def cmd_choice(ask, prompt: str, options, default: str | None = None, aliases: dict | None = None) -> str:
    """
    Volba z možností přes ask(). Case-insensitive validace, vrací kanonický tvar z `options`.
    `aliases` může mapovat zkratky na položky v options (např. {"y": "yes", "n": "no"}).
    """
    opts = [str(o) for o in options]
    canon = {o.lower(): o for o in opts}
    alias_map = {k.lower(): v for k, v in (aliases or {}).items()}

    while True:
        prompt_str = f"{prompt} ({'/'.join(opts)}" + (f", default={default}" if default else "") + "): "
        raw = ask(prompt_str).strip()
        if raw == "" and default:
            return canon.get(default.lower(), default)
        key = raw.lower()
        # alias -> kanonické jméno
        if key in alias_map:
            key = alias_map[key].lower()
        if key in canon:
            return canon[key]
        # nápověda
        print(f"Invalid choice. Available options: {', '.join(opts)}" + (f" (default {default})" if default else ""))


#############################################################################################

if __name__ == "__main__":
    try:
        console_loop()
    except Exception as e:
        print(f"Error in operation: {e}")
        log(f"Error in operation: {e}")
    finally:
        log("Program ukončen")
        print("Program ukončen")

        # disconnect from robots 

        # MiR robot disconnection
        if not mirfce.close_connection():
            print("Failed to properly close the connection.")
            log("Failed to properly close the connection.")
        else: 
            print("Connection closed successfully.")
            log("Connection closed successfully.")

        # KUKA robot disconnection