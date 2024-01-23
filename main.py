'''
OLSR ad hoc routing protocol 
RFC 3236
only for single network interface
'''

from collections.abc import Callable, Iterable, Mapping

from typing import Any
from scapy.all import *


from informationRepo import * 
from constants import *
from packetManager import *
from olsr_logger import *

if __name__ == '__main__':     
    forwarder = packetForwarder()