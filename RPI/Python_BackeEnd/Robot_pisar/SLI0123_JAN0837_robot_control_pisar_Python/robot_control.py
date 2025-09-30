from __future__ import print_function
import sys
import struct
import random
import socket
from time import sleep

#pip install pandas openpyxl
import pandas as pd

url = "https://raw.githubusercontent.com/LukiJanecek/robot_control/master/Body_Abeceda.csv?token=GHSAT0AAAAAACQGF4UTHP2BTKSMOFJRGO3AZQWZHSA"

import Funkce_pohybu

__version__ = '1.1.8'
ENCODING = 'UTF-8'

PY2 = sys.version_info[0] == 2
#if PY2: input = raw_input1

################################################################################################
#Global variables 
legth = 100
height = 50
width = 20

startPointX = 5
startPointY = 5
startPointZ = 5
NumberOfPoints = 0

offset = 0

homeX = -11,68
homeY = -419,42
homeZ = 182,34
homeA = 91,4
homeB = 28,64
homeC = -179,4

# Slovnik akci pro jednotliva pismena
actions = {
    'a': Funkce_pohybu.draw_A,
    'b': Funkce_pohybu.draw_B,
    'c': Funkce_pohybu.draw_C,
    'd': Funkce_pohybu.draw_D,
    'e': Funkce_pohybu.draw_E,
    'f': Funkce_pohybu.draw_F,
    'g': Funkce_pohybu.draw_G,
    'h': Funkce_pohybu.draw_H,
    'i': Funkce_pohybu.draw_I,
    'j': Funkce_pohybu.draw_J,
    'k': Funkce_pohybu.draw_K,
    'l': Funkce_pohybu.draw_L,
    'm': Funkce_pohybu.draw_M,
    'n': Funkce_pohybu.draw_N,
    'o': Funkce_pohybu.draw_O,
    'p': Funkce_pohybu.draw_P,
    'q': Funkce_pohybu.draw_Q,
    'r': Funkce_pohybu.draw_R,
    's': Funkce_pohybu.draw_S,
    't': Funkce_pohybu.draw_T,
    'u': Funkce_pohybu.draw_U,
    'v': Funkce_pohybu.draw_V,
    'w': Funkce_pohybu.draw_W,
    'x': Funkce_pohybu.draw_X,
    'y': Funkce_pohybu.draw_Y,
    'z': Funkce_pohybu.draw_Z,
    # Přidáš další písmena a jejich funkce zde
}

################################################################################################

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
                self.read(var)
            else:
                print('read error, socket closed')
                self.retry = 0
                self.close()
                return

    def write(self, var, value, debug=False):
        if not (isinstance(var, str) and isinstance(value, str)):
            raise Exception('Var name and its value should be string')
        self.varname = var if PY2 else var.encode(ENCODING)
        self.value = value if PY2 else value.encode(ENCODING)
        return self._write_var(debug)

    def _read_var(self, debug):
        req = self._pack_read_req()
        self._send_req(req)
        _value = self._read_rsp(debug)
        if debug:
            print(_value)
        return _value

    def _write_var(self, debug):
        req = self._pack_write_req()
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

    def _pack_write_req(self):
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
        self.connected = False
        self.ipAddress = ipAddress
        self.port = port
        self.client = None

    def KUKA_Open(self):
        if self.connected == False:
            self.client = openshowvar(self.ipAddress, self.port)
            res = self.client.can_connect

            if res == True:
                print('Connection is established!')
                self.connected = True
                return True
            else:
                print('Connection is broken! Check configuration or restart C3_Server at KUKA side.')
                self.connected = False
                return False
        else:
            print('Connection is ready!')

    def KUKA_ReadVar(self, var):
        if self.connected:
            res = self.client.read(var, debug=False)
            if res == b'TRUE':
                return True
            elif res == b'FALSE':
                return False
            else:
                return res
        else:
            return False

    def KUKA_WriteVar(self, var, value):
        if self.connected:
            self.client.write(var, str(value))
            return True
        else:
            return False

    def KUKA_Close(self):
        if self.connected == True:
            self.client.close()
            self.connected = False
            return True

        else:
            return False

