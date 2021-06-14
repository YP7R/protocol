# protocol, _a simple implementation of the bittorent protocol [windows 10]_
## [main](./main.py)
This script downloads pieces
```
--- files
    | --- *.torrent
--- pieces
    | --- [*.part]
```
## [join_files](./join_files.py)
This script group pieces into simple file or multiple files
```
--- files
    | --- torrent
        | --- [files]
``` 

* https://www.bittorrent.org/beps/bep_0003.html
* https://wiki.theory.org/BitTorrentSpecification
* mutliple announce : http://bittorrent.org/beps/bep_0012.html  
* key parameter http://bittorrent.org/beps/bep_0007.html  

next ... transform manager class into a threading class  
next ... multiple announce list  
next ... try catch request  