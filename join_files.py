from classes.Torrent import Torrent
import glob
import re
import shutil
import os
torrent_file = "./files/debian-10.3.0-amd64-netinst.iso.torrent"
torrent = Torrent(torrent_file)

pieces_name = sorted(glob.glob('.\\pieces\\*.part'), key=lambda f: int(re.sub('\\D', '', f)))


with open(f'./files/{torrent.name}', 'wb+') as outfile:
    for piece_file in pieces_name:
        with open(piece_file,'rb') as infile:
            for line in infile:
                outfile.write(line)

with open(f"./files/{torrent.name}", mode='rb') as fp:
    lines = fp.readlines()
fp.close()
file_content = b''.join(lines)
print(len(file_content))

shutil.rmtree('.\\files\\torrent\\',ignore_errors=True)
os.makedirs('.\\files/torrent\\')

current_offset = 0
for name, length in torrent.files:
    with open(f'./files/torrent/{name}', 'wb+') as outfile:
        outfile.write(file_content[0:length])
    outfile.close()
    current_offset += length
