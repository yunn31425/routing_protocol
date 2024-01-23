import struct
from constants import *
import subprocess
import sys
import socket
import fcntl
import asyncio
import threading
from scapy.all import sniff, Raw, TCP, UDP, IP
from multiprocessing import Process, Manager, Queue

from message import *
from informationRepo import *
from numba import jit
from olsr_logger import *

class Sender:
    '''
    todo 소켓 리셋 sender에 넣기 -> broadcaste r가 아니라 
    별도의 queue 꾸릴 것
    '''
    '''
    send message and packets
    '''
    def __init__(self, parent) -> None:
        self.parent = parent
        self.logger = parent.logger
        try:
            self.interface_name = sys.argv[1]
        except IndexError:
            print("interface name must be entered... (e.g wlp1s0)")
            sys.exit()
        # if len(sys.argv) == 1:e
        #     print("enter network interface name")
        #     sys.exit()        
        # # check if network mode is ad-hoc not managed
        # if (subprocess.run('iwconfig | grep Mode', shell=True, capture_output=True, text=True).stdout).split(' ')[10] == "Mode:Managed":
        #     print("change mode into ad-hoc first")
        #     sys.exit()
            
        try:
            SendSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            SendSocket.bind(('', PORTNUM_SEND))
            SendSocket.listen()
            listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listenSocket.bind(('', PORTNUM_RECV))
            listenSocket.listen()
            
            interface_info = fcntl.ioctl(listenSocket.fileno(), 0x8915, struct.pack('255s', bytes((self.interface_name), 'utf-8')))
            self.ip_address = socket.inet_ntoa(struct.unpack('4s', interface_info[20:24])[0])

        except OSError as e:
            if e.errno == 19:
                print("wrong interface name")
                self.logger.error(f'wrong interface name :{self.interface_name}')
                listenSocket.close()
                SendSocket.close()
                sys.exit()
                
            elif e.errno == 98:
                print("port is already in use")
                listenSocket.close()
                SendSocket.close()
                sys.exit()
                
        print("init complete")
        self.logger.info(f'init complete. addr : {self.ip_address}')
                    
    def sendMsg(single_mssage, dest_addr):
        '''
        send message, especially for forwarding
        '''
        with socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW) as sock:
            sock.sendto(single_mssage, (dest_addr, 0))
    
    def broadcastMsg(self, packed_message):
        with socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packed_message, (BROADCAST_ADDR, 14567))

    def getIfaceName(self):
        return self.interface_name
    
    def getIPAddr(self):
        return self.ip_address
        
class OLSRManager:
    '''
    send and receive olsr message to maintain route
    and make route table
    '''
    def __init__(self, parent) -> None:
        
        self.parent = parent
        self.logger = parent.logger
        self.sender = parent.sender
        self.ip_address = self.sender.getIPAddr()
        
        self.mprSet = MPRSet()
        self.neighbor_set = NeighborSet()
        self.link_set = LinkSet()
        self.two_hop_neighbor_set = TwoHopNeighborSet()
        self.duplicated_set = DuplicatedSet()
        self.mprSelector_set = MPRSelectorSet()
        self.topology_set  = TopologyInfo()
        self.route_table = RouteTable()        
        
        self.hello_message_handler = helloMessage(self, parent.getIPAddr())    
        self.packet_header_handler = PacketHeader(parent.getIPAddr())
        self.tc_message_handler = TCMessage(self) 
        self.move_message_handler = MoveMessage()
        self.recalc_message_handler = RecalcMesage()
        
    def packet_processing(self, packet):
        if len(packet['payload']) == PACKET_HEADER_SIZE + MSG_HEADER_SIZE:
            return
        ##print('---', packet['payload'])
        seq_num, message_contents = self.packet_header_handler.detatchHeader(packet['payload'])
        source_addr = packet['src_IP']
        dest_addr = packet['dst_IP']
        for single_msg in message_contents:
            if single_msg['ttl'] < 2: # need to be checked
                print("no processing")
                continue 
            
            #message processing
            if self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], single_msg['message_seq_num']) != -1:
                print("already processed message")
                continue # already processed message
            # process message 
            elif single_msg['message_type'] == HELLO_MESSAGE:
                print("hello message")
                self.logger.debug('hello message from : ' + source_addr)
                self.hello_message_handler.processMessage(single_msg, source_addr)
            elif single_msg['message_type'] == TC_MESSAGE:
                self.tc_message_handler.processMessage(single_msg, source_addr)
            elif single_msg['message_type'] == MID_MESSAGE:
                pass # not yet to deal with it
            elif single_msg['message_type'] == HNA_MESSAGE:
                pass # not yet to deal with it
            elif single_msg['message_type'] == MOVE_MESSAGE:
                # todo 이동 메세지 프로세싱
                pass
            elif single_msg['message_type'] == RECALC_MESSAGE:
                # 경로 변경 메세지 프로세싱
                pass
            else:
                print('unidenfitied message type')
                self.logger.warning('unidenfitied message type : ', single_msg['message_type'])
                
            # message  forwarding # need to be check
            if self.duplicated_set.checkExist_iface(self.ip_address) and self.duplicated_set.checkExist_iface(dest_addr):
                continue # message which has been forwarded 
            elif single_msg['message_type'] == HELLO_MESSAGE: 
                self.hello_message_handler.forwardMessage(single_msg)
            elif single_msg['message_type'] == TC_MESSAGE:
                self.defaultForward(single_msg, source_addr, dest_addr)
            elif single_msg['message_type'] == MID_MESSAGE:
                pass # not yet to deal with it
            elif single_msg['message_type'] == HNA_MESSAGE:
                pass # not yet to deal with it
            elif single_msg['message_type'] == MOVE_MESSAGE:
                # todo 이동 메세지 포워딩
                pass
            elif single_msg['message_type'] == RECALC_MESSAGE:
                # 경로 변경 메세지 포워딩
                pass
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
                    self.parent.sender.sendMsg(single_msg, dest_addr)
                else:
                    return
            else:
                self.parent.sender.sendMsg(single_msg, dest_addr)
            
        # further process for forwarding
        will_retransmit = False
        if self.mprSet.checkExist(source_addr) and single_msg['ttl'] > 1:
            will_retransmit = True
        ptr = self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], single_msg['message_seq_num'])
        
        if ptr != -1:
            print("exist", ptr)
            self.duplicated_set.updateTuple(ptr, time.time() + DUP_HOLD_TIME, dest_addr, will_retransmit)
        else:
            print("non exist", ptr)
            self.duplicated_set.addTuple(single_msg['originator_add'], single_msg['message_seq_num'], will_retransmit,\
                dest_addr, time.time() + DUP_HOLD_TIME)
            
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
        pass # todo : sender로
    


