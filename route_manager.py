
from constants import * 

class RoutingTableManager:  
    def __init__(self, parent) -> None:
        self.parent = parent
    
    def calculateRoute(self):
        #1
        self.parent.route_table.resetTuple()
        #2
        for neighbor in self.parent.neighbor_set.getTuple():
            if neighbor[1] == SYM:                    
                link_tuple = self.parent.link_set.getTuple(neighbor[0])
                if link_tuple:
                    self.parent.route_table.addTuple(link_tuple[1], link_tuple[1], 1, link_tuple[0])
                else:
                    self.parent.route_table.addTuple(neighbor[0], link_tuple[1], 1, link_tuple[0])
        #3          
        for twoNeighbor in self.parent.two_hop_neighbor_set.getTuple():
            if self.parent.neighbor_set.checkwill(twoNeighbor) != WILL_NEVER:
                self.parent.route_table.addTuple(twoNeighbor[1], twoNeighbor[0], 2, link_tuple[0])
        
        #4 - find route to hop count h+1 (h start from 2)
        for topoTuple in self.parent.topology_set.getTuple():
            route_dest = self.parent.route_table.checkExist(topoTuple[0])
            route_last = self.parent.route_table.checkExist(topoTuple[1])
            if (route_dest == False) and (route_last != False):
                    self.parent.route_table.addTuple(topoTuple[0], route_last['R_next_addr'], \
                        route_last['R_dist' + 1], route_last['R_iface_addr'])
                    
        #5-multiple interface : pass!
