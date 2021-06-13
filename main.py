import bencode
import hashlib
import os
from classes.Torrent import Torrent
from classes.Tracker import Tracker
from classes.Manager import Manager

torrent_file = "./files/slackware64-14.2-install-dvd.torrent"
# torrent_file = "./files/debian-10.3.0-amd64-netinst.iso.torrent"

# My identification
me_peer_id = os.urandom(20)

torrent = Torrent(torrent_file)

manager = Manager(torrent, me_peer_id)
tracker = Tracker(manager)
tracker.run()


'''
for file in torrent_information['info']['files']:
    print(file)
    length, output_file = file['length'], '/'.join(file['path'])
    print(length)
    l+=length
'''
