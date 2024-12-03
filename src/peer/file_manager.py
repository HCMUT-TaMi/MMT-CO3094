import os
from typing import List, Dict, Optional
import peer_cli as CLI
from dataclasses import dataclass
import json
from pathlib import Path
import logging
import threading

@dataclass
class FileInfo:
    file_name: str
    fragment_hash: dict[int,str]    # Fragment# : hashing
    total_fragments: int    
    size: int 

class FileManager:
    """
    class FileManager:
        
        File for 1 peer 
        "
            |   Torrent File (contain all the hash name)
            |   Results File (contain the filen name, fragment hash name)
            |   Fragments File (use to send to if users needed)  
        "
        Torrent File contain:
        Torrent file name: "info" hash name  
        "
            |   Whole File Name   
            |   Fragment Numbers 
            |   Size
        "
    """
    def __init__(self, name: str):
        # self.logger = logging.getLogger(__name__)
        self.path = os.path.join("./data",name)
        os.makedirs(self.path, exist_ok=True)

        self.torrent_path = os.path.join(self.path,"torrents.json")
        # self.frags_path = os.path.join(self.path,"/frags") 
        self.files_path = os.path.join(self.path,"files")

        # os.makedirs(self.frags_path,exist_ok=True)
        os.makedirs(self.files_path,exist_ok=True)

        self.torrents : dict[str,FileInfo]
        check = Path(self.torrent_path) 

        if check.is_file():
            #   Read old JSON file
            with open(self.torrent_path,"r") as file:
                self.torrents = json.load(file)
        else: 
            #   Create new JSON file
            with open(self.torrent_path,"w") as file:
                json.dump({}, file)

    def getFile(self):
        return {
            "path": self.path, 
            "frags_path": self.frags_path, 
            "files_path": self.files_path
        }
        
    def getFileAt(self, inf: str): 
        if inf in self.torrents.keys():
            return {
                'type': 'return',
                'name': self.torrents[inf].file_name,
                'size': self.torrents[inf].size
            }
            
    def creatEmptyFile(self, name:str, size: int): 
        path = os.path.join(self.files_path,name)
        with open(path, 'wb') as f:
            f.seek(size - 1)
            f.write(b'\0')
            
        #   Continue with hash here 
        newTorrent = FileInfo(
            file_name = name, 
            fragment_hash = {}, 
            total_fragments = 0, 
            size = size 
        )
        
        self.torrents.update({
            CLI.sha1_encode(name): newTorrent
        })


    """
        WARNING 100!!: Parent file MUST BE EXIT
        Add Fragment info: 
            * "info": str # use for hashing  
            * "name": str 
            * "parent": str 
            * "size": int 
            * "frag_num": int
    """
    def addFragment(
            self,
            info: dict[str,str,str,int,int], # all of the info is in SHA1 form
            data, 
    ): 
        
        #   Create new Torrent for Fragments
        new_torrent = FileInfo(
            info["name"], 
            {},
            1, 
            info["size"] 
        ) 
        self.torrents.update({info["info"]: new_torrent})
            
        parent_torrent = self.torrents[info["parent"]]
        #   Get new Frag_num = Hash_str 
        parent_torrent.fragment_hash.update({info["frag_num"] : info["info"]})

        # pathToFrags = os.path.join(self.frags_path,info["info"])
        pathToParent = os.path.join(self.files_path,self.torrents[info["parent"]].file_name)
        offset = (info["frag_num"] - 1) * 512 * 1024
        
        print("file is writting !!!!")

        #   Update Real File          
        try:
                #   UPDATE Parent file always exits as handle by Peer_node, HANDLE IF WANTED 
                with open(pathToParent, "rb+") as f:
                    f.seek(offset)
                    f.write(data)

                # with lock: 
                #     #   Update the Json file of Torrent File
                #     with open(self.torrent_path, "") as fc: 
                #         fc.read()
                
                parent_torrent.total_fragments += 1

        except IOError as e:
            self.logger.error(f"Failed to write to parent file: {str(e)}")
            return False
        
    """
        WARNING 100!!: Parent file MUST BE EXIT
        This used to check for file that we have and send back information for our friends 
        Looks for file: 
            * "info": str # use for hashing  to find the file
    """
    def looksfor(
        self,
        info: str,
    ):
        # TODO if not found throw
        if CLI.sha1_encode(info) not in self.torrents:
            return {
                "type": "Not Found"
            }
        
        files = self.torrents[CLI.sha1_encode(info)]
        fragment_lists = [i for i in files.fragment_hash.keys()]
        
        print(f"we have: {fragment_lists}")
        return {
            "type": "Found", 
            "frags": fragment_lists,  #interger lists
            "fragsNum": files.total_fragments, 
            "size": files.size 
        }
    
    """
        WARNING 100!!: Parent file MUST BE EXIT
        This used to get the file and lets other to download the files or announcing the file we own  
        Looks for file: 
            * "info": str # use for hashing to find the File
            * "wantFrags": list[int]
        return: Possition of the files to send
    """
        
    def getfrags(
        self,
        info:   str, 
        frags:  list[int], 
    ):
        info = CLI.sha1_encode(info)
        file_path = os.path.join(self.files_path,self.torrents[info].file_name)
        for frag in frags: 
            with open(file_path,"rb") as file: 
                #   Go to the Fragment possition (Fragment#1 = pos 0) then read 512Kb of files
                file.seek((frag - 1) * 512 * 1024)
                frags_data = file.read(512*1024) 
                if not frags_data: 
                    return 

            return frags_data
        
    def breakFile(
        self,
        info: str, 
        len: int
    ):
        num_of_fragment = (int) (len/(512*1024)) + 1
        torrent = self.torrents[info] 
        hash_name = CLI.sha1_encode(info)
        for i in range(1,num_of_fragment+1):
            size = min(len - (i - 1) * 512 * 1024, 512 * 1024) 
            new_torrent = FileInfo(
                info, 
                {},
                0,
                size, 
            ) 
            #   Add Fragment into torrents
            self.torrents.update({f"{hash_name}_{i}":new_torrent})
            #   Update Torrent list, which hash is it and the name of its 
            torrent.fragment_hash.update({i:f"{hash_name}_{i}"}) 
            torrent.total_fragments += 1

        """
            Create new files into File modify by updating the torrent file 
            input: 
                file (not SHA1)
                size (file size)
            Work: 
                First, 
        """
        
    def dump(self):
        for frg in self.torrents.keys():
            print(f"{frg}: {self.torrents[frg].file_name}\n {self.torrents[frg].fragment_hash}\n {self.torrents[frg].total_fragments}\n") 
              
        
        
    def newFiles(
            self,
            file: str,
            port: int,
            ip: str
    )->None: 
        
        inf = CLI.sha1_encode(file)
        if CLI.sha1_encode(file) in self.torrents.keys(): 
            return {
                'type': 'announce',
                'name': self.torrents[inf].file_name,
                'info': inf, 
                'size': self.torrents[inf].size,
                'port': port,
                'IP': ip, 
            }
        
        #   TODO 
        #   IF file is not exits then throw exeptions 
        path = os.path.join(self.files_path,file) 
        size = os.path.getsize(path)
        new_torrent = FileInfo(
            file, 
            {},
            0,
            size, 
        )
        self.torrents.update({CLI.sha1_encode(file):new_torrent})
        self.breakFile(CLI.sha1_encode(file),size)
        return {
                'type': 'announce',
                'name': self.torrents[inf].file_name,
                'info': inf,
                'size': self.torrents[inf].size,
                'port': port,
                'IP': ip, 
        }