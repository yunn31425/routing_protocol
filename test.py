import scapy.all as scapy
import threading
import queue

# 큐 생성
packet_queue = queue.Queue()

# 패킷 처리를 위한 함수
def process_packet(packet):
    # 여기에 패킷을 가로채서 원하는 처리를 수행하는 코드 추가
    # 예를 들어, 패킷 정보 출력
    print(packet.summary())

    # 처리 결과를 큐에 저장
    packet_queue.put(packet)

# 패킷 스니핑을 위한 함수
def sniff_packets(interface):
    scapy.sniff(iface=interface, store=False, prn=process_packet)

# 사용 예제
if __name__ == "__main__":
    # 네트워크 인터페이스 설정 (필요에 따라 변경)
    network_interface = "wlp1s0"

    # 스니핑을 위한 스레드 생성
    sniffer_thread = threading.Thread(target=sniff_packets, args=(network_interface,), daemon=True)

    # 스레드 시작
    sniffer_thread.start()

    try:
        while True:
            # 큐에서 패킷 가져오기 (블로킹됨)
            received_packet = packet_queue.get()
            
            # 이후 원하는 처리 수행
            # ...

    except KeyboardInterrupt:
        # Ctrl+C로 프로그램 종료 시 스레드 종료
        sniffer_thread.join()
        print("Sniffer thread stopped.")