class packetForwarder:
    '''
    read packet and forward packet
    '''
    def __init__(self):
        super().__init__()
        
        self.packet_queue = Queue()
        self.transmit_queue = Queue()           
        
        self.logger = OlSRLogger()
        self.sender = Sender(self)
        self.manager = OLSRManager(self)
        
        
        self.interface_name = self.sender.getIfaceName()
        self.ip_address = self.sender.getIPAddr()
        
        self.enqueue_process = Process(target=self.enqueue)
        self.enqueue_process.start() 
        
        self.dequeue_process = Process(target=self.dequeue)
        self.dequeue_process.start()
               
        self.transmit_process = Process(target=self.transmit)    
        self.transmit_process.start()
        
        self.dequeue_process.join()
        self.enqueue_process.join()
        self.transmit_process.join()
        
    def getIfaceName(self):
        return self.sender.getIfaceName()
    
    def getIPAddr(self):
        return self.sender.getIPAddr()
        
    def enqueuing(self, packet):
        if Raw in packet:
            print(packet[Raw].load)
            if TCP in packet:        
                self.packet_queue.put({
                    'payload' : packet[Raw].load,
                    'src_IP' : packet[IP].src,
                    'dst_IP' : packet[IP].dst,
                    'src_port' : packet[TCP].sport,
                    'dst_port' : packet[TCP].dport,
                    })
            elif UDP in packet:
                self.packet_queue.put({
                    'payload' : packet[Raw].load,
                    'src_IP' : packet[IP].src,
                    'dst_IP' : packet[IP].dst,
                    'src_port' : packet[UDP].sport,
                    'dst_port' : packet[UDP].dport,
                    })
            else:
                self.logger.warning(f'packet with out TCP or UDP')
                return
        else:
            self.logger.warning(f'packet with out Raw')
            return
        
        ##print(packet.summary(), 'dequeing', self.packet_queue.qsize())
            
    async def async_sniff(self):
        sniff(iface=self.interface_name, store=False, prn=self.enqueuing)
        
    def enqueue(self):
        asyncio.run(self.async_sniff())
        
    def dequeue(self):
        try:            
            while True:
                if not self.packet_queue.empty():                
                    single_packet = self.packet_queue.get()
                    print(single_packet['src_IP'], '>>' ,single_packet['dst_IP'], 'dequeing')
                    if single_packet['dst_port'] == 14568:
                        ##print('---', single_packet['payload'])
                        self.manager.packet_processing(single_packet)
                    else:
                        self.packet_processing(single_packet)
        except KeyboardInterrupt:
            print("keyboard interrupt")
            self.logger.info('keyboard interrupt')
            sys.exit()
        
    def packet_processing(self, single_packet):
        '''
        if src_port and dst_port is all olsr port, process it
        else forward according to routing table
        '''     
        
    def transmit(self):
        pass
            
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
        packet_length = struct.unpack_from('!H', binary_packet, 0)[0]
        packet_seq_num = struct.unpack_from('!H', binary_packet, 2)[0]
        message_contents = []
        message_offset = 4
        if packet_length == 4:
            return 
        while packet_length - message_offset > 0:
            message_header = struct.unpack_from('!BBHIBBH', binary_packet, offset=message_offset)
            message_size = message_header[-1]
            message = binary_packet[message_offset + MSG_HEADER_SIZE : message_offset + MSG_HEADER_SIZE + message_size]
            #message = struct.unpack_from(f'I{message_size}', binary_packet, message_offset + MSG_HEADER_SIZE)
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


if __name__ == '__main__':
    '''
    test code for package
    '''
    
    # step1
    packet_forwarder = packetForwarder()
    
    # step2