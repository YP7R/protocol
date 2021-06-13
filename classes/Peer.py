import socket
import hashlib
import queue
import bencode
import logging
import struct
import time
from bitarray import bitarray
from threading import Lock, Thread
from classes.Communication import Communication, send_n_bytes, read_n_bytes

logger = logging.getLogger('PEER')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('\033[94m%(name)s:%(levelname)s - [%(asctime)s]  - %(message)s \033[0m'))
logger.addHandler(ch)


class Peer:
    def __init__(self, ip_address, port, peer_to_manager_queue, me_peer_id, info_hash, sha1_pieces, piece_length):
        # Peer information
        self.remote_ip_address = ip_address
        self.remote_port = port
        self.peer_id = me_peer_id
        self.info_hash = info_hash
        self.sha1_pieces = sha1_pieces
        self.piece_length = piece_length

        # Peer information
        self.remote_handshake = None
        self.remote_extended_protocol = None
        self.remote_bitfield = None

        self.remote_interested = False
        self.remote_unchoked = False
        self.am_unchoked = False
        self.am_interested = False

        self.keep_alive = 0

        # Communication this peer to manager
        self.peer_to_manager_queue = peer_to_manager_queue
        self.peer_to_manager_lock = Lock()
        self.peer_to_manager_events = []

        # Communication manager to this peer
        self.manager_to_peer_queue = queue.Queue()
        self.manager_to_peer_lock = Lock()
        self.manager_to_peer_events = []

        # Currently downloading
        self.current_bytes_to_download = None
        self.current_no_piece = None
        self.current_offset = None
        self.current_piece = None

        # P2P
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.settimeout(2)

        self.state = ""  # Communication.PEER_STATE_INIT
        self.state_machine = Thread(target=self.state_machine_run)

        self.last_message = ""

    def __repr__(self):
        return f"{self.remote_ip_address}:{self.remote_port}"

    def add_peer_event(self, message):
        self.peer_to_manager_lock.acquire()
        self.peer_to_manager_events.append(message)
        self.peer_to_manager_lock.release()

    def notify_manager(self):
        self.peer_to_manager_queue.put(self.__repr__())

    def connect(self):
        try:
            self.soc.connect((self.remote_ip_address, self.remote_port))
            return True
        except socket.error as er:
            return False

    def send_handshake(self):
        protocol_str = 'BitTorrent protocol'
        message = struct.pack('!B19s8s20s20s',
                              len(protocol_str),
                              protocol_str.encode(),
                              '00000000'.encode(),
                              self.info_hash,
                              self.peer_id)

        output = send_n_bytes(self.soc, message)
        return output

    def check_handshake(self):
        condition_protocol_len = self.remote_handshake[0] == 19
        condition_protocol_str = self.remote_handshake[1].decode() == 'BitTorrent protocol'
        condition_info_hash = self.remote_handshake[3] == self.info_hash
        if condition_protocol_len and condition_protocol_str and condition_info_hash:
            return True
        else:
            return False

    def receive_handshake(self):
        len_handshake = 68
        message = read_n_bytes(self.soc, len_handshake)
        if message is None:
            return False

        remote_handshake = struct.unpack('!B19s8s20s20s', message)
        self.remote_handshake = remote_handshake
        if self.check_handshake():
            return True
        return False

    def send_interested_unchoked(self):
        message_interested = struct.pack('!IB', 1, 2)
        message_unchoked = struct.pack('!IB', 1, 1)
        i = send_n_bytes(self.soc, message_interested)
        u = send_n_bytes(self.soc, message_unchoked)
        return i and u

    def send_request(self, no_piece, offset, length):
        len_request = 13
        message = struct.pack('!IBIII', len_request, Communication.PROTOCOL_REQUEST, no_piece, offset, length)
        output = send_n_bytes(self.soc, message)
        return output

    def state_machine_run(self):
        self.state = Communication.PEER_STATE_INIT
        logger.debug(f"{self.state} {self.__repr__()}")

        # Peer connection
        output = self.connect()
        if not output:
            self.last_message = "Tentative de connexion"
            self.add_peer_event(Communication.PEER_DISCONNECT)
            self.notify_manager()
            logger.debug(f"{Communication.PEER_DISCONNECT} {self.__repr__()}")
            return

        # Peer handshake
        output = self.send_handshake()
        if not output:
            self.last_message = "Envoi du handshake"
            self.add_peer_event(Communication.PEER_DISCONNECT)
            self.notify_manager()
            logger.debug(f"{Communication.PEER_DISCONNECT} {self.__repr__()}")
            return

        # Receive handshake and check it
        output = self.receive_handshake()
        if not output:
            self.last_message = 'Reception du handshake'
            self.add_peer_event(Communication.PEER_DISCONNECT)
            self.notify_manager()
            logger.debug(f"{Communication.PEER_DISCONNECT} {self.__repr__()}")

            return

        # Send interested
        output = self.send_interested_unchoked()
        if not output:
            self.last_message = 'Envoie du Interested unchoked'
            self.add_peer_event(Communication.PEER_DISCONNECT)
            self.notify_manager()
            logger.debug(f"{Communication.PEER_DISCONNECT} {self.__repr__()}")
            return

        self.state = Communication.PEER_STATE_CONNECT
        logger.debug(f"{self.state} {self.__repr__()}")

        while self.state == Communication.PEER_STATE_CONNECT:
            output = self.process_message()
            if not output or output == Communication.PEER_CHOKED:
                self.add_peer_event(Communication.PEER_DISCONNECT)
                self.notify_manager()
                logger.debug(f"{Communication.PEER_DISCONNECT} {self.__repr__()}")
                return

            if output == Communication.PEER_UNCHOKED:
                self.state = Communication.PEER_STATE_READY_DOWNLOAD
                logger.debug(f"{self.state} {self.__repr__()}")

        while self.state == Communication.PEER_STATE_READY_DOWNLOAD:
            self.add_peer_event(Communication.PEER_READY_DOWNLOAD)
            self.notify_manager()

            instruction = self.manager_to_peer_queue.get()
            logger.debug(f"{instruction} {self.__repr__()} ")

            if instruction == Communication.MANAGER_STOP:
                self.add_peer_event(Communication.PEER_DISCONNECT)
                self.notify_manager()
                logger.debug(f"{Communication.PEER_DISCONNECT} {self.__repr__()}")
                return


            elif instruction == Communication.MANAGER_WAIT:
                time.sleep(2)

            elif instruction.startswith(Communication.MANAGER_DOWNLOAD_REQUEST):
                instr, no_piece = instruction.split(":")
                # loggder.debug(instruction)
                self.current_bytes_to_download = self.piece_length
                self.current_no_piece = int(no_piece)
                self.current_offset = 0
                self.current_piece = b''

                while self.current_bytes_to_download > 0:
                    size_to_read = 2 ** 15 if self.current_bytes_to_download // (
                            2 ** 15) >= 1 else self.current_bytes_to_download
                    output = self.send_request(self.current_no_piece, self.current_offset, size_to_read)
                    if not output:
                        self.add_peer_event(Communication.PEER_DOWNLOAD_ERROR)
                        self.notify_manager()
                        # logger.debug(f'Il y a eu une erreur,  laquelle ?{output} {self.last_message}')
                        return

                    output = self.process_message()
                    if not output or output == Communication.PEER_CHOKED:
                        # logger.debug(f'Il y a eu une erreur,  laquelle ?{output} {self.last_message}')

                        self.add_peer_event(Communication.PEER_DOWNLOAD_ERROR)
                        self.notify_manager()
                        return

                sha1_piece = hashlib.sha1(self.current_piece).digest()
                verified_sha1_piece = self.sha1_pieces[self.current_no_piece]

                if sha1_piece == verified_sha1_piece:
                    with open(f'./pieces/piece_{self.current_no_piece}.part', 'w+b') as fp:
                        fp.write(self.current_piece)
                        fp.close()
                    self.add_peer_event(Communication.PEER_DOWNLOAD_DONE)
                    self.notify_manager()
                else:
                    self.add_peer_event(Communication.PEER_DOWNLOAD_ERROR)
                    self.notify_manager()
                    return

    def process_message(self):
        output = False

        # Read len-prefix
        raw = read_n_bytes(self.soc, 4, timeout=None)
        if raw is None:
            self.last_message = 'Lecture de len_prefix'
            return output

        # Length prefix
        len_prefix = struct.unpack('!I', raw)[0]
        if len_prefix == Communication.PROTOCOL_KEEP_ALIVE:
            self.last_message = 'Reception d\'un keep alive'
            return not Communication.PROTOCOL_KEEP_ALIVE

        # Raw data
        raw_data = read_n_bytes(self.soc, len_prefix)
        if raw_data is None:
            self.last_message = 'Lecture de raw_data'
            return output

        # Message ID
        message_id = struct.unpack('!B', raw_data[0:1])[0]

        if message_id == Communication.PROTOCOL_EXTENDED:
            extended_message = struct.unpack('!B', raw_data[1:2])[0]

            if extended_message == Communication.PROTOCOL_EXT_HANDSHAKE:  # extended handshake
                extended_payload = raw_data[2:]
                extended_protocol = bencode.decode(extended_payload)
                self.remote_extended_protocol = extended_protocol
                self.last_message = 'Reception d\' un message extended'
                return Communication.PEER_EXT_MESSAGE
            else:
                '''#todo : extended message instruction'''
                self.last_message = 'Reception d\' un message extended'
                return Communication.PEER_EXT_MESSAGE

        elif message_id == Communication.PROTOCOL_BITFIELD:
            # TODO: Longueur du bitfield doit être égale au nombre de sha1 len(pieces_sha1)
            # len(bitfield)*8 == self.infos['nb_piecess_sha1']
            bitfield = raw_data[1:]
            remote_bitfield = bitarray(endian='big')
            remote_bitfield.frombytes(bitfield)
            self.remote_bitfield = remote_bitfield
            self.last_message = 'Reception du bitfield'
            return Communication.PEER_BITFIELD

        elif message_id == Communication.PROTOCOL_HAVE:
            piece_index = struct.unpack('!I', raw_data[1:])[0]
            self.remote_bitfield[piece_index] = True
            self.last_message = 'Reception d\'un have'
            return Communication.PEER_HAVE

        elif message_id == Communication.PROTOCOL_UNCHOKED:
            self.remote_unchoked = True
            self.last_message = 'Reception de unchoked'
            return Communication.PEER_UNCHOKED

        elif message_id == Communication.PROTOCOL_CHOKED:
            self.last_message = 'Reception de choked'
            self.remote_unchoked = False
            return Communication.PEER_CHOKED

        elif message_id == Communication.PROTOCOL_PIECE:
            no_piece, offset = struct.unpack('!II', raw_data[1:9])
            if no_piece == self.current_no_piece and offset == self.current_offset:
                self.current_piece += raw_data[9:]
                self.current_offset += 2 ** 15
                self.current_bytes_to_download -= 2 ** 15
                self.last_message = 'Reception d\'une piece'

                return Communication.PEER_PIECE
            else:
                self.last_message = 'Erreur sur la reception d\'une piece'
                return output
        else:
            # logger.debug(f'AUTRES ::: {self.__repr__()} {message_id}')
            return output
