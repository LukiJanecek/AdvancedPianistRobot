import numpy as np
from kukavarproxy import openshowvar

# Definition of a variables

# ---------------------------------------------------

# Definition of a class KUKA_Handler
class KUKA_Handler:
    def __init__(self, ipAddress, port, defaultPos = np.zeros(shape=6, dtype=("float"))):
        self.connected = False
        if is_valid_ipv4(ipAddress):
            self.ipAddress = ipAddress
        self.port = port
        self.client = None

        self.__pos_default = defaultPos.copy()
        self.__pos_actual = defaultPos.copy()

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

    def KUKA_Continue(self):
        if self.connected == True:
            self.client.write('C3BI_CONT', str(True))
            return True
        else:
            return False

    def KUKA_SendXYZABC(self, offsets = np.zeros(shape=6, dtype=("float")), cont = True, relative = True):
        if self.connected == True:
            string_print = ""
            if relative:
                self.__pos_actual += offsets
            else:
                self.__pos_actual = offsets
                # for i in self.__pos_actual:
                #     string_print += "{:.2f}, ".format(i)
                # print(string_print + " :: actual home position")

            try:
                self.client.write('C3BI_POSXYZ', '{FRAME: X ' + str(self.__pos_actual[0]) +
                                  ', Y ' + str(self.__pos_actual[1]) +
                                  ', Z ' + str(self.__pos_actual[2]) +
                                  ', A ' + str(self.__pos_actual[3]) +
                                  ', B ' + str(self.__pos_actual[4]) +
                                  ', C ' + str(self.__pos_actual[5]) + '}')
            except:
                #print('Exception during communication')
                return False

            if cont:
                self.KUKA_Continue()
            return True
        else:
            return False

    def KUKA_GetState(self, printRes = True):
        if self.connected == True:
            res = self.KUKA_ReadVar('C3BI_BPT', printRes)
            return(res)

        else:
            return False

    def KUKA_ReadVar(self, var, printRes = True):
        if self.connected == True:
            res = self.client.read(var, debug=False)
            if printRes:
                print(res)
            return (res)

        else:
            return False

    def KUKA_Close(self):
        if self.connected == True:
            self.client.close()
            self.connected = False
            return True

        else:
            return False

    def KUKA_GetActualPos(self):
        return (self.__pos_actual)

    def KUKA_homing(self, cont=True):
        try:
            self.client.write('C3BI_POSXYZ', '{FRAME: X ' + str(self.__pos_default[0]) +
                              ', Y ' + str(self.__pos_default[1]) +
                              ', Z ' + str(self.__pos_default[2]) +
                              ', A ' + str(self.__pos_default[3]) +
                              ', B ' + str(self.__pos_default[4]) +
                              ', C ' + str(self.__pos_default[5]) + '}')
            self.__pos_actual = self.__pos_default.copy()
        except:
            #print('Exception during communication')
            return False

        if cont:
            self.KUKA_Continue()

        return True
        # Co jsem si napsal ja pro klaviristu
    def Play_REGGAE(self,var):
        if self.connected == True:
            self.client.write('PyREGGAE', str(var))
            return True
        else:
            return False

    def Play_STUPNICE(self,var):
        if self.connected == True:
            self.client.write('PySTUPNICE', str(var))
            return True
        else:
            return False

    def Play_BEETHOVEN(self,var):
        if self.connected == True:
            self.client.write('PyBEETHOVEN', str(var))
            return True
        else:
            return False
# --------------------------------------------------- Helpers

def is_valid_ipv4(ip):
    parts = ip.split(".")
    if len(parts) < 4 or len(parts) > 4:
        return "invalid IP length should be 4 not greater or less than 4"
    else:
        while len(parts) == 4:
            a = int(parts[0])
            b = int(parts[1])
            c = int(parts[2])
            d = int(parts[3])
            if a <= 0 or a == 127:
                return "invalid IP address"
            elif d == 0:
                return "host id  should not be 0 or less than zero "
            elif a >= 255:
                return "should not be 255 or greater than 255 or less than 0 A"
            elif b >= 255 or b < 0:
                return "should not be 255 or greater than 255 or less than 0 B"
            elif c >= 255 or c < 0:
                return "should not be 255 or greater than 255 or less than 0 C"
            elif d >= 255 or c < 0:
                return "should not be 255 or greater than 255 or less than 0 D"
            else:
                return "Valid IP address ", ip




