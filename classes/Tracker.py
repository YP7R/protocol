from threading import Thread
import struct
import requests
import urllib
import bencode
import time


class Tracker(Thread):
    def __init__(self, manager):
        super(Tracker, self).__init__()
        self.setDaemon(False)  # Exit the thread when program ends
        self.manager = manager
        self.interval = 120

    def run(self):
        while True:
            tracker_url, options = self.manager.get_tracker_url()

            req = requests.get(tracker_url, urllib.parse.urlencode(options))
            response = bencode.decode(req.content)

            # Process response
            if 'failure reason' in response or 'peers' not in response:
                continue

            if 'interval' in response:
                self.interval = 120 or response['interval']

            # Go through peers
            self.manager.peers_dictionary_lock.acquire()
            for i in range(0, len(response['peers']), 6):
                peer = struct.unpack("!BBBBH", response['peers'][i:i + 6])
                peer_ip = '.'.join(map(str, peer[:4]))
                peer_port = peer[-1]
                peer_identification = f"{peer_ip}:{peer_port}"
                print(peer_identification)
                if peer_identification not in self.manager.peers_dictionary:
                    pass
                    # TODO ...
                    # remote_peer = Peer(peer_ip, peer_port,
                    #                   self.manager.peers_to_manager_queue,
                    #                  self.manager.[info_hash, peer_id, pieces])

                    # self.manager.peers_dictionary[peer_key] = remote_peer
                    # remote_peer.state_machine.start()
            self.manager.peers_dictionary_lock.release()

            time.sleep(self.interval)
