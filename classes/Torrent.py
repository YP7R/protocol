import bencode
import hashlib

from numba.cuda import const


class Torrent:
    def __init__(self, torrent_file):

        with open(torrent_file, mode='rb') as fp:
            lines = fp.readlines()
        fp.close()
        content = b''.join(lines)
        self.torrent_information = bencode.decode(content)

        # Mandatory
        self.announce = self.torrent_information['announce']
        self.info_hash = hashlib.sha1(bencode.encode(self.torrent_information['info'])).digest()

        # Mandatory in ['info']
        self.piece_length = self.torrent_information['info']['piece length']
        self.pieces = self.torrent_information['info']['pieces']
        self.name = self.torrent_information['info']['name']

        self.sha1_pieces = [self.pieces[piece * 20:(piece + 1) * 20] for piece in range(len(self.pieces) // 20)]

        self.mode = 'multiple' if 'files' in self.torrent_information['info'] else 'single'
        if self.mode == 'multiple':
            files = []
            for file in self.torrent_information['info']['files']:
                filename, length = '/'.join(file['path']), file['length']
                files.append((filename, length))
            self.files = files
        elif self.mode == 'single':
            files = [(self.torrent_information['info']['name'], self.torrent_information['info']['length'])]
            self.files = files
