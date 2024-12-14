import socket
import threading
import json
import logging
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
import time

@dataclass
class FileInfo:
    file_name: str
    file_hash: list[Tuple[int,str]]   #   File hash and User info
    fragment_size: int = 512 * 1024 
    size: int = 0
    
    
class Tracker:
    def __init__(self, host: str = '0.0.0.0', port: int = 6880):
        self.host = host
        self.port = port
        
        print(host)
        
        # Track files and their fragments across peers
        self.files: Dict[str, FileInfo] = {}  # file_hash -> FileInfo
        self.peers: Dict[Tuple[int,str], bool] = {}  # file_hash -> {(ip, port) -> PeerStatus}
        self.online = True
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("Tracker")
        
        # Start server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        
    def start(self):
        """Start the tracker server"""
        self.logger.info(f"Tracker starting on {self.host}:{self.port}")
        thread = threading.Thread(target=self.command,args=(),daemon=True)
        thread.start() 
        
        while self.online:
            try:
                client_socket, address = self.server_socket.accept()
                client_handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_handler.daemon = True
                client_handler.start()
            except Exception as e:
                self.logger.error(f"Error accepting connection: {e}")
                
                
    def command(self): 
        while self.online: 
            option = input() 
            if option == "Quit": 
                self.online = False 
                break
                 
    def _handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Handle incoming client connections"""
        try:
            data = client_socket.recv(1024).decode('utf-8')
            request = json.loads(data)                
            command = request.get('type')
            
            with self.lock: 
                print(f"Peer {address} require for command {command}")
            if command == 'announce':
                response = self._handle_register(request, address)
            elif command == 'discover':
                response = self._handle_discover(request)
            elif command == 'hello':
                response = self._handle_hello(request)
            else:
                response = {'status': 'error', 'message': 'Unknown command'}
                
            print(response)
            client_socket.send(json.dumps(response).encode('utf-8'))
            
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON from {address}")
            client_socket.send(json.dumps({
                'status': 'error',
                'message': 'Invalid JSON format'
            }).encode('utf-8'))
        except Exception as e:
            self.logger.error(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
            
    def _handle_hello (self,request: dict):
        with self.lock: 
            self.peers[(request["IP"],request['port'])] = True 
            print(f"User {request['IP'], request['port']} have connected and {self.peers[(request['IP'], request['port'])]} is here !!")
            
        return {
                'status': 'success'
        }

    def _handle_register(self, request: dict, address: Tuple[str, int]) -> dict:

        """
            Input: 
                'type': 'announce',
                'name': self.torrents[inf].file_name,
                'info': inf,
                'size': self.torrents[inf].size,
                'port': int 
                'IP': str
        
        """
        """Handle peer registration with file information"""
        
        conn_addr = (request['IP'],request['port'])
        print(f"info: {request['info']}")
        
        with self.lock:  
            info = request['info']
            if info not in self.files.keys():
                new_file = FileInfo(
                    file_name = request['name'],
                    size = request['size'],
                    file_hash = [conn_addr]
                )
                
                self.files.update({info:new_file})
                print(f"{info} with {self.files[info]}")
                
            else: 
                if conn_addr not in self.files[info].file_hash:
                    self.files[info].file_hash.append(conn_addr)
            
            print(f"Peer {conn_addr} have Announce for file {self.files[info].file_name}")
            return {
                'status': 'success',
                'message': 'Registration successful'
            }
            
    def _handle_discover(self, request: dict) -> dict:
        """
            "type": "discover", 
            "info": str
        Handle peer discovery requests
        """
        file_hash = self.files[request['info']].file_hash
        peer_list = [x for x in file_hash if self.peers[x]]
        
        return {
            "peers": peer_list,
            "size": self.files[request['info']].size
        }
        
            
    # def _cleanup_stale_peers(self, file_hash: str):
    #     """Remove peers that haven't been seen in the last 5 minutes"""
    #     current_time = time.time()
    #     stale_timeout = 300  # 5 minutes
        
    #     with self.lock:
    #         if file_hash in self.peer_files:
    #             stale_peers = [
    #                 peer for peer, status in self.peer_files[file_hash].items()
    #                 if current_time - status.last_seen > stale_timeout
    #             ]
                
    #             for peer in stale_peers:
    #                 del self.peer_files[file_hash][peer]
                    
    # def get_stats(self) -> dict:
    #     """Get tracker statistics"""
    #     with self.lock:
    #         stats = {
    #             'total_files': len(self.files),
    #             'files': {}
    #         }
            
    #         for file_hash, file_info in self.files.items():
    #             peer_count = len(self.peer_files.get(file_hash, {}))
    #             total_fragments = file_info.total_fragments
                
    #             # Calculate total availability
    #             if peer_count > 0:
    #                 fragment_availability = {i: 0 for i in range(total_fragments)}
    #                 for peer_status in self.peer_files[file_hash].values():
    #                     for fragment in peer_status.fragments:
    #                         fragment_availability[fragment] += 1
                            
    #                 complete_copies = min(fragment_availability.values())
    #             else:
    #                 complete_copies = 0
                    
    #             stats['files'][file_hash] = {
    #                 'name': file_info.file_name,
    #                 'peer_count': peer_count,
    #                 'complete_copies': complete_copies
    #             }
                
    #         return stats

def main():
    # Create and start tracker
    tracker = Tracker('0.0.0.0', 6880)
    try:
        tracker.start()
    except KeyboardInterrupt:
        print("\nShutting down tracker...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        tracker.server_socket.close()

if __name__ == "__main__":
    main()