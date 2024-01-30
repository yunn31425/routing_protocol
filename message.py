from collections.abc import Callable, Iterable, Mapping
import threading
from constants import *
import time
import struct
from gps_interface import *
from multiprocessing import Process, Manager, Queue
from geopy.distance import distance
from math import sqrt
import time

def decode_validTime(valid_time):
    '''
    decode vaild time from binary to integer
    '''
    mantissa = (valid_time >> 4) & 0x0f
    exponent = valid_time & 0x0f
    
    return int(C*(1+mantissa/16) * (2**exponent))

def encode_validTime(emission_interval):
    '''
    encode vaild time from  to binary
    '''
    mantissa = 0
    exponent = 0

    # Calculate the exponent first
    while emission_interval > C:
        emission_interval /= 2
        exponent += 1

    # Calculate the mantissa
    mantissa = int(((emission_interval / C) - 1) * 16)
    # Combine mantissa and exponent into Htime
    Htime = (mantissa << 4) | exponent
    print('endcoded : ', Htime)
    return Htime

def encodeIPAddr(ip_addr : str):
    binary_addr = b''
    for digit in ip_addr.split('.'):
        binary_addr += struct.pack('!B', int(digit))
        
    return binary_addr

def decodeIPAddr(ip_addr : int):
    tpl = struct.unpack('!BBBB', ip_addr)
    return str(tpl[0]) + '.' + str(tpl[1]) + '.' \
        + str(tpl[2]) + '.' + str(tpl[3])

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
        self.willingness = WILL_DEFAULT
        self.seq_num = 0
        
    def run(self):
        while True:
            if time.time() - self.last_emission_time > HELLO_INTERVAL:
                self.last_emission_time = time.time()
                print('hello message emitted')
                self.packMessage()
            else:
                time.sleep(HELLO_INTERVAL/2)
            
    def packMessage(self):
        '''
        pack hello message
        '''
        packet_format = '!HBB'
        packed_data = struct.pack(packet_format,
                                    RESERVED,             # 0, 16bits
                                    encode_validTime(HELLO_INTERVAL),     # Htime 8bits # mentissa needtobecheck
                                    self.willingness)         # willingness default 8bits
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
                                        encodeIPAddr(single_tuple._l_neighbor_iface_addr)
                                        )                  
        packed_packet = self.parent.packet_header_handler.attatchHeader(
            [HELLO_MESSAGE, HELLO_INTERVAL, 2, self.seq_num, packed_data]
            )
        self.seq_num += 1
        asyncio.run(self.parent.sender.broadcastMsg(packed_packet))
    
    def unpackMessage(self, packed_data):
        '''
        HBB : RESERVED, Htime, willingness
        BBHI : Link Code, RESERVED, Link Message Size, Neighbor interface address...
        '''
        _, Htime, will_value = struct.unpack_from('!HBB',packed_data, offset=0)
        Htime = decode_validTime(Htime)
        
        if len(packed_data) == 4:
            return Htime, will_value, []
        else:
            ptr = 4
            unpacked_data = []
            while ptr < len(packed_data):
                packed_data.append(list(struct.unpack_from('!BBH', packed_data, offset=ptr)))
                interface_length = int((packed_data[-1][2]-4)/4)
                packed_data[-1] += list(struct.unpack_from(f'!I{interface_length}', packed_data, offset=ptr+4))
                ptr += (4 + interface_length*4)
    
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
        print(single_packet['message'])
        Htime, will_value, unpacked_data_lst = self.unpackMessage(single_packet['message'])
        print('unpacked_data_lst', unpacked_data_lst)
        if len(unpacked_data_lst) == 0:
            if self.parent.link_set.checkExist(source_addr) == False:
                print(singletuple for singletuple in self.parent.link_set.tupleList)
                self.parent.link_set.addTuple(self.ip_address, source_addr, time.time()-1, None, time.time()+single_packet['vtime'])
            
        for unpacked_data in unpacked_data_lst:
            print("process for link tuple")
            link_tuple_exist = self.parent.link_set.checkExist(source_addr)
            if link_tuple_exist == False:
                # need to be checked ASYM_TIME value?
                print(self.parent.link_set.tupleList)
                self.parent.link_set.addTuple(self.ip_address, source_addr, time.time()-1, None, time.time()+single_packet['vtime'])
            else:
                self.parent.link_set.updateTuple(link_tuple_exist, None, None, None, time.time() + single_packet['vtime'], None)
                if self.ip_address == unpacked_data[4]:
                    if unpacked_data[1] == LOST_LINK:
                        self.parent.link_set.updateTuple(link_tuple_exist, None, None, time.time() - 1, None, None)
                    elif unpacked_data[1] == SYM_LINK or unpacked_data[1] == ASYM_LINK:
                        self.parent.link_set.updateTuple(link_tuple_exist, None, None, time.time() + single_packet['vtime'], None, time.time() + single_packet['vtime'] + NEIGHB_HOLD_TIME)
                self.parent.link_set.lTimeMax(link_tuple_exist) 
                
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
        
    def forwardMessage(self, single_message):
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
        super().__init__()
        self.name = 'tc_message_handler'    
        self.last_msg_trans_time = 0
        self.last_message_sequence = 0 # 링크 추가 및 삭제시 증가 구현 todo
        self.parent = parent
        
    def run(self) -> None:
        while True:
            if time.time() - self.last_msg_trans_time > TC_INTERVAL:
                self.last_msg_trans_time = time.time()
                print('TCMessage emitted')
                self.generateMessage()
            else:
                time.sleep(TC_INTERVAL/2)
    
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
        unpacked_data = None
        for i in range(length): # todo - length 고려 길이 맞추어 줄 것
            unpacked_data += struct.unpack_from('!I', packed_data, i)
            
        return unpacked_data
        
    def generateMessage(self):
        address = []
        for addr in self.parent.neighbor_set.getTuple():
            address.append(addr[0])
        packed_message = self.packMessage(self.last_message_sequence, address)
        packet_packet = self.parent.packet_header_handler.attatchHeader(
            [TC_MESSAGE, TOP_HOLD_TIME, 255, self.last_message_sequence, packed_message])
        asyncio.run(self.parent.sender.SendToMPR(packet_packet))
        self.last_message_sequence += 1
    
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
    |                       Interface Address                       |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    
    * MOVE_MOVE_NODE
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Longitude          |            Latitude           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Altitude           |        Velocity_North         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |         Velocity_East         |         Velocity_Down         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    
    * MOVE_CLOSE_NODE, MOVE_AWAY_NODE, 
    * NODE_ROUTE_RECALC
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                  Bridge Node Interface Address                |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                  Bridge Node Interface Address                |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    :                             . . .                             :
    :                                                               :
    
    Node Type : 1 : moving Node, 2 : Moving Close Node, 3 : Moving away Node
                4 : recalc Message
    '''
    
    def __init__(self, parent) -> None:
        self.gps_handler = GPSReceiver(parent.logger)
        self.check_time_prev = 0
        self.longitude_prev = None
        self.latitude_prev = None
        self.msg_seq_num = 0
        self.ip_address = parent.ip_address
        
        self.parent = parent
        self.logger = parent.logger
        self.sendr = parent.sender
        self.status = MOVE_DEFAULT_STATE
        self.monitoring_process = Process(target=self.monitorVelocity)
        
        self.monitoring_process.start()        
    
    def monitorVelocity(self):
        while True:
            if time.time() - self.check_time_prev > VELO_CHECK_PERIOD:
                if self.gps_handler.checkStatus():
                    
                    self.check_time_prev = time.time()
                    if self.gps_handler.getVelocity()['velocity'] > MOVE_VELO_THRESHOLD:
                        self.broadcastMoveMsg()
                        time.sleep(MOVE_INTERVAL)
                        necessary_neighbor = self.calcNecessaryNeighbor()
                        self.broadcastRecalc(necessary_neighbor)
                
    def broadcastMoveMsg(self):        
        message_contents = self.packMessageMoving(MOVE_MOVE_NODE, self.gps_handler.getVelocity(), \
            self.gps_handler.getCoordinate())
        packet_contents = self.parent.packet_header_handler.attatchHeader(
            [MOVE_MESSAGE, 2, 2, self.msg_seq_num, message_contents])
        self.sender.broadcastMsg(packet_contents)
        self.status = MOVE_MESSAGE_SENT_STATE
        
    def broadcastRecalc(self, necessary_neighbor):
        message_contents = self.packMessageRecv(necessary_neighbor, NODE_ROUTE_RECALC)
        packet_contents = self.parent.packet_header_handler.attatchHeader(
            [MOVE_MESSAGE, TOP_HOLD_TIME, 255, self.msg_seq_num, message_contents])
        self.sender.broadcastMsg(packet_contents)
        self.status = MOVE_DEFAULT_STATE
    
    def sendNodeMovement(self, interface_list, node_type, sent_interface_addr):
        message_contents = self.packMessageRecv(interface_list, node_type)
        packet_contents = self.parent.packet_header_handler.attatchHeader(
            [MOVE_MESSAGE, TOP_HOLD_TIME, 255, self.msg_seq_num, message_contents])
        
        asyncio.run(self.sender.sendMsg(packet_contents, sent_interface_addr))
        
    def packMessageRecv(self, interface_addr, node_type):
        packet_format1 = '!HH'
        packed_data = struct.pack(packet_format1, node_type, len(interface_addr)*4+8)
        packed_data += encodeIPAddr(self.parent.sender.getIPAddr())
        for addr in interface_addr:
            packed_data += encodeIPAddr(addr)
            
        return packed_data    

    def packMessageMoving(self, nodeType, velocity, coordinate):
        '''
        message send by moving node
        '''
        packet_format1 = '!HH'
        packet_format2 = '!eeeeee'
        packed_data = struct.pack(packet_format1, nodeType, 20)
        packed_data += encodeIPAddr(self.parent.sender.getIPAddr())
        packed_data += struct.pack(packet_format2, coordinate['longitude_deg'], \
            coordinate['latitude_deg'], coordinate['absolute_altitude_m'], velocity['north_m_s'],\
                velocity['east_m_s'], velocity['down_m_s'])
        return packed_data
    
    def calcRelativeVel(self, nodedata):
        '''
        check if this node and moving node is getting closer or away
        '''
        cur_velosity = self.gps_handler.getVelocity()
        
        relative_velocity = sqrt((cur_velosity['north_m_s'] - nodedata['north_m_s'])**2 +
                            (cur_velosity['east_m_s'] - nodedata['east_m_s'])**2 +
                            (cur_velosity['down_m_s'] - nodedata['down_m_s'])**2)
        
        return MOVE_CLOSE_NODE if relative_velocity > -1 else MOVE_AWAY_NODE
    
    def unpackMessage(self, binary_data):
        packet_format = '!HHI'
        message_type, message_size, sent_interface_addr = struct.unpack(packet_format, binary_data)
        node_data = None
        
        if message_type == MOVE_MOVE_NODE:
            unpacked_data = struct.unpack_from('!eeeeee', binary_data, 8)
            node_data = {
            'longitude' : unpacked_data[0],
            'latitude' : unpacked_data[1],
            'altitude' : unpacked_data[2],
            'vel_north' : unpacked_data[3],
            'vel_east' : unpacked_data[4],
            'vel_down' : unpacked_data[5]
            }
        elif message_type in [MOVE_CLOSE_NODE, MOVE_AWAY_NODE, NODE_ROUTE_RECALC]:
            unpacked_data = struct.unpack_from(f'!I{message_size-8}', binary_data, 8)
            node_data = unpacked_data
        else:
            print("undefined message")
            return
                
        return node_data, message_type, sent_interface_addr
    
    def forwardMessage(self, message):
        '''
        MoveMessage need to be forwarded if message type is NODE_ROUTE_RECALC
        '''
        node_data, message_type, sent_interface_addr = self.unpackMessage(message)
        if message_type == NODE_ROUTE_RECALC:
            packed_packet = self.parent.packet_header_handler.attatchHeader(
            [NODE_ROUTE_RECALC, NODE_RECALC_INTERVAL, 1, self.seq_num, message]
            )
            asyncio.run(self.parent.sender.broadcastMsg(packed_packet)) #todo
        else:
            return
        
    def routeRecalc(self, r_neighbor_reachable_list, moving_node_ip):
        min_hop = float('INF')
        next_addr = None
        for i, route in enumerate(self.parent.RouteTable.getTuple()):
            if route['R_dest_addr'] in r_neighbor_reachable_list and route['R_dist'] < min_hop:
                min_hop = route['R_dist']
                next_addr = route['R_next_addr']
                
        for i, route in enumerate(self.parent.RouteTable.getTuple()):
            if route['R_dest_addr'] == moving_node_ip:
                self.parent.RouteTable.updateTuple(None, next_addr, min_hop+1, None)            
    
    def calcNecessaryNeighbor(self):
        '''
        for a moving node, after gathering all messages from neighbor node
        '''
        all_reachable = self.parent.reachable_set.getAllReachable()
        necessary_neighbor = []
        while len(all_reachable) > 0:
            for single_lst in self.parent.reachable_set.getTuple():
                necessary_neighbor.append(single_lst)
                all_reachable = [single_addr for single_addr in all_reachable \
                                 if single_addr not in single_lst['r_neighbor_reachable_list']]
                
        return necessary_neighbor
    
    def processMessage(self, binary_packet):
        node_data, message_type, sent_interface_addr = self.unpackMessage(binary_packet)
        if message_type == NODE_ROUTE_RECALC:
            self.routeRecalc(node_data, sent_interface_addr)
        elif  message_type == MOVE_MOVE_NODE:
            node_type = self.calcRelativeVel(node_data)
            interface_list = self.parent.getDestExcept(sent_interface_addr)
            self.sendNodeMovement(interface_list, node_type, sent_interface_addr)
        elif self.status == MOVE_MESSAGE_SENT_STATE: 
           self.parent.reachable_set.addTuple(sent_interface_addr, message_type, node_data)
        
class MIDMessage(threading.Thread):
    '''
    not defined yet : todo
    ''' 
    def __init__(self):
        super().__init__()