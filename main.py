'''
OLSR ad hoc routing protocol 
RFC 3236
only for single network interface

+ move message and reclacMessage
'''

from informationRepo import * 
from constants import *
from packetManager import *
from olsr_logger import *

if __name__ == '__main__':     
    manager = OLSRManager()
    
    # move message, reCalcmessage 다시보기
    # 라우팅 테이블 따라 경로 설정되는거 -> 네트워크 계층에서 설정하기
    # 보내는 메세지 잡아서 라우팅 테이블 따라서 보내기
    # subnet - multi interface - 
    # 어떠한 노드를 default node, 즉 인터넷에 접속을 제공하는 노드라고 설정하면
    # 기본적으로 외부와의 통신을 위해 해당 노드를 거치게 됨
    # 해당 노드에서는 망 외부에서 들어오는 메세지와 망 내부에서 외부로 나가는 메세지를 
    # 변역? 
    # 메세지 만료 핸들러 동작