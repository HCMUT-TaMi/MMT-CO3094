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
from file_manager import FileManager
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
        self.thread_pool = []
        self.fileManager = FileManager(self.config["user_name"])
        self.sayHitoTracker()

    def sayHitoTracker(): 
        ans = peer_cli.HelloWord()
        #   TODO 
        #   Connect with Tracker from here, change HelloWorld to fit the data 

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
                'file_path': 'data/downloads',
                'frags_path': 'data/uploads',
                'user_port': 1234, 
                'user_name': 'guest',
                'piece_size': 512*1024,
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

            with self.lock:
                if choice == "View":
                    console.print("[cyan]Viewing items...[/]")

                elif choice == "Download":
                    console.print("[bold blue]Entering the file you want to announce: [/]")
                    inp = console.input()
                    console.print("[magenta]Waiting for Tracker Respone...[/]")
                    threading.Thread(target=self.download,args=(inp,),daemon=True).start()
                    
                elif choice == "Announce":
                    console.print("[bold blue]Entering the file you want to announce: [/]")
                    inp = console.input()
                    console.print("[red]Working on it...[/]")
                    threading.Thread(target=self.announce,args=(inp,),daemon=True).start()
                elif choice == "Quit":
                    console.print("[bold yellow]Exiting...[/]")
                    with self.lock(): 
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

    """
        user_handle_askTracker 
        * Send request to Tracker to track files
        * Analyse the request from the tracker (in the download functions)
            if data.type == "not found" -> console back to user 
            else: 
                get peers list and file name hash
                check for fragment we need (least from which we have)
                run peer_node to dowload
                
    """

    def _user_handle_askTracker(
            self, 
            file: str
    ):
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
                
        except socket.timeout:
            console.print("[bold red]Connection timed out after 10 seconds. Tracker not responding.[/]".format(10))
            return None

        finally: 
            s.close()

        return data 
            

    def download(
            self,
            file: str, 
    )->None:
        data = self._user_handle_askTracker(file)
        torrent = self.fileManager.looksfor(file)
        want_fragment = [i for i in range(0,torrent["fragsNum"]) not in torrent["frags"]]

        #   Get all to prepare
        dowload_NODE = Node(
            data["peers"], 
            want_fragment, 
            file, 
            torrent["size"], 
            self.fileManager
        )

        #   Start Dowloading
        dowload_NODE.start() 


    """
        Receiving data having form: 
        "type": discover or download files 
        "info": get the info of the data
        "fragments": only for download type 
    """
    def listen_to(self, conn, addr):
        with conn: 
            data = conn.recv(1024)
            data = json.loads(data.decode("utf-8"))
            if data['type'] == "discovery":
                torrent = self.fileManager.looksfor(data['info'])
                message = peer_cli.ret_discovery(data['info'],torrent['frags'])
                conn.send(json.dumps(message).encode("utf-8"))

            elif data['type'] == 'download': 
                frag = peer_cli.bit_decode(data['fragments'])
                frags_data = self.fileManager.getfrags(data['info'],frag)
                # Establish a socket connection
                conn.sendall(frags_data)
                

    def _listen_handle(self): 
        try: 
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind('',self.config['port'])
                while self.online:
                    s.listen(9)
                    conn, addr = s.accept()
                    runThread = threading.Thread(target = self.listen_to, args = (conn,addr,), daemon=True)
                    runThread.start()
                    
        except socket.error: 
            #   Print out the error 
            pass
                    
    def announce(self,
                 file: str):
        try:  
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: 
                s.connect(self.config["tracker_host"],self.config["tracker_port"]) 
                #   TODO
                #   CHANGE THE MESSAGE TO FIT TRACKER IN peer_cli
                self.fileManager.newFiles(file)
                message = peer_cli.announce(file)
                s.send(json.dumps(message).encode("utf-8"))

        except socket.error: 
            pass

    def main():
        #TODO later on for testing 
        