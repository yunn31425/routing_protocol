from collections.abc import Callable, Iterable, Mapping
import threading
from typing import Any
from constants import *
import time
import struct
        

def decode_validTime(valid_time):
    '''
    decode vaild time from binary to integer
    '''
    c = 0.0625
        
    mantissa = (valid_time >> 4) & 0x0f
    exponent = valid_time & 0x0f
    
    return C*(1+mantissa/16) * (2**exponent)

def encode_validTime(emission_interval):
    '''
    encode vaild time from  to binary
    '''
    mantissa = 0
    exponent = 0

    # Calculate the exponent first
    while emission_interval >= C:
        emission_interval /= 2
        exponent += 1

    # Calculate the mantissa
    mantissa = int((emission_interval / C - 1) * 16)

    # Combine mantissa and exponent into Htime
    Htime = (mantissa << 4) | exponent
    return Htime

class helloMessage(threading.Thread):
    '''
    hello message handler
    message type : hello message
    TTL : 1
    VTime set by NEIGHB_HOLD_TIME
    generated based on link set, neighbor set, MPR set 
    
    never be forwarded or recoreded to duplicated set
    '''
    def __init__(self, parent, ip_address) -> None:
        super().__init__()
        self.last_emission_time = 0
        self.parent = parent
        self.ip_address = ip_address
        
    def run(self):
        if self.last_emission_time - time.time() > HELLO_INTERVAL:
            self.packMessage()
            self.last_emission_time = time.time()
            
    def packMessage(self):
        '''
        pack hello message
        '''
        packet_format = '!HBB'
        packed_data = struct.pack(packet_format,
                                    RESERVED,             # 0, 16bits
                                    encode_validTime(NEIGHB_HOLD_TIME),     # Htime 8bits # mentissa needtobecheck
                                    WILL_DEFAULT)         # willingness default 8bits
        packet_format = '!BBHI'
        for single_tuple in self.parent.link_set.getTuple():
            link_code = NOT_NEIGH
            if self.parent.mprSet.checkExist(single_tuple._l_neighbor_iface_addr):
                link_code = MPR_NEIGH
            else:
                link_code = self.parent.neighbor_set.checkExist(single_tuple._l_neighbor_iface_addr)
            link_code = (link_code<<2) + single_tuple.getLinkType()
            link_message_size = 32*3
            packed_data += struct.pack(packet_format,
                                        link_code,
                                        RESERVED,
                                        link_message_size,
                                        single_tuple._l_neighbor_iface_addr
                                        )                
        return packed_data
    
    def unpackMessage(self, packed_data): # function need to be checked
        '''
        HBB : RESERVED, Htime, willingness
        BBHI : Link Code, RESERVED, Link Message Size, Neighbor interface address...
        '''
        _, Htime, will_value = struct.unpack_from('!HBB',packed_data, offset=0)
        message_size = int(len(packed_data)/4) - 1
        unpacked_data = [_ for _ in range(int(message_size/2))]
        for i in range(int(message_size/2)):
            unpacked_data[i] = list(struct.unpack_from('!BBH', packed_data, offset=4+i*8))
            unpacked_data[i] += list(struct.unpack_from(f'!I', packed_data, offset=8+i*8)) # need to be checked
            
            
        return Htime, will_value, unpacked_data

    def encodeLinkCode(self, neigh_type, link_type):
        data = (neigh_type<<2) & 0x0C
        data += link_type & 0x03
        
        return data
    
    def decodeLinkCode(self, linkCode):
        neigh_type = (linkCode>>2) & 0x03
        link_type = linkCode & 0x03
        
        return neigh_type, link_type

    def processMessage(self, single_packet, source_addr):
        '''link_code -> neighbor type and Link type todo 
        BBHI : (link_code, reserved, link Message size, neighbor inteface address)
        link Tuple : (l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time)
        '''
        Htime, will_value, unpacked_data_lst = self.unpackMessage(single_packet['message'])
        
        for unpacked_data in unpacked_data_lst:
            # process for link tuple
            link_tuple_exist = self.parent.link_set.checkExist(source_addr)
            if  link_tuple_exist:
                # need to be checked ASYM_TIME value?
                self.parent.link_set.addTuple(self.ip_address, source_addr, time.time()-1, None, time.time()+single_packet['vtime'])
            else:
                self.parent.link_set.updateTuple(link_tuple_exist, None, None, None, time.time() + single_packet['vtime'], None)
                if self.ip_address == unpacked_data[4]:
                    if unpacked_data[1] == LOST_LINK:
                        self.parent.link_set.updateTuple(link_tuple_exist, None, None, time.time() - 1, None, None)
                    elif unpacked_data[1] == SYM_LINK or unpacked_data[1] == ASYM_LINK:
                        self.parent.link_set.updateTuple(link_tuple_exist, None, None, time.time() + single_packet['vtime'], None, time.time() + single_packet['vtime'] + NEIGHB_HOLD_TIME)
                self.parent.link_set.lTimeMax(link_tuple_exist) # why?
                
            # process for neighbor_tuple
            neigh_tuple_exist = self.parent.neighbor_set.checkExist(source_addr)
            if neigh_tuple_exist:
                self.parent.neighbor_tuple_update_will(neigh_tuple_exist, will_value)
                
            # process for 2_hop_neighbor_tuple            
            if link_tuple_exist and self.parent.link_set.checkLinkType(link_tuple_exist) == SYM_LINK:
                if unpacked_data[0] == SYM_NEIGH or unpacked_data[0] == MPR_NEIGH:
                    if unpacked_data[0] == self.ip_address:
                        pass #slightly discard packet
                    else:
                        self.parent.two_hop_neighbor_set.addTuple(source_addr, unpacked_data[4], time.time() + single_packet['vtime'])
                
                elif unpacked_data[0] == NOT_NEIGH:
                    self.parent.two_hop_neighbor_set.addTuple(source_addr, unpacked_data[4])
                else:
                    print("undefined type")
                
            # process for MPR Set - calculated with MPR
            # MPR set has to be recalculated when change occurs in SYM_NEIGH or 
            #self.parent.mprSet
            '''
            self.mprSet = MPRSet()
            self.neighbor_set = NeighborSet()
            self.link_set = LinkSet()
            self.two_hop_neighbor_set = TwoHopNeighborSet()
            self.duplicated_set = DuplicatdSet()
            '''
            temp_mpr = self.parent.neighbor_set.filterWillingness(WILL_ALWAYS)
            n = self.parent.neighbor_set.getNeigh()
            n2 = self.parent.two_hop_neighbor_set.getTwoHopNeigh()
            node_d = [] # D(y) for each nodes in neighbor tuple
            for n_node in self.parent.neighbor_set.getTuple():
                node_d.append(self.parent.two_hop_neighbor_set.calculateDegree(n_node))
            onlyNode, coverNode = self.parent.two_hop_neighbor_set.checkSingleLink()
            temp_mpr += onlyNode
            
            #n2.remove(node for node in coverNode)
            n2 = [node for node in n2 if node not in coverNode]
            
            while n2:
                reachability = {node: sum(1 for n in n2 if n not in temp_mpr) for node in n}

                # 단계 4.2: N_willingness가 가장 높고 도달성이 0이 아닌 노드 선택
                selected_node = max(n, key=lambda node: (n[node], reachability[node]))
                temp_mpr.add(selected_node)

                # MPR 세트에 의해 커버된 노드 제거
                for neighbor in n[selected_node]:
                    n2.discard(neighbor)     
                    
            self.parent.mprSet.updateMpr(temp_mpr)         
                    
                    
            # process for mpr selector set
            if unpacked_data[1] == MPR_NEIGH:
                for msg in unpacked_data[3:]:
                    if msg == self.ip_address:
                        self.parent.mprSelector_set.addTuple(source_addr)
                
        # todo : 이웃 사라짐 -> 해당 이웃에 대한 2hop 이웃 삭제, MPR selector에서 삭제, 
        # todo : 이웃 변동시 MPR set 재계산
        # todo : MPR set 변동시 HELLO MESSAGE 재발송
        
    def forwardMessage(self):
        '''
        hello message MUST never be forwarded
        '''
        return 
    
