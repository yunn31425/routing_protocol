'''
OLSR ad hoc routing protocol 
RFC 3236
only for single network interface

+ move message and reclacMessage
'''

from informationRepo import * 
from constants import *
from packetManager import *
from olsr_logger import *

if __name__ == '__main__':     
    manager = OLSRManager()