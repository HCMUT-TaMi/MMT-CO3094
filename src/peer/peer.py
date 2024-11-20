import socket
import threading
import time 
import json
import logging
from typing import Dict, List, Optional
import hashlib
from rich.console import Console
from rich.table import Table

import sys

import peer_node
from peer_node import Node 

import peer_cli 
import file_manager
console = Console()

class Peer:
    """
    Class Peer:

    """
    def __init__(self, config_file: str):
        self.config = self._load_config(config_file)
        self._setup_logging()  
        self.online = True
        self.lock = threading.Lock()
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
        self.online = True
        #   Start User Request
        threading.Thread(target=self._listen_handle, daemon=True).start()

        while self.online: 
            console.print("[bold green]Enter your choice:[/]", end=" ")
            choice = input()
            if choice == "View":
                console.print("[cyan]Viewing items...[/]")
            elif choice == "Download":
                console.print("[bold blue]Entering the file you want to announce: [/]")
                inp = console.input()
                time.sleep(0.1)
                console.print("[magenta]Waiting for Tracker Respone...[/]")
                threading.Thread(target=self.download,args=(inp,),daemon=True).start()
                
            elif choice == "Announce":
                console.print("[bold blue]Entering the file you want to announce: [/]")
                console.input()
                time.sleep(0.1)
                console.print("[red]Working on it...[/]")


            elif choice == "Quit":
                console.print("[bold yellow]Exiting...[/]")
                self.online = False  
                break
            else:
                console.print("[bold red]Invalid choice. Try again![/]")

    #   =======================================================
    #                   User_handle 
    #   =======================================================

    def sha1_encode(input_string:str):
        encoded_string = input_string.encode('utf-8')
        sha1_hash = hashlib.sha1(encoded_string)
        return sha1_hash.hexdigest()

    def _user_handle_askTracker(
            self, 
            file: str
    ):
        socket.settimeout(10)
        message = peer_cli.peer_ask_tracker(self.sha1_encode(file))
        try: 
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                message = peer_cli.peer_ask_tracker(self.sha1_encode(file))
                s.connect((self.config.get("tracker_host"),self.config.get("tracker_port")))
                s.send(json.dumps(message).encode("utf-8"))
                data = s.recv(512*1024)

                try: 
                    data = json.loads(data) 
                except json.JSONDecodeError:
                    console.print("[bold red]Failed to decode tracker response - invalid JSON[/]")
                    return None
                
                if 
                

        except socket.timeout:
            console.print("[bold red]Connection timed out after {} seconds. Tracker not responding.[/]".format(10))
            return None

        finally: 
            s.close()

        return data 
            

    def download(
            self,
            file: str, 
    )->None:
        self._user_handle_askTracker(file)

        
        


    
