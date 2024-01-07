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

#message listening port
PORTNUM = 14567

#define emission interval
HELLO_INTERVAL = 2
REFRESH_INTERVAL = 2
TC_INTERVAL = 2
MID_INTERVAL = TC_INTERVAL
HNA_INTERVAL = TC_INTERVAL

#define holding time 
NEIGHB_HOLD_TIME = REFRESH_INTERVAL*3
TOP_HOLD_TIME = 3*TC_INTERVAL
DUP_HOLD_TIME = 30
MID_HOLD_TIME = MID_INTERVAL*3
HNA_HOLD_TIME = HNA_INTERVAL*3

class InterfaceAssociation(threading.Thread):
    def __init__(self):
        super().__init__()
        self.interfaceTuple = []
        self.start()

    def run(self): # 일정 시간이 지나면 tuple 삭제
        while True:
            for i, tuple in enumerate(self.interfaceTuple):
                if self.checkTimeExpired(tuple[2]):
                    self.interfaceTuple.pop(i)
                    print(f'tuple deleted {i}')
        
    def addTuple(self, iface_addr, main_addr, addtime = time.time()):
        self.interfaceTuple.append((iface_addr, main_addr, addtime))
    
    def delTuple(self, index):
        self.interfaceTuple.pop(index)
    
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False
            
        
class informationRepo:
    def __init__(self) -> None:
        self.link_tuple = []
    
    def add_link_tuple():
        pass

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
        exit()
        
    # if (subprocess.run('iwconfig | grep Mode', shell=True, capture_output=True, text=True).stdout).split(' ')[10] == "Mode:Managed":
    #     print("change mode into ad-hoc first")
    #     exit()
    
    
    interfaceAss = InterfaceAssociation()

        
    
    
