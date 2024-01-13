from collections.abc import Callable, Iterable, Mapping
import time
import threading
from typing import Any

from constants import *

class InterfaceAssociation(threading.Thread):
    def __init__(self):
        super().__init__()
        self.interfaceTuple = []
        self.start()

    def run(self): # 일정 시간이 지나면 tuple 삭제
        while True:
            for i, tuple in enumerate(self.interfaceTuple):
                if self.checkTimeExpired(tuple[-1]):
                    self.interfaceTuple.pop(i)
                    print(f'tuple deleted {i}')
        
    def addTuple(self, i_iface_addr, i_main_addr, i_addtime = time.time()):
        self.interfaceTuple.append((i_iface_addr, i_main_addr, i_addtime))
    
    def delTuple(self, index):
        self.interfaceTuple.pop(index)
    
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False
            
class LinkSet(threading.Thread):
    
    class linkTuple:
        def __init__(self, l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time) -> None:
            self._l_local_iface_addr = l_local_iface_addr
            self._l_neighbor_iface_addr = l_neighbor_iface_addr
            self._l_SYM_time = l_SYM_time
            self._l_ASYM_time = l_ASYM_time
            self._l_time = l_time
        
        def checkExpired(self):
            if self._l_time > time.time():
                return False
            
            return True
        
        def getLinkType(self):
            cur_time = time.time()
            if self._l_SYM_time >= cur_time:
                return SYM_LINK
            if self._l_ASYM_time >= cur_time:
                return ASYM_LINK
            return LOST_LINK
            
    def __init__(self):
        super().__init__()
        self.tupleList = [] #linkSetTuple
        # self.start()

    def run(self): # 일정 시간이 지나면 tuple 삭제
        while True:
            for i, tuple in enumerate(self.tuple):
                if self.tupleList.checkExpired():
                    self.tupleList.pop(i)
                    print(f'tuple deleted {i}')
        
    def addTuple(self, l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time = time.time()):
        self.tupleList.append(self.linkTuple(l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time))
    
    def delTuple(self, index):
        self.tupleList.pop(index)
        
    def getTuple(self):
        return self.tupleList
    
class NeighborSet:
    def __init__(self):
        super().__init__()
        self.neighborTuple = []

    def addTuple(self, n_neighbor_main_addr, n_status, n_willingness):
        self.neighborTuple.append((n_neighbor_main_addr, n_status, n_willingness))
        
    def checkExist(self, addr):
        for i in self.neighborTuple:
            if i[0] == addr:
                if i[1] == SYM:
                    return SYM_NEIGH
                elif i[1] == NOT_SYM:
                    return NOT_NEIGH
                return UNSPEC_LINK
            
        return UNSPEC_LINK
    
    def delTuple(self, index):
        self.neighborTuple.pop(index)

class TwoHopNeighborSet(threading.Thread):
    def __init__(self):
        super().__init__()
        self.TwoneighborTuple  = []
        self.start()

    def run(self): # 일정 시간이 지나면 tuple 삭제
        while True:
            for i, tuple in enumerate(self.TwoneighborTuple):
                if self.checkTimeExpired(tuple[-1]):
                    self.TwoneighborTuple .pop(i)
                    print(f'tuple deleted {i}')
        
    def addTuple(self, n_neighbor_main_addr,n_2hop_addr, n_time = time.time()):
        self.TwoneighborTuple.append((n_neighbor_main_addr,n_2hop_addr, n_time))
    
    def delTuple(self, index):
        self.TwoneighborTuple.pop(index)
    
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False

class MPRSet(threading.Thread):
    def __init__(self):
        super().__init__()
        self.MPRTuple = []
        # self.start()

    def addTuple(self, neighbor):
        self.MPRTuple.append(neighbor)
    
    def checkExist(self, addr):
        return addr in self.MPRTuple
    
    def delTuple(self, index):
        self.MPRTuple.pop(index)    
        
class MPRSelectorSet(threading.Thread):
    def __init__(self):
        super().__init__()
        self.mprSelectorTuple  = []
        # self.start()

    def run(self): # 일정 시간이 지나면 tuple 삭제
        while True:
            for i, tuple in enumerate(self.mprSelectorTuple):
                if self.checkTimeExpired(tuple[-1]):
                    self.mprSelectorTuple.pop(i)
                    print(f'tuple deleted {i}')
        
    def addTuple(self, ms_main_addr, ms_time = time.time()):
        self.mprSelectorTuple.append((ms_main_addr, ms_time))
    
    def delTuple(self, index):
        self.mprSelectorTuple.pop(index)
    
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False  
      
class TopologyInfo(threading.Thread):
    def __init__(self):
        super().__init__()
        self.topoloyTuple = []
        # self.start()

    def run(self): # 일정 시간이 지나면 tuple 삭제
        while True:
            for i, tuple in enumerate(self.topoloyTuple):
                if self.checkTimeExpired(tuple[-1]):
                    self.topoloyTuple.pop(i)
                    print(f'tuple deleted {i}')
        
    def addTuple(self, t_dest_addr, t_last_addr, t_seq, t_time = time.time()):
        self.topoloyTuple.append((t_dest_addr, t_last_addr, t_seq, t_time))
    
    def delTuple(self, index):
        self.topoloyTuple.pop(index)
    
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False
    
class DuplicatdSet():
    '''
    maintain transmitted message 
    to prevent transmitting the same 
    OLSR message twice
    (store packet data which has been processed)
    '''
    
    class duplicatedTuple:
        def __init__(self, d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time):
            self._d_addr = d_addr,                  # originator address of the message
            self._d_seq_num = d_seq_num             # message sequence number of the message
            self._d_retransmitted = d_retransmitted # boolean, whether the message has been retransmitted,
            self._d_iface_list = d_iface_list       
            # list of the addresses of the interfaces on which the message has been received
            self._d_time = d_time                   # tuple expires and *MUST* be removed.
        
    def __init__(self):
        super().__init__()
        self.dTupleList = []
        
    def checkExist(self, d_addr, d_seq_num):
        pass
    
    def addTuple(self, d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time):
        self.dTupleList.append(self.duplicatedTuple(d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time))
        
    
class TimeOutManager(threading.Thread):
    '''
    tour every repository and pop element that over times
    '''
    def __init__(self):
        super().__init__()
        
    def run(self):
        pass