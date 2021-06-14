import struct
import requests
import urllib
import bencode
import time
import logging
from classes.Communication import Communication
from classes.Peer import Peer
from threading import Thread


logger = logging.getLogger('TRACKER')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('\033[91m%(name)s:%(levelname)s - [%(asctime)s]  - %(message)s \033[0m'))
logger.addHandler(ch)


class Tracker(Thread):
    def __init__(self, manager):
        super(Tracker, self).__init__()
        self.setDaemon(True)  # Exit the thread when program ends
        self.interval = 90
        self.manager = manager

    def run(self):
        while True:
            tracker_url, options = self.manager.get_tracker_url()

            logger.debug(f"{Communication.TRACKER_REQUEST}")
            req = requests.get(tracker_url, urllib.parse.urlencode(options))
            response = bencode.decode(req.content)

            # Process response
            if 'failure reason' in response or 'peers' not in response:
                logger.debug(response)
                continue

            if 'interval' in response:
                self.interval = 90 or response['interval']
                logger.debug(f"{Communication.TRACKER_INTERVAL} {self.interval}")

            # Go through peers
            self.manager.peers_dictionary_lock.acquire()
            logger.debug(self.manager.peers_dictionary.keys())
            for i in range(0, len(response['peers']), 6):
                peer = struct.unpack("!BBBBH", response['peers'][i:i + 6])
                peer_ip = '.'.join(map(str, peer[:4]))
                peer_port = peer[-1]
                peer_identification = f"{peer_ip}:{peer_port}"
                if peer_identification not in self.manager.peers_dictionary:
                    remote_peer = Peer(peer_ip, peer_port,
                                       self.manager.peers_to_manager_queue,
                                       self.manager.me_peer_id,
                                       self.manager.torrent)
                    self.manager.peers_dictionary[peer_identification] = remote_peer

                    logger.debug(f"{Communication.TRACKER_NEW_PEER} {remote_peer.__repr__()}")
                    remote_peer.state_machine.start()

            logger.debug(self.manager.peers_dictionary.keys())
            self.manager.peers_dictionary_lock.release()
            time.sleep(self.interval)
