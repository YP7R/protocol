import queue
import os
import logging
from threading import Lock


class Manager:
    def __init__(self, torrent, me_peer_id):
        # Pieces
        self.piece_length = torrent.piece_length
        self.nb_pieces = len(torrent.pieces) // 20
        self.sha1_pieces = [torrent.pieces[i * 20:(i + 1) * 20] for i in range(self.nb_pieces)]
        self.pieces_to_download = [i for i in range(self.nb_pieces)]
        self.verified_pieces = []

        # Peers
        self.peers_dictionary = {}
        self.peers_dictionary_lock = Lock()
        self.peers_to_manager_queue = queue.Queue()

        # Information
        self.url_options = Lock()
        self.download = 0
        self.upload = 0
        self.left = self.nb_pieces * torrent.piece_length
        self.key = os.urandom(4)

        # My identification
        self.me_peer_id = me_peer_id

        # Others
        self.torrent = torrent

    def get_tracker_url(self):
        self.url_options.acquire()
        url_options = (self.torrent.announce,
                        {'info_hash': self.torrent.info_hash,
                         'peer_id': self.me_peer_id,
                         'port': 6881,
                         'numwant': 50,
                         'uploaded': self.upload,
                         'downloaded': self.download,
                         'left': self.left,
                         'key': self.key,
                         'compact': 1,
                         })
        self.url_options.release()
        return url_options
