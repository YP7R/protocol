import os
import shutil
import logging
from classes.Torrent import Torrent
from classes.Tracker import Tracker
from classes.Manager import Manager
from classes.Communication import Communication

logger = logging.getLogger('MANAGER')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('\033[92m%(name)s:%(levelname)s - [%(asctime)s]  - %(message)s \033[0m'))
logger.addHandler(ch)

torrent_file = "./files/slackware64-14.2-install-dvd.torrent"
torrent_file = "./files/debian-10.3.0-amd64-netinst.iso.torrent"

# My identification
me_peer_id = os.urandom(20)

torrent = Torrent(torrent_file)

shutil.rmtree('./pieces', ignore_errors=True)
os.makedirs('./pieces')

manager = Manager(torrent, me_peer_id)
tracker = Tracker(manager)

tracker.start()

while True:
    id_peer = manager.peers_to_manager_queue.get()
    peer_to_delete = None

    manager.peers_dictionary_lock.acquire()
    manager.peers_dictionary[id_peer].peer_to_manager_lock.acquire()

    if Communication.PEER_DISCONNECT in manager.peers_dictionary[id_peer].peer_to_manager_events:
        logger.debug(f"{manager.peers_dictionary[id_peer].last_message} {id_peer}")
        peer_to_delete = id_peer

    else:
        if len(manager.peers_dictionary[id_peer].peer_to_manager_events) == 0:
            logger.debug(f"Why ...{id_peer}")

        message = manager.peers_dictionary[id_peer].peer_to_manager_events.pop(0)
        logger.debug(f'-- {id_peer} {message}')

        if message == Communication.PEER_READY_DOWNLOAD:

            # Check if we have all pieces downloaded
            if len(manager.verified_pieces) == manager.nb_pieces:
                manager.peers_dictionary[id_peer].manager_to_peer_queue.put(Communication.MANAGER_STOP)
                logger.debug(f"{Communication.MANAGER_STOP} {id_peer} ALL_PIECES_DOWNLOADED")

            # If there are pieces to download
            elif len(manager.verified_pieces) < manager.nb_pieces and len(
                    manager.pieces_to_download) > 0:

                piece_to_dl = -1
                for index_piece in manager.pieces_to_download:
                    if manager.peers_dictionary[id_peer].remote_bitfield[index_piece]:
                        piece_to_dl = index_piece
                        break

                if piece_to_dl != -1:
                    manager.pieces_to_download.remove(piece_to_dl)
                    manager.peers_dictionary[id_peer].manager_to_peer_queue.put(
                        f'{Communication.MANAGER_DOWNLOAD_REQUEST}:{piece_to_dl}')
                    logger.debug(f"{Communication.MANAGER_DOWNLOAD_REQUEST} {id_peer} {piece_to_dl}")
                else:
                    manager.peers_dictionary[id_peer].manager_to_peer_queue.put(Communication.MANAGER_WAIT)

            # Dans le cas où les pieces sont téléchargés et que nécessite vérification
            elif len(manager.verified_pieces) < manager.nb_pieces and len(
                    manager.pieces_to_download) == 0:
                manager.peers_dictionary[id_peer].manager_to_peer_queue.put(Communication.MANAGER_WAIT)
                logger.debug(f"{Communication.MANAGER_WAIT} {id_peer} WAIT_PIECES_VERIFICATION")
        
        elif message == Communication.PEER_DOWNLOAD_DONE:
            manager.verified_pieces.append(manager.peers_dictionary[id_peer].current_no_piece)
            logger.debug(f"{Communication.PEER_DOWNLOAD_DONE} {id_peer} {manager.peers_dictionary[id_peer].current_no_piece}")
        elif message == Communication.PEER_DOWNLOAD_ERROR:
            # logger.debug(f'Refus {manager.peers_dictionary[id_peer].last_message}')
            manager.pieces_to_download.append(manager.peers_dictionary[id_peer].current_no_piece)
            peer_to_delete = id_peer
            logger.debug(f"{Communication.PEER_DOWNLOAD_ERROR} {id_peer} {manager.peers_dictionary[id_peer].current_no_piece}")
        else:
            print(f"Pourquoi tu fais ça {id_peer}")

    manager.peers_dictionary[id_peer].peer_to_manager_lock.release()
    if peer_to_delete is not None:
        del manager.peers_dictionary[id_peer]

    manager.peers_dictionary_lock.release()

    if len(manager.verified_pieces) == manager.nb_pieces and manager.peers_to_manager_queue.empty():
        break
