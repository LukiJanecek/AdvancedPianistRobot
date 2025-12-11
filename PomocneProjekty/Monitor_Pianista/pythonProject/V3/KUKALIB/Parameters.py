import numpy as np


### Global vars ------------------------------------------
ip_KUKA = '192.168.1.15'      # KUKA ARM KRC4, CELL n. 2

port_KUKA = 7000               # Created port in SmartPad communication settings



KUKA1_posX_default = 0.0
KUKA1_posY_default = 0.0
KUKA1_posZ_default = 0.0
KUKA1_posA_default = 0.0
KUKA1_posB_default = 0.0
KUKA1_posC_default = 0.0

KUKA1_defaultPositions = np.array([KUKA1_posX_default, KUKA1_posY_default, KUKA1_posZ_default, KUKA1_posA_default,
                                   KUKA1_posB_default, KUKA1_posC_default], dtype="float")


# Two testing array for relative movement of KUKA ARMS in 1st DEMO


# 100.0     means     100.0 mm
# 0.0       means     0.0 mm

# Due to problems with direct definition I wrote these two lines to define 'byte' pattern externally
myTrue = b'TRUE'  # Definition of TRUE in 'byte' form
myFalse = b'FALSE'  # Definition of FALSE in 'byte' form