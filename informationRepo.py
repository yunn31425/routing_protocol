import time
import threading


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
    def __init__(self):
        super().__init__()
        self.linkSetTuple = []
        self.start()

    def run(self): # 일정 시간이 지나면 tuple 삭제
        while True:
            for i, tuple in enumerate(self.linkSetTuple):
                if self.checkTimeExpired(tuple[-1]):
                    self.linkSetTuple.pop(i)
                    print(f'tuple deleted {i}')
        
    def addTuple(self, l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time = time.time()):
        self.linkSetTuple.append((l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time))
    
    def delTuple(self, index):
        self.linkSetTuple.pop(index)
    
    def checkTimeExpired(self, addtime):
        if time.time() - addtime > 1: # time has to be checked 
            return True
        return False
    
    def checkLinkStatus(self, index):
        if self.linkSetTuple[index][2] > time.time():
            return 'symmetric'
        elif self.linkSetTuple[index][3] > time.time():
            return 'asymmetric'
        else:
            return 'lost'
        
class NeighborSet:
    def __init__(self):
        super().__init__()
        self.neighborTuple  = []

    def addTuple(self, n_neighbor_main_addr, n_status, n_willingness):
        self.neighborTuple.append((n_neighbor_main_addr, n_status, n_willingness))
    
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
        self.MPRTuple  = []
        self.start()

    def addTuple(self, neighbor):
        self.MPRTuple.append(neighbor)
    
    def delTuple(self, index):
        self.MPRTuple.pop(index)    
        
class MPRSelectorSet(threading.Thread):
    def __init__(self):
        super().__init__()
        self.mprSelectorTuple  = []
        self.start()

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
        self.start()

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