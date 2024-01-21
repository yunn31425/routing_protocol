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
    
    def checkExist(self):
        pass # todo
    
    def updateTuple(self):
        pass # todo
    
    def lTimeMax(self, tuple_exist):
        pass # todo
    
    def checkLinkType(self, tuple_ptr):
        return self.tupleList[tuple_ptr].getLinkType()
    
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
    
    def checkwill(self, addr):
        for i in self.neighborTuple:
            if i[0] == addr:
                return i[2]
            
        return
    
    def delTuple(self, index):
        self.neighborTuple.pop(index)
        
    def filterWillingness(self, willingness):
        return [node for node in self.neighborTuple if node.n_willingness == willingness]
    
    def getTuple(self):
        return self.neighborTuple   

class TwoHopNeighborSet(threading.Thread):
    '''
    n_neighbor_main_addr    : main address of a neighbor
    n_2hop_addr             : main address of a 2-hop neighbor with 
                            a symmetric link to N_neighbor_main_add
    n_time                  :
    '''
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
        
    def addTuple(self, n_neighbor_main_addr, n_2hop_addr, n_time = time.time()):
        # will replace same tuple - same n_neighbor_main_addr,n_2hop_addr
        self.TwoneighborTuple.append((n_neighbor_main_addr,n_2hop_addr, n_time))
    
    def delTuple(self, index):
        self.TwoneighborTuple.pop(index)
        
    def getTuple(self):
        return self.TwoneighborTuple
    
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False
    
    def checkSingleLink(self):
        '''
        return address of main addr which is only 
        link to a 2_hop_neighbor 
        '''
        onlyNode = []
        dupNode = []
        coverNode = []
        
        for node in self.TwoneighborTuple:
            if node.n_neighbor_main_addr in dupNode:
                continue
            if node.n_neighbor_main_addr in onlyNode:
                onlyNode.remove(node.n_neighbor_main_addr)
                dupNode.append(node.n_neighbor_main_addr)
            onlyNode.append(node.n_neighbor_main_addr)
        for node in self.TwoneighborTuple:
            coverNode.append(node.n_2hop_addr)
        return onlyNode, coverNode

    def getTwoHopNeigh(self):
        return [node[1] for node in self.TwoneighborTuple]
    
    def delTuple(self, n_neighbor_main_addr, n_2hop_addr):
        pass

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

    def getTupleLastAddr(self, t_last_addr):
        # 주소에 해당하는 ansn 반환
        return ansn
    
    def updateTuple(self, idx, t_dest_addr, t_last_addr, t_seq, t_time):
        pass
    
    def findTuple(self, t_dest_addr, t_last_addr, t_seq, t_time):\
        pass # none 제외 해당 조건 있으면 tuple 찾기
    
    
class DuplicatdSet():
    '''
    maintain transmitted message 
    to prevent transmitting the same 
    OLSR message twice
    (store packet data which has been processed)
    '''
    def singleTuple(self, d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time):                    
        return [d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time]
        
    def __init__(self):
        super().__init__()
        self.dTupleList = []
        
    def checkExist_addr_seq(self, d_addr, d_seq_num,  check_retransmit=False):
        ptr_lower = 0
        ptr_upper = len(self.dTupleList)-1
        ptr_mid = 0
        
        while ptr_lower < ptr_upper:
            ptr_mid = round((ptr_upper + ptr_lower)/2) 
            print(ptr_lower, ptr_mid, ptr_upper)
            if d_seq_num == self.dTupleList[ptr_mid][1]:
                break
            elif d_seq_num < self.dTupleList[ptr_mid][1]:
                ptr_upper = ptr_mid -1
            elif d_seq_num > self.dTupleList[ptr_mid][1]:
                ptr_lower = ptr_mid + 1
        
        if self.dTupleList[ptr_mid][1] == d_seq_num and \
            self.dTupleList[ptr_mid][0] == d_addr:
            if check_retransmit:
                if self.dTupleList[ptr_mid][2] == False:
                    pass
            else:
                return ptr_mid
        return False
    
    def checkExist_iface(self, ip_address, check_retransmit=False):
        ptr_lower = 0
        ptr_upper = len(self.dTupleList)-1
        ptr_mid = 0
        
        while ptr_lower < ptr_upper:
            ptr_mid = round((ptr_upper + ptr_lower)/2) 
            print(ptr_lower, ptr_mid, ptr_upper)
            if ip_address == self.dTupleList[ptr_mid][3]:
                break
            elif ip_address < self.dTupleList[ptr_mid][3]:
                ptr_upper = ptr_mid -1
            elif ip_address > self.dTupleList[ptr_mid][3]:
                ptr_lower = ptr_mid + 1
        
        if self.dTupleList[ptr_mid][3] == ip_address:
            if check_retransmit:
                if self.dTupleList[ptr_mid][2] == False:
                    return ptr_mid
            else:
                return ptr_mid
        return False
                
    def addTuple(self, d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time):
        self.dTupleList.append(self.singleTuple(d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time))
        self.dTupleList.sort(key=lambda x: x[1])
        
    def updateTuple(self, ptr, new_time, dest_addr, retransmit):
        original = self.dTupleList[ptr] 
        original[4] = new_time
        original[3].append(dest_addr)
        original[2] = retransmit
        self.dTupleList[ptr] = original 
        self.dTupleList.sort(key=lambda x: x[1])
    
class TimeOutManager(threading.Thread):
    '''
    tour every repository and pop element that over times
    '''
    def __init__(self):
        super().__init__()
        
    def run(self):
        pass
     
# processing : using the content of the messages
# forwarding : retransmitting the same message


class LocationSet():
    def __init__(self) -> None:
        pass
    def addTuple(self):
        pass
    def updateTuple(self):
        pass
    
    
class RouteTable:
    def __init__(self) -> None:
        self.route_table = []
    
    def addTuple(self, R_dest_addr, R_next_addr, R_dist, R_iface_addr):
        '''
        R_dest_addr : destination addr
        R_next_addr : next to be reach to dest
        R_dist : hops to be reached to dest
        R_iface_addr : interface that link exist to destination
        '''
        self.route_table.append(R_dest_addr, R_next_addr, R_dist, R_iface_addr)
        
    def resetTuple(self):
        self.route_table = []