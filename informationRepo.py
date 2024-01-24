from collections.abc import Callable, Iterable, Mapping
import time
import threading
from typing import Any
import asyncio
import time
from constants import *

class InterfaceAssociation:
    def __init__(self):
        super().__init__()
        self.interfaceTuple = []

    async def run(self): # 일정 시간이 지나면 tuple 삭제
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
            
class LinkSet:    
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
        
        def getNeighAddr(self):
            return self._l_neighbor_iface_addr
            
    def __init__(self):
        super().__init__()
        self.tupleList = [] #linkSetTuple
        
    async def run(self): # 일정 시간이 지나면 tuple 삭제
        for i, single_tuple in enumerate(self.tupleList):
            if self.tupleList.checkExpired(single_tuple):
                self.tupleList.pop(i)
                print(f'tuple deleted {i}')
        
    def addTuple(self, l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time = time.time()):
        self.tupleList.append(self.linkTuple(l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time))
    
    def delTuple(self, index):
        self.tupleList.pop(index)
        
    def getTuple(self):
        return self.tupleList
    
    def checkExist(self, source_addr):
        for i, single_tuple in enumerate(self.tupleList):
            if single_tuple.getNeighAddr() == source_addr:
                return i
            
        return False
    
    def updateTuple(self, idx, l_local_iface_addr=None, l_neighbor_iface_addr=None, \
        l_SYM_time=None, l_ASYM_time=None, l_time=None):
        original = self.tupleList[idx]
        self.tupleList[idx] = [
            l_local_iface_addr if l_local_iface_addr is not None else original[0],
            l_neighbor_iface_addr if l_neighbor_iface_addr is not None else original[1],
            l_SYM_time if l_SYM_time is not None else original[2],
            l_ASYM_time if l_ASYM_time is not None else original[3],
            l_time if l_time is not None else original[4]     
        ]
    
    def lTimeMax(self, idx):
        self.tupleList[idx][4] = max(self.tupleList[idx][4], self.tupleList[idx][3])
    
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
    
    def getNeigh(self):
        return [single_tuple[0] for single_tuple in self.neighborTuple]

class TwoHopNeighborSet:
    '''
    n_neighbor_main_addr    : main address of a neighbor
    n_2hop_addr             : main address of a 2-hop neighbor with 
                            a symmetric link to N_neighbor_main_add
    n_time                  :
    '''
    def __init__(self):
        super().__init__()
        self.TwoneighborTuple  = []
        

    async def run(self): # 일정 시간이 지나면 tuple 삭제
        for i, tuple in enumerate(self.TwoneighborTuple):
            if self.checkTimeExpired(tuple[-1]):
                self.TwoneighborTuple.pop(i)
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

class MPRSet:
    def __init__(self):
        super().__init__()
        self.MPRTuple = []

    def addTuple(self, neighbor):
        self.MPRTuple.append(neighbor)
    
    def checkExist(self, addr):
        return addr in self.MPRTuple
    
    def delTuple(self, index):
        self.MPRTuple.pop(index)    
    
    def updateMpr(self, new_mpr):
        self.MPRTuple = new_mpr
        
class MPRSelectorSet:
    def __init__(self):
        super().__init__()
        self.mprSelectorTuple  = []

    async def run(self): # 일정 시간이 지나면 tuple 삭제
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
      
