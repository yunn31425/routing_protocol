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
  
        # check if network mode is ad-hoc not managed
        if (subprocess.run('iwconfig | grep Mode', shell=True, capture_output=True, text=True).stdout).split(' ')[10] == "Mode:Managed":
            print("change mode into ad-hoc first")
            
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
                self.logger.error("port is already in use")
                listenSocket.close()
                SendSocket.close()
                sys.exit()
                
        self.logger.info(f'Sender init complete. addr : {self.ip_address}')
                    
    async def sendMsg(self, single_mssage, dest_addr):
        '''
        send message, especially for forwarding
        '''
        try:
            with socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW) as sock:
                sock.sendto(single_mssage, (dest_addr, 14567))
        except OSError as e:
            self.logger.error(f'send failed : {e.errno}')
    
    async def broadcastMsg(self, packed_message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(packed_message, (BROADCAST_ADDR, 14567))
                self.logger.info('broadcast' + str(packed_message))
        except OSError as e:
            print(e.errno)
            self.logger.error(f'broadcast failed : {e.errno}')
            
    async def SendToMPR(self, packed_message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW) as sock:
                for dest_addr in self.parent.mprSelector_set.getMPRAddr():
                    sock.sendto(packed_message, (dest_addr, 14567))
        except OSError as e:
            self.logger.error(f'send failed : {e.errno}')

    def getIfaceName(self):
        return self.interface_name
    
    def getIPAddr(self):
        return self.ip_address

class PacketForwarder:
    '''
    read packet and forward packet
    '''
    def __init__(self, parent):
        
        self.olsr_manager = parent
        
        self.packet_queue = Queue()
        self.transmit_queue = Queue()
        self.broadcast_queue = Queue()      
        
        self.logger = self.olsr_manager.logger
        self.sender = Sender(self)
        
        self.interface_name = self.sender.getIfaceName()
        self.ip_address = self.sender.getIPAddr()
        
        self.enqueue_process = Process(target=self.enqueue)
        self.enqueue_process.start() 
        
        self.dequeue_process = Process(target=self.dequeue)
        self.dequeue_process.start()
            
        self.transmit_process = Process(target=self.transmit)    
        self.transmit_process.start()

        
    def getIfaceName(self):
        return self.sender.getIfaceName()
    
    def getIPAddr(self):
        return self.sender.getIPAddr()
        
    def enqueuing(self, packet):
        if Raw in packet:
            #print('packet enqueued', packet[Raw].load)
            self.logger.info('packet enqueued {packet[Raw].load}')
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
        
        # if queue size overflow, control willingness
        if self.packet_queue.qsize() > MAX_QUEUE_LENGTH:
            self.olsr_manager.hello_message_handler.willingness = WILL_NEVER
            self.logger.info("packet queue overflow, willingness -> WILL_NEVER")
            print("packet queue overflow, willingness -> WILL_NEVER")
        
        if self.olsr_manager.hello_message_handler.willingness == WILL_NEVER:
            if self.packet_queue.qsize() < MAX_QUEUE_LENGTH/1.2:
                self.olsr_manager.hello_message_handler.willingness == WILL_DEFAULT
                self.logger.info("packet queue overflow solved, willingness -> WILL_DEFAULT")
                print("packet queue overflow solved, willingness -> WILL_DEFAULT")
         
        ##print(packet.summary(), 'dequeing', self.packet_queue.qsize())
            
    async def async_sniff(self):
        sniff(iface=self.interface_name, store=False, prn=self.enqueuing)
        
    def enqueue(self):
        '''
        enqueuing received packet to queue before processing
        '''
        asyncio.run(self.async_sniff())
        
    def dequeue(self):
        '''
        dequeuing received packet to queue for processing
        '''
        try:            
            while True:
                if not self.packet_queue.empty():
                    print("packet dequeued")
                    single_packet = self.packet_queue.get()
                    print(single_packet['src_IP'], '>>' ,single_packet['dst_IP'], 'dequeing')
                    
                    if single_packet['src_IP'] == self.ip_address:
                        print("emited by this node")
                        self.default_packet_processing(single_packet)
                        # 라우팅 테이블에 따라 라우팅
                    elif single_packet['dst_IP'] in [self.ip_address,BROADCAST_ADDR]:
                        print("into this node")
                        if single_packet['dst_port'] == 14567:
                            print("olsr message")
                            self.olsr_manager.packet_processing(single_packet)
                        else:
                            print("default")
                            self.default_packet_processing(single_packet)
        except KeyboardInterrupt:
            print("keyboard interrupt")
            self.logger.info('keyboard interrupt')
            sys.exit()   
    
    def transmit(self):
        while True:
            if not self.transmit_queue.empty():
                self.transmit_single(self.transmit_queue.get())
                
    def transmit_single(self, single_message):
        single_packet = self.parent.attatchHeader(single_message)
        dest_ip = self.olsr_manager.route_table.getBridge()
        self.sender(single_packet) 
    
    def default_packet_processing(self, single_packet):
        next_addr = self.olsr_manager.route_table.getNextAddr(single_packet['dst_IP'])
        if next_addr:
            self.sender.sendMsg(single_packet['payload'], next_addr)
        else:
            self.olsr_manager.unreach_queue.putQueue(single_packet['dst_IP'], single_packet['payload'])
class PacketHeader:
    '''
    packet header for olsr protocol
    '''
    def __init__(self, this_node_ip) -> None:
        self.packet_seqence_num = 0
        self.node_ip = this_node_ip
        
    def encodeIPAddr(ip_addr : str):
        binary_addr = b''
        for digit in ip_addr.split('.'):
            binary_addr += struct.pack('!B', int(digit))
            
        return binary_addr

    def decodeIPAddr(ip_addr : int):
        tpl = struct.unpack('!BBBB', ip_addr)
        return str(tpl[0]) + '.' + str(tpl[1]) + '.' \
            + str(tpl[2]) + '.' + str(tpl[3])
                
    
    def attatchHeader(self, message_contents):
        packet_contents = b''
        packet_length = 0
        print(message_contents)
        if len(message_contents[4]) == 0:
            return
        
        message_size = len(message_contents[4])
            
        
        packet_contents += encodeIPAddr(self.node_ip)  # originator_address
        packet_contents += struct.pack("!BBH",
                                        message_contents[2],         # time to live
                                        0,                  # hop_count
                                        message_contents[3])         # message_seq_num
        packet_contents += message_contents[4]
        packet_length += message_size + 4*3
        packet_contents = struct.pack('!HHBBH', 
                                        packet_length,
                                        self.packet_seqence_num,
                                        message_contents[0],         # message_type
                                        message_contents[1],         # vtime
                                        message_size) + packet_contents

        self.packet_seqence_num += 1
        print(packet_contents)
        return packet_contents
            
    def detatchHeader(self, binary_packet):
        packet_length = struct.unpack_from('!H', binary_packet, 0)[0]
        packet_seq_num = struct.unpack_from('!H', binary_packet, 2)[0]
        message_contents = []
        message_offset = 4
        print('packet_length', packet_length)
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

        
class OLSRManager:
    '''
    send and receive olsr message to maintain route
    and make route table
    '''
    def __init__(self) -> None:
        
        self.logger = OlSRLogger()
        self.sender = Sender(self)
        self.ip_address = self.sender.getIPAddr()
        
        self.packet_header_handler = PacketHeader(self.ip_address)
        
        self.mprSet = MPRSet()
        self.neighbor_set = NeighborSet()
        self.link_set = LinkSet()
        self.two_hop_neighbor_set = TwoHopNeighborSet()
        self.duplicated_set = DuplicatedSet()
        self.mprSelector_set = MPRSelectorSet()
        self.topology_set  = TopologyInfo()
        self.reachable_set = ReachablitySet()
        self.route_table = RouteTable()        
        
        self.timeout_manager = TimeOutManager()
        self.timeout_manager.addRepository([self.link_set, self.two_hop_neighbor_set,
                                            self.mprSelector_set, self.topology_set,
                                            self.duplicated_set])
        self.timeout_manager.start()
        
        self.hello_message_handler = helloMessage(self, self.ip_address)    
        self.move_message_handler = MoveMessage(self)
        self.tc_message_handler = TCMessage(self) 
        
        self.unreach_queue = UnreachQueue(self)
            
        self.packet_forwarder = PacketForwarder(self)
        
        print("init complete")
        self.logger.info('init complete')
        
        self.tc_message_handler.start()
        self.hello_message_handler.start()
        
    def packet_processing(self, packet):
        if len(packet['payload']) == PACKET_HEADER_SIZE + MSG_HEADER_SIZE:
            print("header only")
            return
        print("payload", packet['payload'])
        seq_num, message_contents = self.packet_header_handler.detatchHeader(packet['payload'])
        source_addr = packet['src_IP']
        dest_addr = packet['dst_IP']
        print(message_contents)
        for single_msg in message_contents:
            if single_msg['ttl'] < 2: # need to be checked
                print("no processing")
                continue 
            
            #message processing
            if self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], single_msg['message_seq_num']) is not False:
                print("already processed message")
                pass # already processed message
            # process message 
            elif single_msg['message_type'] == HELLO_MESSAGE:
                print("hello message received")
                self.logger.debug('hello message from : ' + source_addr)
                self.hello_message_handler.processMessage(single_msg, source_addr)
            elif single_msg['message_type'] == TC_MESSAGE:
                self.tc_message_handler.processMessage(single_msg, source_addr)
            elif single_msg['message_type'] == MID_MESSAGE:
                pass # not yet to process it 
            elif single_msg['message_type'] == HNA_MESSAGE:
                pass # not yet to process it
            elif single_msg['message_type'] == MOVE_MESSAGE:
                self.move_message_handler.processMessage(single_msg, source_addr)
            else:
                print('unidenfitied message type')
                self.logger.warning('unidenfitied message type : ', single_msg['message_type'])
                
            # message  forwarding # need to be check
            idx = self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], single_msg['message_seq_num'])
            if (idx is not False) and (self.ip_address in self.duplicated_set.getIfaceLst(idx)):
                pass # message which has been forwarded already
            elif single_msg['message_type'] == HELLO_MESSAGE: 
                self.hello_message_handler.forwardMessage(single_msg)
            elif single_msg['message_type'] == TC_MESSAGE:
                self.defaultForward(single_msg, source_addr, dest_addr)
            elif single_msg['message_type'] == MID_MESSAGE:
                pass # not yet to forward it
            elif single_msg['message_type'] == HNA_MESSAGE:
                pass # not yet to forward it
            elif single_msg['message_type'] == MOVE_MESSAGE:
                self.move_message_handler.processMessage(single_msg)
            else: # default forwawding
                self.defaultForward(single_msg, source_addr, dest_addr)

    def defaultForward(self, single_msg, source_addr, dest_addr):
        if self.neighbor_set.checkExist(source_addr) != SYM:
            return
        else:
            if self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], \
                single_msg['message_seq_num'], True):
                if self.duplicated_set.checkExist_iface(dest_addr) is False:
                    pass # for further consideration
                else:
                    return
            else:
                pass # for further consideration
            
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
            self.packet_forwarder.transmit_queue.put(single_msg) # todo : 해결되도록!
            
if __name__ == '__main__':
    '''
    test code for package
    '''