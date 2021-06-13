import bencode
import hashlib


class Torrent:
    def __init__(self, torrent_file):

        with open(torrent_file, mode='rb') as fp:
            lines = fp.readlines()
        fp.close()
        self.content = b''.join(lines)
        self.torrent_information = bencode.decode(self.content)

        # Mandatory
        self.announce = self.torrent_information['announce']
        self.info_hash = hashlib.sha1(bencode.encode(self.torrent_information['info'])).digest()

        # Mandatory in ['info']
        self.piece_length = self.torrent_information['info']['piece length']
        self.pieces = self.torrent_information['info']['pieces']
        self.name = self.torrent_information['info']['name']
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