class TopologyInfo:
    '''
    t_dest_addr
    t_last_addr
    t_seq
    t_time
    '''
    def __init__(self):
        super().__init__()
        self.topoloyTuple = []
    

    async def run(self): # 일정 시간이 지나면 tuple 삭제
        for i, tuple in enumerate(self.topoloyTuple):
            if self.checkTimeExpired(tuple['t_time']):
                self.topoloyTuple.pop(i)
                print(f'tuple deleted {i}')
        
    def addTuple(self, t_dest_addr, t_last_addr, t_seq, t_time = time.time()):
        self.topoloyTuple.append({
            't_dest_addr' : t_dest_addr,
            't_last_addr' : t_last_addr, 
            't_seq' : t_seq, 
            't_time' : t_time
            })
    
    def delTuple(self, index):
        self.topoloyTuple.pop(index)
    
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False

    def getTupleLastAddr(self, t_last_addr):
        # 주소에 해당하는 ansn 반환
        return self.topoloyTuple[self.findTuple(t_last_addr)]['t_seq']
    
    def updateTuple(self, idx, t_dest_addr, t_last_addr, t_seq, t_time):
        original = self.topoloyTuple[idx]
        self.topoloyTuple[idx] = {
            't_dest_addr' : (t_dest_addr if t_dest_addr is not None else original['t_dest_addr']),
            't_last_addr' : (t_last_addr if t_last_addr is not None else original['t_last_addr']), 
            't_seq' : (t_seq if t_seq is not None else original['t_seq']), 
            't_time' : (t_time if t_time is not None else original['t_time']),
        }
    
    def findTuple(self, t_dest_addr=None, t_last_addr=None, t_seq=None, t_time=None):
        for i, singleTuple in enumerate(self.topologyTuple):
            if (t_dest_addr is None or singleTuple['T_dest_addr'] == t_dest_addr) and \
                (t_last_addr is None or singleTuple['T_last_addr'] == t_last_addr) and \
                (t_seq is None or singleTuple['T_seq'] == t_seq) and \
                (t_time is None or singleTuple['T_time'] == t_time):
                return i

        return None
                        
    
    def getTuple(self):
        return self.topoloyTuple

class DuplicatedSet:
    '''
    maintain transmitted message 
    to prevent transmitting the same 
    OLSR message twice
    (store packet data which has been processed)
    D_addr              : originator address of the message
    D_seq_num           : message sequence number of the message
    D_retransmitted     : boolean indicating whether the message has been already retransmitted
    D_iface_list        : list of the addresses of the interfaces on which the message has been received
    D_time              : the time at which a tuple expires
    '''
    def _singleTuple(self, d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time):                    
        return [d_addr, d_seq_num, d_retransmitted, [d_iface_list], d_time]
        
    def __init__(self):
        super().__init__()
        self.dTupleList = []
        
    async def run(self): # 일정 시간이 지나면 tuple 삭제
        for i, tuple in enumerate(self.dTupleList):
            if self.checkTimeExpired(tuple[-1]):
                self.dTupleList.pop(i)
                print(f'tuple deleted {i}')
        
    def checkExist_addr_seq(self, d_addr, d_seq_num, check_retransmit=False):      
        print('dup', self.dTupleList)  
        for i, single_tuple in enumerate(self.dTupleList):
            if  single_tuple[0] == d_addr and single_tuple[1] == d_seq_num:
                if check_retransmit:
                    if single_tuple[2] == False:
                        pass
                else:
                    return i
        
        return False
    
    def checkExist_iface(self, ip_address, check_retransmit=False):
        for i, single_tuple in enumerate(self.dTupleList):
            if ip_address in single_tuple[3]:
                if check_retransmit:
                    if single_tuple[2] == False:
                        return i                    
                else:
                    return i
        return -1
                
    def addTuple(self, d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time):
        self.dTupleList.append(self._singleTuple(d_addr, d_seq_num, d_retransmitted, d_iface_list, d_time))
        self.dTupleList.sort(key=lambda x: x[1])
        
    def updateTuple(self, ptr, new_time, dest_addr, retransmit):
        original = self.dTupleList[ptr]
        if new_time is not None:
            original[4] = new_time
        if dest_addr is not None:
            original[3].append(dest_addr)
        if retransmit is not None:
            original[2] = retransmit
        self.dTupleList[ptr] = original 
        self.dTupleList.sort(key=lambda x: x[1])
        
        
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False  
    
    def getIfaceLst(self, idx):
        return self.dTupleList[idx][3]

