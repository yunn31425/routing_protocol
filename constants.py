#message listening port
PORTNUM_SEND = 14567
PORTNUM_RECV = 14568

#define emission interval
HELLO_INTERVAL = 2
REFRESH_INTERVAL = 2
TC_INTERVAL = 2
MID_INTERVAL = TC_INTERVAL
HNA_INTERVAL = TC_INTERVAL

#define holding time 
NEIGHB_HOLD_TIME = REFRESH_INTERVAL*3
TOP_HOLD_TIME = 3*TC_INTERVAL
DUP_HOLD_TIME = 30
MID_HOLD_TIME = MID_INTERVAL*3
HNA_HOLD_TIME = HNA_INTERVAL*3

#hello message format
RESERVED = 0

# message willingness
WILL_NEVER = 0
WILL_LOW = 1
WILL_DEFAULT = 3
WILL_HIGH = 6
WILL_ALWAYS = 7

# message types
HELLO_MESSAGE = 1
TC_MESSAGE = 2
MID_MESSAGE = 3
HNA_MESSAGE = 4

MOVE_MESSAGE = 5
RECALC_MESSAGE = 6

#link types
UNSPEC_LINK = 0 # no specific information about the links
ASYM_LINK = 1   # links are asymmetric
SYM_LINK = 2    # links are symmetric
LOST_LINK = 3   # links have been lost

# Neighbor types
NOT_NEIGH = 0   # the neighbors have at least one symmetrical link with this node.
SYM_NEIGH = 1   # the neighbors have at least one symmetrical link AND have been selected as MPR by the sender
MPR_NEIGH = 2   # the nodes are either no longer or have not yet become symmetric neighbors

SYM = 0
NOT_SYM = 1

# constant size of headers
PACKET_HEADER_SIZE = 4*1
MSG_HEADER_SIZE = 4*3

MTU = 1500

TC_REDUNDANCY = 0
MPR_COVERAGE = 1
MAXJITTER = HELLO_INTERVAL/4

BROADCAST_ADDR = '192.168.1.255'

C = 0.0625

VELO_CHECK_PERIOD = 1

MOVE_VELO_THRESHOLD = 2

MAX_QUEUE_LENGTH = 1000


# MoveMessage status
MOVE_DEFAULT_STATE = 0
MOVE_MESSAGE_SENT_STATE = 1

# MoveMessage node type 
MOVE_MOVE_NODE = 1
MOVE_CLOSE_NODE = 2
MOVE_AWAY_NODE = 3
NODE_ROUTE_RECALC = 4

MOVE_INTERVAL = 0.5

NODE_RECALC_INTERVAL = 2

