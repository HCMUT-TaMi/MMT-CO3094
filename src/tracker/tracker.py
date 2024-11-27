import socket
import threading
import json
import time
import logging
import hashlib
from typing import Dict, Optional
from .peer_manager import PeerManager
from .metainfo import MetaInfo


#Handle Multi-Threads
from _thread import *
import threading

class Tracker:
    """
    Class Tracker:
    - Tracker server is responsible for managing torrent metadata and peer connections.
    it uses a PeerManager to keep track of connected peers and their state.
    - The tracker server listens for incoming connections from peers and responds to announce requests.
    - It also periodically cleans up stale peer connections.
    - The tracker server is started by calling the start() method.
    - The server can be shutdown gracefully by calling the shutdown() method.

    Attributes:
    @config: A dictionary containing the tracker configuration.
    @torrents: A dictionary of torrent metainfo hash indexed by info_hash.
    @peer_managers: A dictionary of PeerManager instances indexed by info_hash.
    @lock: A threading lock to protect shared data structures from race condition.
    @running: A boolean flag indicating if the server is running
    """
    def __init__(self, config_file: str):
        self.config = self._load_config(config_file)
        self._setup_logging()
        self.torrents: Dict[str, MetaInfo] = {}
        self.peer_managers: Dict[str, PeerManager] = {}
        self.lock = threading.Lock()
        self.running = False

    def _setup_logging(self):
        logging.basicConfig(
            level=getattr(logging, self.config.get('log_level', 'INFO')),
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler("logs/tracker.log"),
                logging.StreamHandler()
            ]
        )

    def _load_config(self, config_file: str) -> dict:
        """
        Load the tracker configuration from a JSON file.
        """
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return {
                'port': 6001,
                'ip': '127.0.0.1',
                'announce_interval': 1800,
                'cleanup_interval': 1800,
                'max_peers_per_torrent': 50
            }

    def start(self):
        """
        Start the tracker server.

        The server listens for incoming connections from peers and responds to announce requests.
        It also periodically cleans up stale peer connections.

        The server runs in a loop until the running flag is set to False.
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.config.get('ip', '127.0.0.1'), int(self.config.get('port', 6001))))
            self.server_socket.listen(int(self.config.get('listen_backlog', 50)))
            self.running = True
            logging.info(f"Tracker running on {self.config.get('ip', '127.0.0.1')}:{self.config.get('port', 6001)}")

            # Start peer cleanup thread
            # threading.Thread(target=self._peer_cleanup_daemon, daemon=True).start()

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logging.debug(f"Accepted connection from {address}")
                    threading.Thread(target=self._handle_peer, args=(client_socket,), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error(f"Error accepting connections: {e}")
        except Exception as e:
            logging.critical(f"Failed to start tracker: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """
        Shutdown the tracker server gracefully.
        """
        self.running = False
        try:
            if hasattr(self, 'server_socket'):
                self.server_socket.close()
                logging.info("Server socket closed.")
        except Exception as e:
            logging.error(f"Error closing server socket: {e}")

    def _handle_peer(self, client_socket: socket.socket):
        """
        Handle incoming connections from peers.

        The method reads the incoming data and processes the announce request.
        """
        try:
            data = client_socket.recv(4096)

            if not data:
                return
            
            request = json.loads(data.decode())

            if request['type'] == 'announce':
                self._handle_announce(client_socket, request)

        except Exception as e:
            logging.error(f"Error handling peer: {e}")
        finally:
            client_socket.close()
    
    def _handle_announce(self, client_socket: socket.socket, request: Dict):
        """
        Handle announce requests from peers.

        The method processes the announce request and updates the peer manager.
        It also sends a response back to the peer with a list of other peers.
        """
        try:
            info_hash = request['info_hash']
            peer_id = request['peer_id'] 
            port = request['port']
            peer_manager = self._get_peer_manager(info_hash)
            peer_manager.add_peer(peer_id, client_socket.getpeername()[0], port)
            response = {
                'peers': peer_manager.get_peers_for_pieces(request['pieces'], peer_id)
            }
            client_socket.sendall(json.dumps(response).encode())
        except Exception as e:
            logging.error(f"Error handling announce: {e}")

    def _get_peer_manager(self, info_hash: str) -> PeerManager:
        """
        Get the PeerManager instance for a specific torrent.

        If the PeerManager does not exist, it creates a new instance.
        """
        with self.lock:
            if info_hash not in self.peer_managers:
                self.peer_managers[info_hash] = PeerManager()
            return self.peer_managers[info_hash]
        
    

        

        