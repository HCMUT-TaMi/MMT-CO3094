import socket
import threading
import json
import time
import logging
import uuid
from typing import Dict, List, Optional
from .file_manager import FileManager
from .piece_manager import PieceManager

class Peer:
    """
    Class Peer:
    - Manages peer connections and torrent downloads.
    - It keeps track of active downloads and upload sockets.
    - It provides methods to start downloads,
      handle upload requests, and announce to the tracker.
    - The peer service is started by calling the start() method.
    - The service can be shutdown gracefully by setting the running flag to False.

    Attributes:
    @config: A dictionary containing the peer configuration.
    @peer_id: A unique identifier for the peer.
    @file_manager: An instance of FileManager to manage download and upload files.
    @active_downloads: A dictionary of active downloads indexed by info_hash.
    @upload_sockets: A dictionary of upload sockets indexed by peer_id.
    @running: A boolean flag indicating if the peer service is running.
    @lock: A threading lock to protect shared data structures
    """
    def __init__(self, config_file: str):
        self.config = self._load_config(config_file)
        self._setup_logging()
        self.peer_id = str(uuid.uuid4())
        self.file_manager = FileManager(
            self.config['download_path'],
            self.config['upload_path']
        )
        self.active_downloads: Dict[str, PieceManager] = {}
        self.upload_sockets: Dict[str, socket.socket] = {}
        self.running = False
        self.lock = threading.Lock()

    def _setup_logging(self):
        logging.basicConfig(
            level=getattr(logging, self.config.get('log_level', 'INFO')),
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler("logs/peer.log"),
                logging.StreamHandler()
            ]
        )

    def _load_config(self, config_file: str) -> dict:
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return {
                'download_path': 'data/downloads',
                'upload_path': 'data/uploads',
                'max_connections': 10,
                'piece_size': 524288,
                'tracker_host': 'localhost',
                'tracker_port': 6881
            }

    def start(self):
        """
        Start the peer service
        - Start upload listener
        - Start download manager
        - Start tracker announcer
        """
        self.running = True
        
        # Start upload listener
        threading.Thread(target=self._upload_listener, daemon=True).start()
        
        # Start download manager
        threading.Thread(target=self._download_manager, daemon=True).start()
        
        # Start tracker announcer
        threading.Thread(target=self._tracker_announcer, daemon=True).start()
        
        logging.info(f"Peer started with ID: {self.peer_id}")

    def download_torrent(self, metainfo: dict):
        """
        Start downloading a torrent
        """
        info_hash = metainfo['info_hash']
        
        if info_hash in self.active_downloads:
            logging.warning(f"Already downloading torrent: {info_hash}")
            return
        
        # Initialize piece manager
        piece_manager = PieceManager(
            metainfo['piece_length'],
            metainfo['pieces']
        )
        
        # Initialize download file
        file_path = self.file_manager.init_download(
            metainfo['name'],
            metainfo['total_size']
        )
        
        with self.lock:
            self.active_downloads[info_hash] = {
                'piece_manager': piece_manager,
                'file_path': file_path,
                'metainfo': metainfo
            }
        
        logging.info(f"Started download for torrent: {metainfo['name']}")

    def _upload_listener(self):
        """
        Listen for upload requests from other peers
        """
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', 0))  # Random port
        server_socket.listen(self.config['max_connections'])
        
        while self.running:
            try:
                client_socket, address = server_socket.accept()
                threading.Thread(
                    target=self._handle_upload_request,
                    args=(client_socket, address),
                    daemon=True
                ).start()
            except Exception as e:
                logging.error(f"Upload listener error: {e}")

    def _download_manager(self):
        """Manage multiple concurrent downloads"""
        while self.running:
            try:
                with self.lock:
                    for info_hash, download in self.active_downloads.items():
                        if len(download['piece_manager'].completed_pieces) < len(download['piece_manager'].piece_hashes):
                            self._request_pieces(info_hash)
                time.sleep(1)
            except Exception as e:
                logging.error(f"Download manager error: {e}")

    def _tracker_announcer(self):
        """Periodically announce to tracker"""
        while self.running:
            try:
                self._announce_to_tracker()
                time.sleep(self.config.get('announce_interval', 1800))
            except Exception as e:
                logging.error(f"Tracker announcer error: {e}")
    
    
    """
    Còn nữa nhưng t chưa làm kịp =)))
    """