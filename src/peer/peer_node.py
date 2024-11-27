import socket
import threading
from typing import Dict, List, Tuple
import socket
import logging 
import peer_cli as CLI 
import json 
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from file_manager import FileManager

class Node: 
    def __init__ (
            self,
            peers: List[tuple[str,int]], #   Contain IP and Ports from receiving Peers from Tracker 
            want_fragment: List[str],
            file_name: str, #   Wanted file by User, HAVE BEEN HASHED
            len : int, 
            manage: FileManager
        ): 

        #   Peer Tracking
        self.len = len
        self._Peers = peers

        #   File Tracking
        self._File = file_name 
        self._BitTrack : Dict[Tuple, str] = {}  # Track of Peer and given BitTrack in form of 0b1101
        self._Total_Fragment = (int) (len / (512 * 1024)) + 1
        self.frag_size = 512 * 1024
        self._Want_Fragment = want_fragment
        #   Thread Safety
        self.lock = threading.Lock()  
        self.manage = manage

    """"
        Start(input): 
            * For each peers -> creates one Thread to receive the given files 
            * Handle Alogrithm for choosing the file we want first 
            * Check for files before stop 
            * Print out beutifully the information if the file is dowloaded 
    """

    def start(
            self,
        ):
        try: 
        #   DISCOVERY STAGE

             #   Create Threads for each peers to find out the peers which objects they own 
            Discover_Threads = []
            for peer in self._Peers: 
                thread = threading.Thread(target = self.discovery,args = (peer,),daemon = True)
                Discover_Threads.append(thread) 
                thread.start()          

            for thread in Discover_Threads: 
                thread.join()

        #   CHOOSING  STAGE
            #   Dowload_list release dictionary of peers and corresponding fragments
            dowload_list = self.rarest_first() 
  
        #   DOWNLOAD  STAGE
            #   Ensure that there is parent files 
            self.create_empty_file()
            Dowload_Threads = []

            #   Create Threads for each peers and corresponding fragments in Interger 
            for peer,frags in dowload_list.items(): 
                thread = threading.Thread(target = self.download, args = (peer,frags,))
                Dowload_Threads.append(thread)
                thread.start()

            for thread in Dowload_Threads: 
                thread.join()

        except: 
            logging(f"Problem connection with {peer[0]} and {peer[1]}\n")

    """ 
       Discovery: 
       * Ask peers which fragment do they have and return Dictionary of Peers and it's contain fragment
       * Input: IP and Ports of Threads
       * Output: Update _Discovery Dictionary 
    """

    def discovery(
            self,
            peer: tuple
    ): 
        try: 
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: 
                s.connect(peer)  #   peer[0] = IP, peer[1] = Port
                message = CLI.discovery(self._File)

                s.send(json.dumps(message).encode('utf-8'))
                bitwise = s.recv(1024).decode() 

                #   Expect to get the Bitwise in datas 
                with self.lock: 
                    self._BitTrack.update(peer,bitwise) 
        except: 
            logger.error(f"Cannot connect to IP: {peer[0]} with Port: {peer[1]} \n Please try again \n")
        finally: 
            s.close()

    """
        RAREST_FIRST and PEER SELETION 
        Input: 
        {
            "Peer 1": [Having Lists]
            "Peer 2": [Having Lists]
        }

        Procedure: 
            * Count number of pieces 
            * Quick Sort to Sorts 
            * Iterate through Sort List, finding the least contain Peer and assign new Peers to it 
            * Return the results 

        Output: 
        {
            "Peer 1": [Download List] 
            "Peer 2": [Download List]
        }

        """

    def rarest_first(self): 
        #   Counting the all the bit we have  
        count = [0] * self._Total_Fragment

        #   if User BitTrack having value of 1 then fragment counter + 1 
        for _,bittrack in self._BitTrack.items(): 
            for i in range(0,self._Total_Fragment): 
                if bittrack[i-1] == "1": 
                    count[i] += 1
        
        #   Using Sort to get Pieces that is rarest (on the [0] of the address)
        sorted_pieces = sorted(len(self._Peers), key = lambda piece : count[piece])
        peer_for_piece = {peer: [] for peer in self._Peers}       
        want_fragment = self._Want_Fragment

        for piece in sorted_pieces:

            #   If piece is not want by anyone then continue
            if piece not in want_fragment:
                continue

            #   Get all the users
            piece_for_peer = [peer for peer,bit in self._BitTrack.items() if bit[piece - 1] == "1"] #   Add into List if Peer having the require bit]
            min_peer = min(piece_for_peer,key = lambda x :len(peer_for_piece[x]))
            peer_for_piece[min_peer].append(piece) 
            want_fragment.remove(piece) 
            
        return peer_for_piece 
        
    def decode(
            self,
            frag:int
    ): 
        mess = ['0'] * self.len 
        mess[frag] = '1'
        return ''.join(mess)
    
    def create_empty_file(self):
        with open(self._File, 'wb') as f:
            f.seek(self.len - 1)
            f.write(b'\0')



    def download(self, peer: Tuple[str, int], frags: list[int]):
        count = 0
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

                #   Fragment number in Fragment lists
                for frag in frags:

                    #   Send File_Name and encode Fragment number 
                    s.send(json.dumps(CLI.download(self._File,CLI.bit_encode(frag))).encode('utf-8'))

                    #   Receive the fragment data in chunks
                    fragment_data = b""
                    expected_size = min(self.frag_size, self.len - self.frag_size * (frag - 1))  
                    while len(fragment_data) < expected_size:
                        chunk = s.recv(expected_size)
                        if not chunk:
                            raise ConnectionError(f"Incomplete fragment received for index {frag}")
                        fragment_data += chunk

                    logger.info(f"Downloaded {frag} fragments from {peer[0]}:{peer[1]}")
                    
                    # Write the fragment to the file
                    fragList = {
                        "info": f"{self._File}_{frag}", 
                        "name": f"{self._File}_{frag}",
                        "parent": self._File, 
                        "size": expected_size,
                        "frag_num": frag 
                    }

                    #   Write file
                    self.manage.addFragment(fragList,fragment_data,self.lock)

        except ConnectionError as e:
            print(f"Connection error: {e}")
        except Exception as e:
            print(f"Error connecting to IP: {peer[0]} on Port: {peer[1]}.\nDetails: {e}")

        finally: 
            s.close()