class TCMessage(threading.Thread):
    '''
        packet TC message
        -> link sensing과 neighbor detection을 통해 수집한 정보 전파
        -> 라우팅을 위한 경로 전송
    '''
    def __init__(self, parent) -> None:
        self.last_msg_trans_time = 0
        self.last_message_sequence = 0 # 링크 추가 및 삭제시 증가 구현 todo
        self.parent = parent
        
    def run(self) -> None:
        while True:
            if self.last_msg_trans_time - time.time() > TC_INTERVAL:
                self.generateMessage()
    
    def packMessage(self, ansn, adversized_nei_addr):
        '''
        TTL : 225, Vtime : TOP_HOLD_TIME
        ANSN : Advertised Neighbor Sequence Number
        Advertised Neighbor Main Address
        '''
        packed_data = struct.pack('!HH', ansn, 0)
        for addr in adversized_nei_addr:
            packed_data += struct.pack('!I', addr)
            
        return packed_data            

    def unpackMessage(self, packed_data, length):
        '''
        ANSN, RESERVED, advertisesd main address ....
        '''
        ansn = struct.unpack_from('!H', packed_data, 0)
        for i in range(length): # todo - length 고려 길이 맞추어 줄 것
            unpacked_data += struct.unpack_from('!I', unpacked_data, i)
            
        return unpacked_data
        
    def generateMessage(self):
        address = []
        for addr in self.parent.neighbor_set.getTuple():
            address.append(addr[0])
        packed_message = self.packMessage(self.last_message_sequence, address)
        packet_packet = self.parent.packet_header_handler(packed_message)
        self.parent.sender(packet_packet)
    
    def forwardMessage(self):
        '''
        TC message must be forwarded according to the default forwarding algorithm
        '''
        pass
            
    def processMessage(self, single_msg, source_addr):
        '''
        message_type, vtime, message_size, originator_add, ttl, Hop_count, message_seq_num, message
        '''
        ansn, neighbor_addrsss = self.unpackMessage(single_msg['message'], single_msg['message_size']) # todo 메세지 사이즈 부적확
        if self.parent.link_set.getLinkType(source_addr) != SYM_LINK:
            return
        
        t_seq = self.parent.topology_set.getTupleAddr(source_addr)

        if t_seq > ansn:
            return
        elif t_seq < ansn:
            self.parent.topology_set.delTuple(source_addr)

        for addr in neighbor_addrsss:
            addr_idx = self.parent.topology_set.findTuple(addr, source_addr)
            if addr_idx:
                self.parent.topology_set.updateTuple(addr_idx, None, None, None, time.time() + single_msg['vtime'])
            else:
                self.parent.topology_set.addTuple(addr, source_addr, ansn, time.time() + single_msg['vtime'])
   