class TimeOutManager(threading.Thread):
    '''
    tour every repository and pop element that over times
    '''
    def __init__(self):
        super().__init__()
        self.repository = []    
        
    def run(self):
        for single_repo in self.repository:
            asyncio.run(single_repo.run())

        time.sleep(1)

    def addRepository(self, repo_lst):
        for repo in repo_lst:
            self.repository.append(repo)
    
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
        self.route_table.append({
            'R_dest_addr' : R_dest_addr,
            'R_next_addr' : R_next_addr,
            'R_dist' : R_dist,
            'R_iface_addr' : R_iface_addr
            })
        
    def resetTuple(self):
        self.route_table = []
        
    def checkExist(self, addr):
        for route in self.route_table:
            if route['R_dest_addr'] == addr:
                return route
            
        return False
        
    def checkExistDest(self, addr):
        for route in self.route_table:
            if route['R_dest_addr'] == addr:
                return route['R_dist']
            
        return False
    
    def checkExistNext(self, addr):
        for route in self.route_table:
            if route['R_dest_addr'] == addr:
                return route['R_next_addr']
            
        return False
    
    def getDestExcept(self, ip_addr):
        bridge_addr = []
        for route in self.route_table:
            if route['R_next_addr'] != ip_addr:
                bridge_addr.append(route['R_dest_addr'])
                
        return bridge_addr    
    
    def updateTuple(self, idx, R_dest_addr=None, R_next_addr=None, R_dist=None,\
        R_iface_addr=None):
        original = self.route_table[idx]
        self.route_table[idx] = {            
            'R_dest_addr' : R_dest_addr if R_dest_addr is not None else original['R_dest_addr'],
            'R_next_addr' : R_next_addr if R_next_addr is not None else original['R_next_addr'],
            'R_dist' : R_dist if R_dist is not None else original['R_dist'],
            'R_iface_addr' : R_iface_addr if R_iface_addr is not None else original['R_iface_addr'],
        }
            
    def getNextAddr(self, dest_addr):
        for single_tuple in self.route_table:
            if single_tuple['R_dest_addr'] == dest_addr:
                return single_tuple['R_next_addr']
        return False
            
class ReachablitySet():
    def __init__(self) -> None:
        self.reachablity_tuple = []
    
    def addTuple(self, r_neighbor_addr, r_neighbor_move_status, r_neighbor_reachable_list):
        self.reachablity_tuple.append({
            'r_neighbor_addr' : r_neighbor_addr,
            'r_neighbor_move_status' : r_neighbor_move_status, 
            'r_neighbor_reachable_list' : r_neighbor_reachable_list
        })
    
    def sortTuple(self):
        self.reachablity_tuple.sort(key=lambda x: x['r_neighbor_move_status'], reverse=True)
        self.reachablity_tuple.sort(key=lambda x: len(x['r_neighbor_reachable_list']), reverse=True)
        
    def getAllReachable(self):
        all_reachable_list = []
        for single_lst in self.reachablity_tuple:
            all_reachable_list.extend(single_tuple for single_tuple in single_lst \
                if single_tuple not in all_reachable_list)
            
        return all_reachable_list
    
    def getTuple(self):
        return self.reachablity_tuple
    
        
if __name__ == '__main__':
    # duplicated Set Test
    
    duplicated_set = DuplicatedSet()
    duplicated_set.addTuple(808464432, 12337, False, '127.0.0.1', 1705926862.1785054)
    print(duplicated_set.dTupleList)
    print(duplicated_set.checkExist_addr_seq(808464432,12337))
    print(duplicated_set.checkExist_addr_seq(808464432,12338))
    duplicated_set.addTuple(808464432, 12338, False, '127.0.0.1', 1705926862.1785054)
    print(duplicated_set.checkExist_addr_seq(808464432,12338))
    print(duplicated_set.checkExist_iface('127.0.0.1'))