###################################### RUN Program ##########################################################
#Program
robot = KUKA_Handler('192.168.1.152', 7000)
robot.KUKA_Open()

#number_of_iterations = 1  # pocet iteraci vsech os.
#for i in range(1, 7):
#    robot.KUKA_WriteVar(f'PyITER[{i}]', number_of_iterations)  # zapsani poctu iteraci do PyITER[1] až PyITER[6]
#sleep(1)
#robot_speed = 30
#robot.KUKA_WriteVar('PySPEED', robot_speed)  # rychlost jednotlivych pohybu robotu v procentech.
#sleep(1)

while True:

    x = 0
    y = 0
    z = 0
    a = 0
    b = 0
    c = 0

    print("Proměnné: ")
    print(x)
    print(y)
    print(z)
    print(a)
    print(b)
    print(c)
    print(" ")

    robot.KUKA_WriteVar('PyX', x)
    robot.KUKA_WriteVar('PyY', y)
    robot.KUKA_WriteVar('PyZ', z)
    robot.KUKA_WriteVar('PyA', a)
    robot.KUKA_WriteVar('PyB', b)
    robot.KUKA_WriteVar('PyC', c)

    sleep(0.5)

    #Zajetí do HomeBodu
    robot.KUKA_WriteVar('PyDomu', True)

    #Čekání něž tam dojede
    while not robot.KUKA_ReadVar('PyDomuFb'):
        sleep(0.5)

    robot.KUKA_WriteVar('PyDomu', False)
    robot.KUKA_WriteVar('PyDomuFb', False)

    #PŘI NEZNÁNÍ Písmena
    def unknown_action(robot, offset):
        print("Neznámé písmeno - není funkce")

    user_input = input("Zadej slovo o velikosti 1 až 5 písmen: ").lower()

    """
    # Smyčka bude pokračovat, dokud uživatel nezadá přesně čtyři písmena
    while len(user_input) != 4:
        print("Nezadali jste přesně čtyři písmena.")

        user_input = input("Zadej čtyři písmena: ").lower()
    """

    # Smyčka bude pokračovat, dokud uživatel nezadá minimálně 1 a maximálně 5 písmen
    while not (1 <= len(user_input) <= 5):
        print("Nezadali jste správný počet písmen.")

        user_input = input("Zadej slovo o velikosti 1 až 5 písmen: ").lower()
        

    # Pokud je vstup platný, provede se následující kód
    i = 0
    offsetDef = 70
    letters = list(user_input)  # Rozdělení vstupu na písmena
    for letter in letters:  # Smyčka prochází každé písmeno
        print(" ")
        print("Je vybrano pismeno:")
        print(letter)

        i += 1

        if i == 1:
            offset = 0
        elif i > 1:
            offset = offsetDef * (i-1)
            
        
        # Volání příslušné funkce pro každé písmeno nebo funkce pro neznámé písmeno
        try:
            actions.get(letter, unknown_action)(robot, offset)
        except Exception as e:
            print(f"Chyba při zpracování písmene {letter}: {str(e)}")

    print('PISMENA JSOU NAPSANY!')

robot.KUKA_Close()

#number_of_iterations = 1  # pocet iteraci vsech os.
    #for i in range(1, 7):
    #    robot.KUKA_WriteVar(f'PyITER[{i}]', number_of_iterations)  # zapsani poctu iteraci do PyITER[1] až PyITER[6]
    #sleep(1)
    #robot_speed = 30
    #robot.KUKA_WriteVar('PySPEED', robot_speed)  # rychlost jednotlivych pohybu robotu v procentech.
    #sleep(1)

#PyX -> zapsat
#PyY -> zapsat
#PyZ -> zapsat
#PyA -> zapsat
#PyB -> zapsat
#PyC -> zapsat

#PyDomu
#PyDomuFb -> cist 
#PyPsani()
#PyDopsano -> cist 
#PyBodDopsan -> cist 
#PyDalsiBod -> zapsat

#PyRun -> nepouzivame
#PyDone -> nepouzivame 
