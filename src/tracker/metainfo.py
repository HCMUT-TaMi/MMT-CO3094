from dataclasses import dataclass
from typing import List, Dict

@dataclass
class MetaInfo:
    """
    Metadata for a torrent file
    Includes information about the files in the torrent
    info_hash: A unique identifier for the torrent
    piece_length: Length of each piece in bytes
    pieces: A list of SHA1 hashes for each piece
    files: A list of dictionaries containing file information
    total_size: Total size of all files in the torrent
    name: The name of the torrent
    """
    info_hash: str
    piece_length: int
    pieces: List[str]
    files: List[Dict]
    total_size: int
    name: str