import socket


class Communication:
    PEER_STATE = "PEER_STATE"
    PEER_STATE_INIT = 'PEER_STATE_INIT'
    PEER_STATE_CONNECT = 'PEER_STATE_CONNECT'
    PEER_STATE_READY_DOWNLOAD = 'PEER_STATE_READY_DOWNLOAD'

    PEER_INSTRUCTION = "PEER_INSTRUCTION"
    PEER_DISCONNECT = "PEER_DISCONNECT"
    PEER_CHOKED = "PEER_CHOKED"
    PEER_UNCHOKED = "PEER_UNCHOKED"
    PEER_READY_DOWNLOAD = "PEER_READY_DOWNLOAD"
    PEER_DOWNLOAD_DONE = "PEER_DOWNLOAD_DONE"
    PEER_DOWNLOAD_ERROR = "PEER_DOWNLOAD_ERROR"

    PEER_EXT_MESSAGE = "PEER_EXTENDED_MESSAGE"
    PEER_BITFIELD = "PEER_BITFIELD"
    PEER_PIECE = "PEER_PIECE"
    PEER_HAVE = "PEER_HAVE"

    MANAGER_INSTRUCTION = "MANAGER_INSTRUCTION"
    MANAGER_STOP = "MANAGER_STOP"
    MANAGER_WAIT = "MANAGER_WAIT"
    MANAGER_DOWNLOAD_REQUEST = "MANAGER_DOWNLOAD_REQUEST"

    TRACKER_REQUEST = "TRACKER_REQUEST"
    TRACKER_INTERVAL = "TRACKER_INTERVAL"
    TRACKER_NEW_PEER = "TRACKER_NEW_PEER"

    PROTOCOL_KEEP_ALIVE = 0
    PROTOCOL_EXTENDED = 20
    PROTOCOL_EXT_HANDSHAKE = 0
    PROTOCOL_BITFIELD = 5
    PROTOCOL_HAVE = 4
    PROTOCOL_CHOKED = 0
    PROTOCOL_UNCHOKED = 1
    PROTOCOL_INTERESTED = 2
    PROTOCOL_NOT_INTERESTED = 3
    PROTOCOL_REQUEST = 6
    PROTOCOL_PIECE = 7





def read_n_bytes(soc, n, timeout=None):

    n_to_read = n
    nb_empty_msg = 0
    raw = bytes()
    default_t = soc.gettimeout()

    if timeout is not None:
        soc.settimeout(timeout)

    while n_to_read > 0:
        try:
            msg_rcv = soc.recv(n_to_read)
            # print(f'--- {msg_rcv}')
            if len(msg_rcv) > 0:
                raw += msg_rcv
                n_to_read -= len(msg_rcv)
                nb_empty_msg = 0
            else:
                nb_empty_msg += 1
                if nb_empty_msg >= 3:
                    return None
        except socket.error as er:
            return None

    soc.settimeout(default_t)
    return raw


def send_n_bytes(soc, message):
    output = False
    lm = len(message)
    try:
        n = soc.send(message)
        if n == lm:
            output = True
    except socket.error as er:
        output = False
    return output
