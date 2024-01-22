'''
OLSR ad hoc routing protocol 
RFC 3236
only for single network interface
'''

from collections.abc import Callable, Iterable, Mapping

from typing import Any
from scapy.all import *


from informationRepo import * 
from forwarder import *
from constants import *
from packetManager import *
from olsr_logger import *

if __name__ == '__main__':     
    olsr_logger = OlSRLogger()
    olsr_manager = OLSRManager()
    forwarder = packetForwarder()
    forwarder.addLogger(olsr_logger)
    forwarder.addManager(olsr_manager)
    
    
    
    # todo : 현재 packet 수신과 forwarding에 대해 어마어마한 혼동을 가지고 있으므로 구별할 것