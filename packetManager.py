import struct
from constants import *
import subprocess
import sys
import socket
import fcntl
import asyncio
import threading
from scapy.all import sniff, IP, Raw
from multiprocessing import Process, Manager, Queue

from message import *
from informationRepo import *
from numba import jit

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

class Sender:
    '''
    todo 소켓 리셋 sender에 넣기 -> broadcaste r가 아니라
    '''
    def __init__(self, debug=False) -> None:
        self.stauts = False
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
                listenSocket.close()
                SendSocket.close()
                sys.exit()
                
            elif e.errno == 98:
                print("port is already in use")
                listenSocket.close()
                SendSocket.close()
                sys.exit()
                
        print("init complete")
                
    def sendMessage():
        pass
    
    def broadcastMsg():
        pass
    
    def getIfaceName(self):
        return self.interface_name
    
    def getIPAddr(self):
        return self.ip_address
        
class OLSRManager:
    def __init__(self) -> None:
        pass        

class packetForwarder:
    '''
    read packet and forward packet
    '''
    def __init__(self):
        super().__init__()

        self.mprSet = MPRSet()
        self.neighbor_set = NeighborSet()
        self.link_set = LinkSet()
        self.two_hop_neighbor_set = TwoHopNeighborSet()
        self.duplicated_set = DuplicatedSet()
        self.mprSelector_set = MPRSelectorSet()
        self.topology_set  = TopologyInfo()
        self.route_table = RouteTable()
        
        self.packet_queue = Queue()
        self.transmit_queue = Queue()
                
        self.sender = Sender()
        
        self.interface_name = self.sender.getIfaceName()
        self.ip_address = self.sender.getIPAddr()
             
        self.hello_message_handler = helloMessage(self, self.ip_address)    
        self.packet_header_handler = PacketHeader(self.ip_address)
        self.tc_message_handler = TCMessage(self)
        
        self.enqueue_process = Process(target=self.enqueue)
        self.enqueue_process.start() 
        
        self.dequeue_process = Process(target=self.dequeue)
        self.dequeue_process.start()
               
        self.transmit_process = Process(target=self.transmit)    
        self.transmit_process.start()
        
        self.dequeue_process.join()
        self.enqueue_process.join()
        self.transmit_process.join()
        
    def enqueuing(self, packet):
        ilayer = packet.getlayer("IP")
        if packet.getlayer("Raw"):            
            #print('hehe', packet[Raw].load)
            self.packet_queue.put({
                'payload' : packet[Raw].load,
                'src_IP' : ilayer.src,
                'dst_IP' : ilayer.dst
                })
            #print(packet.summary(), 'dequeing', self.packet_queue.qsize())
            
    async def async_sniff(self):
        sniff(iface=self.interface_name, store=False, prn=self.enqueuing)
        
    def enqueue(self):
        asyncio.run(self.async_sniff())
        # while True:
        #     print(sniff(iface=self.interface_name, store=False,prn=self.enqueuing, timeout=None))
        
    def dequeue(self):
        while True:
            if not self.packet_queue.empty():                
                single_packet = self.packet_queue.get()
                print(single_packet['src_IP'], '>>',single_packet['dst_IP'], 'dequeing')
                self.packet_processing(single_packet)
        
    def packet_processing(self, packet):
        if len(packet['payload']) == PACKET_HEADER_SIZE + MSG_HEADER_SIZE:
            return
        seq_num, message_contents = self.packet_header_handler.detatchHeader(packet['payload'])
        source_addr = packet['src_IP']
        dest_addr = packet['dst_IP']
        for single_msg in message_contents:
            print(single_msg)
            if single_msg['ttl'] < 2: # need to be checked
                continue 
            if self.duplicated_set.checkExist_addr_seq(single_msg['originator_add'], single_msg['message_seq_num']):
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
    
    def broadcastMessage(self, packed_message):
        # todo : sender로 옮기기
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
        packet_length = struct.unpack_from('!H', binary_packet, 0)[0]
        packet_seq_num = struct.unpack_from('!H', binary_packet, 2)[0]
        message_contents = []
        message_offset = 4
        if packet_length == 4:
            return 
        while packet_length - message_offset > 0:
            print(binary_packet)
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