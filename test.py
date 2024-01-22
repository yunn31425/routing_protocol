import socket
import struct
from time import *

def send_udp_packet(cnt, destination_ip, destination_port, message):
    # Create a UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Destination address (IP address, port)
    dest_address = (destination_ip, destination_port)

    try:
        # Send the UDP packet
        udp_socket.sendto(message.encode('utf-8'), dest_address)
        print(f"{cnt} UDP packet sent to {destination_ip}:{destination_port}: {message}")

    finally:
        # Close the socket
        udp_socket.close()

if __name__ == "__main__":
    # Specify the destination IP address and port
    dest_ip = "127.0.0.1"  # Change this to the appropriate destination IP
    dest_port = 1000  # Change this to the appropriate destination port

    # Specify the message to send in the UDP packet
    udp_message = "Hello, UDP!!"
    cnt = 0
        

    # Define the values for the first OLSR packet header
    packet_length_1 = 100
    packet_sequence_number_1 = 1
    message_type_1 = 2
    vtime_1 = 3
    message_size_1 = 20
    originator_address_1 = 0x11223344
    time_to_live_1 = 10
    hop_count_1 = 5
    message_sequence_number_1 = 100

    # Define the values for the second OLSR packet header
    packet_length_2 = 120
    packet_sequence_number_2 = 2
    message_type_2 = 1
    vtime_2 = 4
    message_size_2 = 25
    originator_address_2 = 0xAABBCCDD
    time_to_live_2 = 8
    hop_count_2 = 3
    message_sequence_number_2 = 200

    # Define the values for the second part of the OLSR packet header
    reserved_2 = 0
    htime_2 = 1
    willingness_2 = 2
    link_code_2 = 3
    reserved_2_2 = 0
    link_message_size_2 = 15
    neighbor_interface_address_2 = 0x44556677

    # Format the first OLSR packet header
    olsr_header_1 = struct.pack("!IIBBHIIIB", packet_length_1, packet_sequence_number_1,\
                                message_type_1, vtime_1, message_size_1, originator_address_1,\
                                time_to_live_1, hop_count_1, message_sequence_number_1)

    # Format the second OLSR packet header
    olsr_header_2 = struct.pack("!BBHBHBI", reserved_2, htime_2, willingness_2,\
                                link_code_2, reserved_2_2, link_message_size_2, neighbor_interface_address_2)

    # Combine the two headers
    combined_header = olsr_header_1 + olsr_header_2

    # Print the combined header in hexadecimal format
    print("Combined Header (Hex):", combined_header.hex())


    # Call the function to send the UDP packet
    while True:
        
        send_udp_packet(cnt, dest_ip, dest_port, combined_header.hex())
        cnt = (cnt+1)%2
        sleep(1)