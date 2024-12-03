import socket
import threading
import time 
import json
import os
import logging
import time
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
    def __init__(self, name: str):
        self.config = self._load_config(name)
        self.online = True
        self.lock = threading.Lock()
        # self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.thread_pool = []
        self.fileManager = FileManager(self.config["user_name"])
        self.IP = self.getIP()
        # self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM).bind(('localhod',self.config['tracker_port']))
        self.sayHitoTracker()


    def getIP(self): 
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80)) 
            local_ip = s.getsockname()[0]
            return local_ip 
            
    def sayHitoTracker(self): 
        ans = peer_cli.HelloWord(self.config['user_name'],self.config['user_port'], self.IP)
        try: 
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.config['tracker_host'],self.config['tracker_port']))
                s.sendall(json.dumps(ans).encode("utf-8"))
                ans = json.loads(s.recv(1024).decode("utf-8"))
        except Exception as e:  
            print(f"Cannot connect to Tracker due to: {e} \n PEER WILL BE DISABLE")
            self.online = False
            

        #   TODO 
        #   Connect with Tracker from here, change HelloWorld to fit the data 

    # def _setup_logging(self):
    #     logging.basicConfig(
    #         level=getattr(logging, self.config.get('log_level', 'INFO')),
    #         format='%(asctime)s [%(levelname)s] %(message)s',
    #         handlers=[
    #             logging.FileHandler("logs/peer.log"),
    #             logging.StreamHandler()
    #         ]
    #     )

    def _load_config(self, name: str) -> dict:
        
        config_file = os.path.join("./config", f"{name}.json")
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return {
                'file_path': 'data/downloads',
                'frags_path': 'data/uploads',
                'user_port': 5221, 
                'user_name': 'guest',
                'piece_size': 512*1024,
                'tracker_host': 'localhost',
                'tracker_port': 6880
            }
    def start(self):
        #   Start User Request
        threading.Thread(target=self._listen_handle, daemon=True).start()

        #   Handle by using Self.Lock ? 
        while self.online: 

            console.print("[bold green]Enter your choice:[/]", end=" ")
            choice = input()
            with self.lock:
                if choice == "View":
                    console.print("[cyan]Viewing items...[/]")

                elif choice == "Download":
                    console.print("[bold blue]Entering the file you want to Download: [/]")
                    inp = console.input()
                    console.print("[magenta]Waiting for Tracker Respone...[/]")
                    threading.Thread(target=self.download,args=(inp,),daemon=True).start()
                    
                elif choice == "Announce":
                    console.print("[bold blue]Entering the file you want to Announce: [/]")
                    inp = console.input()
                    console.print("[red]Working on it...[/]")
                    threading.Thread(target=self.announce,args=(inp,),daemon=True).start()

                elif choice == "Quit":
                    console.print("[bold yellow]Exiting...[/]")
                    self.online = False  
                    break
                
                elif choice == "Dump": 
                    self.fileManager.dump()
                    
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
                message = peer_cli.peer_ask_tracker(peer_cli.sha1_encode(file))                
                s.connect((self.config.get("tracker_host"),self.config.get("tracker_port")))
                
                s.send(json.dumps(message).encode("utf-8"))
                data = s.recv(512*1024)
                
                try: 
                    data = json.loads(data.decode("utf-8")) 
                except json.JSONDecodeError:
                    console.print("[bold red]Failed to decode tracker response - invalid JSON[/]")
                    return None
                
        except socket.timeout:
            console.print("[bold red]Connection timed out after 10 seconds. Tracker not responding.[/]".format(10))
            return None

        return data 
            

    def download(
            self,
            file: str, 
    )->None:
        data = self._user_handle_askTracker(file)

        #   TODO cout when no file in tracker 

        torrent = self.fileManager.looksfor(file)
        if torrent['type'] == "Found": 
            want_fragment = [i for i in range(1,torrent["fragsNum"] + 1) if i not in torrent["frags"]]
        else:
            want_fragment = [i for i in range(1,(int)(data["size"]/(512*1024)) + 2)]
        
        with self.lock: 
            print(f"i want {want_fragment}")

        #   Get all to prepare
        dowload_NODE = Node(
            data["peers"], 
            want_fragment, 
            file, 
            data["size"],
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
        try:
            with conn: 
                data = conn.recv(512*1024)
                data = json.loads(data.decode("utf-8"))
                if data['type'] == "discovery":
                    torrent = self.fileManager.looksfor(data['info'])
                    message = peer_cli.ret_discovery(data['info'],torrent['frags'],torrent['fragsNum'])
                    conn.send(json.dumps(message).encode("utf-8"))

                elif data['type'] == 'download': 
                    frags = peer_cli.bit_decode(data['fragments'])          
                    for frag in frags: 
                        print(f"sending Frag# {frag}")
                        frags_data = self.fileManager.getfrags(data['info'],[frag])
                        time.sleep(0.05)
                        
                        conn.send(len(frags_data).to_bytes(4,'big'))
                        # Establish a socket connection
                        # print(len(frags_data))
                        
                        conn.sendall(frags_data)
        except Exception as e:
            print(f"Details: {e}") 
                    

    def _listen_handle(self): 
        try: 
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0',self.config['user_port']))
                s.listen(9)
                
                with self.lock: 
                    print("Listening Socket setup complete!")
                    
                while self.online:
                    conn, addr = s.accept()
                    
                    with self.lock: 
                        print(f"Connect with {addr}")

                    runThread = threading.Thread(target = self.listen_to, args = (conn,addr,), daemon=True)
                    runThread.start()
                    
        except Exception as e:
            print(f"Details: {e}")
                    
    def announce(self,
                 file: str):
        try:  
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: 
                s.connect((self.config["tracker_host"],self.config["tracker_port"])) 
                #   TODO
                #   CHANGE THE MESSAGE TO FIT TRACKER IN peer_cli
                message = self.fileManager.newFiles(file,self.config['user_port'],self.IP)
                print(message)
                
                # message = peer_cli.announce(file)
                s.send(json.dumps(message).encode("utf-8"))

        except socket.error: 
            pass

def main():
    # Create and start tracker
    
    if len(sys.argv) < 2: 
        User = Peer('guest')
    
    else:
        User = Peer(sys.argv[1])
        
    User.start()

if __name__ == "__main__":
    main()
        