class MoveMessage(threading.Thread):
    '''
    soruce : monitor current node movement ->
    soruce : send message to one hop neighbor ->
    neighbor : compare it with its location ->
    neighbor :send back if they are coming close ->
    source : select neighbor to be connect and broadcast ->
    all nodes : change its routing table element of moving node
    
    Message Format
    0                    1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Node Type          |          Message Size         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Longitude          |            Latitude           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Altitude           |        Velocity_North         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |         Velocity_East         |         Velocity_Down         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                       Interface Address                       |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    :                             . . .                             :
    :                                                               :
    
    Node Type : 1 : moving Node, 2 : Moving Close Node, 3 : Moving away Node
    '''
    
    def __init__(self) -> None:
        pass
    def packMessage(self):
        pass
    def unpackMessage(self):
        pass
    def forwardMessage(self):
        pass
    def processMessage(self):
        pass
    
class RecalcMesage(threading.Thread):
    '''
    emitted by moving node 
    if a node receive this message of (moving node, bridge node),
    routing toward moving node SHOULD be changed toward bridge node first
    
    Message Format
    0                    1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Node Type          |          Message Size         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                  Moving Node Interface Address                |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                  Bridge Node Interface Address                |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                  Bridge Node Interface Address                |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    :                             . . .                             :
    :                                                               :
    
    Node Type : 1 : moving Node, 2 : Moving Close Node, 3 : Moving away Node
    '''
    
    def __init__(self) -> None:
        pass
    def packMessage(self):
        pass
    def unpackMessage(self):
        pass
    def forwardMessage(self):
        pass
    def processMessage(self):
        pass
    
class MIDMessage(threading.Thread):
    '''
    not defined yet : todo
    ''' 
    def __init__(self):
        super().__init__()