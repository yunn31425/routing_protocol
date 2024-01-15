'''
OLSR ad hoc routing protocol 
RFC 3236
only for single network interface
'''

from collections.abc import Callable, Iterable, Mapping
import sys
import socket
import logging 
import struct
from socket import *
import threading
import time
import subprocess
import fcntl
import queue
import gc

from typing import Any
from scapy.all import *
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
    
    #todo 소켓 리셋 sender에 넣기 -> broadcaster가 아니라
    
    try:
        listenSocket = socket(AF_INET, SOCK_STREAM)
        listenSocket.bind(('', PORTNUM_SEND))
        listenSocket.listen()
        listenSocket.close()
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
            self.enqueue_thread = threading.Thread(target=self.enqueue())
            self.dequeue_thread = threading.Thread(target=self.dequeue())
            self.transmit_thread = threading.Thread(target=self.transmit())
            
            self.mprSet = MPRSet()
            self.neighbor_set = NeighborSet()
            
            self.packet_queue = queue.Queue()
            self.transmit_queue = queue.Queue()
            
            self.interface_name = interface_name
            self.duplicated_set = DuplicatdSet()
            
            self.sender = Sender()
            self.hello_message_handler = helloMessage()
            
            
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
            scapy.sniff(ifaces=self.interface_name, store=False, prn=self.enqueuing)
            
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
                if single_msg['ttl'] < 2:
                    continue
                if self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], message_contents['message_seq_num']):
                    continue # already processed message
                else: 
                    # process message 
                    if single_msg['message_type'] == HELLO_MESSAGE: 
                        self.hello_message_handler.processMessage(single_msg)
                    elif single_msg['message_type'] == TC_MESSAGE:
                        pass #todo
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
                        pass #todo
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
            with socket(AF_INET, SOCK_DGRAM) as sock:
                sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
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
                                        }
                    [message_header, message])
                message_offset += (MSG_HEADER_SIZE + message_size)
                
            return packet_seq_num, message_contents                
            
    class helloMessage(threading.Thread):
        '''
        hello message handler
        message type : hello message
        TTL : 1
        VTime set by NEIGHB_HOLD_TIME
        generated based on link set, neighbor set, MPR set 
        '''
        def __init__(self) -> None:
            super().__init__()
            self.last_emission_time = 0
            
        def run(self):
            if self.last_emission_time - time.time() > HELLO_INTERVAL:
                pass # broadcast
                
        def cal_Htime_tobit(self):
            pass
        
        def cal_Htime_todigit(self):
            pass
        
        def packMessage(self, linkSet : LinkSet, neighborSet : NeighborSet, MPRSet : MPRSet):
            packet_format = '!HBB'
            packed_data = struct.pack(packet_format,
                                      RESERVED,             # 0, 16bits
                                      NEIGHB_HOLD_TIME,     # Htime 8bits #todo mentissa
                                      WILL_DEFAULT)         # willingness default 8bits
            packet_format = '!BBHI'
            for single_tuple in linkSet.getTuple():
                link_code = 0
                if MPRSet.checkExist(single_tuple._l_neighbor_iface_addr):
                    link_code = MPR_NEIGH
                else:
                    link_code = neighborSet.checkExist(single_tuple._l_neighbor_iface_addr)
                link_code = (link_code<<2) + single_tuple.getLinkType()
                link_message_size = 32*3
                packed_data += struct.pack(packet_format,
                                           link_code,
                                           RESERVED,
                                           link_message_size,
                                           single_tuple._l_neighbor_iface_addr
                                           )
                
            return packed_data
        
        def unpackMessage(self, packed_data):
            size = struct.calcsize(packed_data)
            _, Htime, will_value = map(struct.unpack_from('!HBB',packed_data, offset=0))
            unpacked_data = [_ for _ in range((size-4)/4)]
            for i in range((size-4)/4):
                unpacked_data[i] = struct.unpack_from('!BBHI', packed_data, offset=4+i*4)
                
            return Htime, will_value, unpacked_data

        def processMessage(self):
            pass
        
        def forwardMessage(self):
            pass
        
    class TCMessage:
        def __init__(self) -> None:
            pass
        def packMessage(self):
            pass
        def unpackMessage(self):
            pass
        def processMessage(self):
            pass
        def forwardMessage(self):
            pass
        
        
    # interfaceAss = InterfaceAssociation()
    LinkSetTuple = LinkSet()
    neighborTuple = NeighborSet()
    # twoneighborTuple = TwoHopNeighborSet()
    mprTuple = MPRSet()
    # mprSelector = MPRSelectorSet()
    # topolodyTuple = TopologyInfo()
    hello = helloMessage()
    hello.packMessage(LinkSetTuple, neighborTuple, mprTuple)
        
            
    
        
    #- HELLO-messages, performing the task of link sensing, neighbor detection and MPR signaling,
    # - TC-messages, performing the task of topology declaration (advertisement of link states).
    
    
