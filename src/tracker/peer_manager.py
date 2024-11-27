# src/tracker/peer_manager.py
import threading
import time
from typing import Dict, List, Optional
import logging

class PeerManager:
    """
    Class PeerManager:
    - Manages peer connections and piece availability.
    - It keeps track of connected peers and the pieces they have available.
    - It provides methods to add and remove peers, update piece availability, and get peers for specific pieces.
    
    Attributes:
    @peers: A dictionary of peer information indexed by peer_id.
    @pieces: A dictionary of piece hashes indexed by peer_id.
    @lock: A threading lock to protect shared data structures
    """
    def __init__(self):
        self.peers: Dict[str, Dict] = {}  # {peer_id: peer_info}
        self.pieces: Dict[str, List[str]] = {}  # {peer_id: [piece_hashes]}
        self.lock = threading.Lock()

    def add_peer(self, peer_id: str, ip: str, port: int) -> None:
        with self.lock:
            self.peers[peer_id] = {
                'ip': ip,
                'port': port,
                'last_seen': time.time(),
                'uploaded': 0,
                'downloaded': 0
            }

    def update_pieces(self, peer_id: str, pieces: List[str]) -> None:
        with self.lock:
            self.pieces[peer_id] = pieces

    def get_peers_for_pieces(self, wanted_pieces: List[str], exclude_peer: str) -> List[Dict]:
        return available_peers

    def cleanup_stale_peers(self, max_age: int) -> None:
        """Remove peers that haven't been seen recently"""
        current_time = time.time()
        with self.lock:
            stale_peers = [
                peer_id for peer_id, peer in self.peers.items()
                if current_time - peer['last_seen'] > max_age
            ]
            for peer_id in stale_peers:
                del self.peers[peer_id]
                if peer_id in self.pieces:
                    del self.pieces[peer_id]