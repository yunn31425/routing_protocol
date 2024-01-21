'''
OLSR ad hoc routing protocol 
RFC 3236
only for single network interface
'''

from collections.abc import Callable, Iterable, Mapping
import sys
import logging 
import struct
import socket
import threading
import time
import subprocess
import fcntl
import queue
import gc

from typing import Any
from scapy.all import*  
from numba import jit

from informationRepo import * 
from forwarder import *
from constants import *


if __name__ == '__main__':
    
    nodeLogger = logging.getLogger("node")
    nodeLogger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler('olsr.log')
    nodeLogger.addHandler(file_handler)
    
    # if len(sys.argv) == 1:
    #     print("enter network interface name")
    #     exit()
    
    #todo 소켓 리셋 sender에 넣기 -> broadcaste r가 아니라
    
    try:
        listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listenSocket.bind(('', PORTNUM_SEND))
        listenSocket.listen()
        listenSocket.close()
        listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listenSocket.bind(('', PORTNUM_RECV))

    except OSError as e:
        if e.errno == 98:
            print("port is already in use")
            listenSocket.close()
        else:
            interface_info = fcntl.ioctl(listenSocket.fileno(), 0x8915, struct.pack('256s', (sys.argv[1])).encode('utf-8'))
            ip_address = socket.inet_ntoa(struct.unpack('4s', interface_info[20:24])[0])
        exit()
        
    # check if network mode is ad-hoc not managed
    # if (subprocess.run('iwconfig | grep Mode', shell=True, capture_output=True, text=True).stdout).split(' ')[10] == "Mode:Managed":
    #     print("change mode into ad-hoc first")
    #     exit()
    
    def deconde_validTime(valid_type):
        c = 0.0625
        if valid_type == 1:
            valid_time = 1
            
        mantissa = (valid_time >> 4) & 0x0f
        exponent = valid_time & 0x0f
        
        return c*(1+mantissa/16) * (2**exponent)
    
    def encode_validTime(valid_type):
        pass #todo

    class Sender:
        def __init__(self) -> None:
            pass
        
    class packetForwarder(threading.Thread):
        '''
        read packet and forward packet
        '''
        def __init__(self, interface_name):
            super().__init__()

            self.mprSet = MPRSet()
            self.neighbor_set = NeighborSet()
            self.link_set = LinkSet()
            self.two_hop_neighbor_set = TwoHopNeighborSet()
            self.duplicated_set = DuplicatdSet()
            self.mprSelector_set = MPRSelectorSet()
            self.topology_set  = TopologyInfo()
            self.route_table = RouteTable()
            
            self.packet_queue = queue.Queue()
            self.transmit_queue = queue.Queue()
            
            self.interface_name = interface_name            
            
            self.sender = Sender()
            
            self.hello_message_handler = helloMessage(self)    
            self.packet_header_handler = PacketHeader()
            self.tc_message_handler = TCMessage(self)
            
            self.enqueue_thread = threading.Thread(target=self.enqueue())
            self.dequeue_thread = threading.Thread(target=self.dequeue())
            self.transmit_thread = threading.Thread(target=self.transmit())
                    
            self.enqueue_thread.start()
            self.dequeue_thread.start()
            self.transmit_thread.start()
            
            self.enqueue_thread.join()
            self.dequeue_thread.join()
            self.transmit_thread.join()
            
        def enqueuing(self, packet):
            while True:
                self.packet_queue.put(packet)
                
        def enqueue(self):
            sniff(iface=self.interface_name, store=False, prn=self.enqueuing)
            
        def dequeue(self):
            while True:
                if not self.packet_queue.empty():
                    single_packet = self.packet_queue.get()
                    self.packet_processing(packet=single_packet)
            
        def packet_processing(self, packet):
            if struct.calcsize(packet) == PACKET_HEADER_SIZE + MSG_HEADER_SIZE:
                return
            seq_num, message_contents = PacketHeader().detatchHeader(packet)
            source_addr = packet[scapy.IP].src
            dest_addr = packet[scapy.IP].dest
            for single_msg in message_contents:
                if single_msg['ttl'] < 2: # need to be checked
                    continue 
                if self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], message_contents['message_seq_num']):
                    continue # already processed message
                else:  
                    # process message 
                    if single_msg['message_type'] == HELLO_MESSAGE: 
                        self.hello_message_handler.processMessage(single_msg, source_addr)
                    elif single_msg['message_type'] == TC_MESSAGE:
                        self.tc_message_handler.processMessage(single_msg, source_addr)
                    elif single_msg['message_type'] == MID_MESSAGE:
                        pass # not yet to deal with it
                    elif single_msg['message_type'] == HNA_MESSAGE:
                        pass # not yet to deal with it
                    else:
                        print('unidenfitied message type')
                    
                    # message  # need to be check
                    if self.duplicated_set.checkExist_iface(ip_address) and \
                        self.duplicated_set.checkExist_iface(dest_addr):
                        continue # message which has been forwarded 
                    elif single_msg['message_type'] == HELLO_MESSAGE: 
                        self.hello_message_handler.forwardMessage(single_msg)
                    elif single_msg['message_type'] == TC_MESSAGE:
                        self.defaultForward(single_msg, source_addr, dest_addr)
                    elif single_msg['message_type'] == MID_MESSAGE:
                        pass # not yet to deal with it
                    elif single_msg['message_type'] == HNA_MESSAGE:
                        pass # not yet to deal with it
                    else: # default forwawding
                        self.defaultForward(single_msg, source_addr, dest_addr)

        def defaultForward(self, single_msg, source_addr, dest_addr):
            if self.neighbor_set.checkExist(source_addr) != SYM:
                return
            else:
                if self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], \
                    single_msg['message_seq_num'], True):
                    if self.duplicated_set.checkExist_iface(dest_addr) is False:
                        pass # todo message will be forwarded
                    else:
                        return
                else:
                    pass # todo message will be forwarded
                
            # further process for forwarding
            will_retransmit = False
            if self.mprSet.checkExist(source_addr) and single_msg['ttl'] > 1:
                will_retransmit = True
            ptr = self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], single_msg['message_seq_num'])
            if ptr:
                self.duplicated_set.updateTuple(ptr, time.time() + DUP_HOLD_TIME, dest_addr, will_retransmit)
            else:
                self.duplicated_set.addTuple(single_msg['originator_add'], single_msg['message_seq_num'], will_retransmit,\
                    [dest_addr], time.time() + DUP_HOLD_TIME)
                
            if will_retransmit:
                single_msg['ttl'] -= 1
                single_msg['Hop_count'] += 1
                self.transmit_queue.put(single_msg)
                                    
        def transmit(self):
            while True:
                if not self.transmit_queue.empty():
                    self.transmit_single(self.transmit_queue.get())
                    
        def transmit_single(self, single_message):
            PacketHeader().attatchHeader(single_message)
            pass
        
        def broadcastMessage(self, packed_message):
            with socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(packed_message, (BROADCAST_ADDR, 14567))
                
    class PacketHeader:
        '''
        packet header for olsr protocol
        '''
        def __init__(self, this_node_ip) -> None:
            self.packet_seqence_num = 0
            self.node_ip = this_node_ip
        
        def attatchHeader(self, message_contents):
            packet_contents = ''
            packet_length = 0
            if len(message_contents) == 0:
                return
            for message in message_contents:
                message_size = 0 #todo
                packet_format = '!BBHIBBH' + f'I{message_size}'
                packet_contents += struct.pack(packet_format,
                                               message[0], # message_type
                                               message[1], # vtime
                                               message_size,
                                               self.this_node_ip,   # originator_address
                                               message[2], # time to live
                                               0,                   # hop_count
                                               message[3], # message_seq_num
                                               message[4]) # message conents
                packet_length += message_size + 4*3
                
            packet_contents = struct.pack('!HH', 
                                          packet_length,
                                          self.packet_seqence_num) + packet_contents
            self.packet_seqence_num += 1
            return packet_contents
                
        def detatchHeader(self, binary_packet):
            binary_packet = binary_packet[scapy.Raw].load
            packet_length = struct.unpack_from('!H', binary_packet, 0)
            packet_seq_num = struct.unpack_from('!H', binary_packet, 2)
            message_contents = []
            message_offset = 4
            if packet_length == 4:
                return 
            while packet_length - message_offset > 0:
                message_header = struct.unpack_from('!BBHIBBH', binary_packet, offset=message_offset)
                message_size = message_header[-1]
                message = struct.unpack_from(f'I{message_size}', binary_packet, message_offset + MSG_HEADER_SIZE)
                message_contents.append({
                                            'message_type'      : message_header[0],
                                            'vtime'             : message_header[1],
                                            'message_size'      : message_header[2],
                                            'originator_add'    : message_header[3],
                                            'ttl'               : message_header[4],
                                            'Hop_count'         : message_header[5],
                                            'message_seq_num'   : message_header[6],
                                            'message'           : message                                            
                                        })
                message_offset += (MSG_HEADER_SIZE + message_size)
                
            return packet_seq_num, message_contents                
            
    class helloMessage(threading.Thread):
        '''
        hello message handler
        message type : hello message
        TTL : 1
        VTime set by NEIGHB_HOLD_TIME
        generated based on link set, neighbor set, MPR set 
        
        never be forwarded or recoreded to duplicated set
        '''
        def __init__(self, parent) -> None:
            super().__init__()
            self.last_emission_time = 0
            self.parent = parent
            
        def run(self):
            if self.last_emission_time - time.time() > HELLO_INTERVAL:
                self.packMessage()
                self.last_emission_time = time.time()
                
        def cal_Htime_tobit(self):
            pass
        
        def cal_Htime_todigit(self):
            pass
        
        # todo - parent에서 상속 받아오기
        # todo - genenration과 pack message 모호한 것 나누기
        def packMessage(self):
            '''
            pack hello message
            '''
            packet_format = '!HBB'
            packed_data = struct.pack(packet_format,
                                      RESERVED,             # 0, 16bits
                                      NEIGHB_HOLD_TIME,     # Htime 8bits #todo mentissa todo
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
        
        def unpackMessage(self, packed_data): # todo :
            '''
            HBB : RESERVED, Htime, willingness
            BBHI : Link Code, RESERVED, Link Message Size, Neighbor interface address...
            '''
            size = struct.calcsize(packed_data)
            _, Htime, will_value = map(struct.unpack_from('!HBB',packed_data, offset=0))
            unpacked_data = [_ for _ in range((size-4)/4)]
            for i in range((size-4)/4):
                unpacked_data[i] = list(struct.unpack_from('!BBH', packed_data, offset=3+i*4))
                unpacked_data[i] += list(struct.unpack_from(f'I{(unpacked_data[i][2]-4)/4}', packed_data, offset= 3 + i*4 + 4)) # need to be checked
                
                
            return Htime, will_value, unpacked_data

        def processMessage(self, single_packet, source_addr):
            '''link_code -> neighbor type and Link type todo 
            BBHI : (link_code, reserved, link Message size, neighbor inteface address)
            link Tuple : (l_local_iface_addr, l_neighbor_iface_addr, l_SYM_time, l_ASYM_time, l_time)
            '''
            Htime, will_value, unpacked_data = self.unpackMessage(single_packet['message'])
            
            # process for link tuple
            link_tuple_exist = self.parent.link_set.checkExist(source_addr)
            if not link_tuple_exist:
                # need to be checked ASYM_TIME value?
                self.parent.link_set.addTuple(ip_address, source_addr, time.time()-1, None, time.time()+single_packet['vtime'])
            else:
                self.parent.link_set.updateTuple(link_tuple_exist, None, None, None, time.time() + single_packet['vtime'], None)
                if ip_address == unpacked_data[4]:
                    if unpacked_data[1] == LOST_LINK:
                        self.parent.link_set.updateTuple(link_tuple_exist, None, None, time.time() - 1, None, None)
                    elif unpacked_data[1] == SYM_LINK or unpacked_data[1] == ASYM_LINK:
                        self.parent.link_set.updateTuple(link_tuple_exist, None, None, time.time() + single_packet['vtime'], None, time.time() + single_packet['vtime'] + NEIGHB_HOLD_TIME)
                self.parent.link_set.lTimeMax(link_tuple_exist) # why?
                
            # process for neighbor_tuple
            neigh_tuple_exist = self.parent.neighbor_tuple.checkExist(source_addr)
            if neigh_tuple_exist:
                self.parent.neighbor_tuple_update_will(neigh_tuple_exist, will_value)
                
            # process for 2_hop_neighbor_tuple            
            if link_tuple_exist and self.parent.link_set.checkLinkType(link_tuple_exist) == SYM_LINK:
                if unpacked_data[0] == SYM_NEIGH or unpacked_data[0] == MPR_NEIGH:
                    if unpacked_data[0] == ip_address:
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
            n = self.neighbor_set.getNeigh()
            n2 = self.two_hop_neighbor_set.getTwoHopNeigh()
            node_d = [] # D(y) for each nodes in neighbor tuple
            for n_node in self.parent.neighbor_set.getTuple:
                node_d.append(self.parent.two_hop_neighbor_set.calculateDegree(n_node))
            onlyNode, coverNode = self.two_hop_neighbor_set.checkSingleLink()
            temp_mpr += onlyNode
            
            n2.remove(node for node in coverNode)
            
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
                    if msg == ip_address:
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

        
    # interfaceAss = InterfaceAssociation()
    #LinkSetTuple = LinkSet()
    #neighborTuple = NeighborSet()
    # twoneighborTuple = TwoHopNeighborSet()
    #mprTuple = MPRSet()
    # mprSelector = MPRSelectorSet()
    # topolodyTuple = TopologyInfo()
    #hello = helloMessage()
    #hello.packMessage(LinkSetTuple, neighborTuple, mprTuple)
        
    #- HELLO-messages, performing the task of link sensing, neighbor detection and MPR signaling,
    # - TC-messages, performing the task of topology declaration (advertisement of link states).
    
    
    # neighbor set : creaton : detect link, update : link change, removal : link deleted
    
    forwarder = packetForwarder('wlp1s0')
    
    class MoveMessage(threading.Thread):
        '''
        soruce : monitor current node movement ->
        soruce : send message to one hop neighbor ->
        neighbor : compare it with its location ->
        neighbor :send back if they are coming close ->
        source : select neighbor to be connect and broadcast ->
        all nodes : change its routing table element of moving node
        '''
        
        def __init__(self) -> None:
            pass
        def packMessage(self):
            pass
        def unpackMessage(self):
            pass
        
    class RoutechangeMessage(threading.Thread):
        '''
        soruce : monitor current node movement ->
        soruce : send message to one hop neighbor ->
        neighbor : compare it with its location ->
        neighbor :send back if they are coming close ->
        source : select neighbor to be connect and broadcast ->
        all nodes : change its routing table element of moving node
        '''
        
        def __init__(self) -> None:
            pass
        def packMessage(self):
            pass
        def unpackMessage(self):
            pass
        
    # Routing configuration    
    # data packet forwarding
    
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
                              