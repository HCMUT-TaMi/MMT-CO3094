import hashlib
from typing import List, Dict, Set
import threading

class PieceManager:
    """
    class PieceManager:
    - Manages the download progress of a torrent.
    - It keeps track of completed pieces and pieces being downloaded by peers.
    - It provides methods to check if a piece is needed, start downloading a piece,
    and verify a downloaded piece.

    Attributes:
    @piece_length: Length of each piece in bytes
    @piece_hashes: A list of SHA1 hashes for each piece
    @completed_pieces: A set of indexes for completed pieces
    @in_progress: A dictionary of pieces being downloaded indexed by piece index
    @lock: A threading lock to protect shared data structures
    """
    def __init__(self, piece_length: int, pieces: List[str]):
        self.piece_length = piece_length
        self.piece_hashes = pieces
        self.completed_pieces: Set[int] = set()
        self.in_progress: Dict[int, Set[str]] = {}  # piece_index -> set of peer_ids
        self.lock = threading.Lock()

    def need_piece(self, index: int) -> bool:
        """
        Check if we need a specific piece
        """
        with self.lock:
            return index not in self.completed_pieces

    def start_piece(self, index: int, peer_id: str) -> bool:
        """
        Start downloading a piece
        @index: The index of the piece
        @peer_id: The peer id downloading the piece

        Returns:
        - True if the piece download is started
        - False if the piece is already completed or in progress
        """
        with self.lock:
            if index in self.completed_pieces:
                return False
            if index not in self.in_progress:
                self.in_progress[index] = set()
            self.in_progress[index].add(peer_id)
            return True

    def verify_piece(self, index: int, piece_data: bytes) -> bool:
        """
        Verify a downloaded piece
        @index: The index of the piece
        @piece_data: The data for the piece

        Returns:
        - True if the piece is valid
        - False if the piece is invalid
        """
        if index >= len(self.piece_hashes):
            return False
        
        piece_hash = hashlib.sha1(piece_data).hexdigest()
        if piece_hash == self.piece_hashes[index]:
            with self.lock:
                self.completed_pieces.add(index)
                if index in self.in_progress:
                    del self.in_progress[index]
            return True
        return False