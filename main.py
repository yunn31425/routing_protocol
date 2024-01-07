'''
OLSR ad hoc routing protocol 
RFC 3236
only for single network interface
'''




from collections.abc import Callable, Iterable, Mapping
import sys
import socket
import logging 
import struct
from socket import *
import threading
import time
import subprocess
from typing import Any
# from numba import jit

from informationRepo import * 
from forwarder import *
from constants import *


class helloMessage:
    pass

class message:
    pass

class helloMessage(message):
    pass

class tcMessage(message):
    pass


if __name__ == '__main__':
    
    # if len(sys.argv) == 1:
    #     print("enter network interface name")
    #     exit()

    try:
        listenSocket = socket(AF_INET, SOCK_STREAM)
        listenSocket.bind(('', PORTNUM))
        listenSocket.listen()

    except OSError as e:
        if e.errno == 98:
            print("port is already in use")
            listenSocket.close()
        else:
            print(e)
        exit()
        
    # check if network mode is ad-hoc not managed
    # if (subprocess.run('iwconfig | grep Mode', shell=True, capture_output=True, text=True).stdout).split(' ')[10] == "Mode:Managed":
    #     print("change mode into ad-hoc first")
    #     exit()
    
    
    interfaceAss = InterfaceAssociation()
    LinkSetTuple = LinkSet()
    twoneighborTuple = TwoHopNeighborSet()
    mprTuple = MPRSet()
    mprSelector = MPRSelectorSet()
    topolodyTuple = TopologyInfo()
    
    class PacketHeader:
        pass
    
    class helloMessage(threading.Thread):
        '''
        message type : hello message
        TTL : 1
        VTime set by NEIGHB_HOLD_TIME
        generated based on link set, neighbor set, MPR set 
        '''
        def __init__(self) -> None:
            super().__init__()
            self.last_emission_time = 0
            
        def run(self):
            pass
        
        def cal_Htime_tobit(self):
            pass
        
        def cal_Htime_todigit(self):
            pass
        
        def packMessage(self, ):
            packet_format = ''
            packed_data = struct.pack(packet_format,
                                      RESERVED,             # 0
                                      NEIGHB_HOLD_TIME,     # Htime
                                      WILL_DEFAULT,         # willingness default
                                      )
        
        def unpackMessage(self):
            pass
        
        
    
        
    
    
