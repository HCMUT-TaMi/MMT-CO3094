import socket
import threading
from typing import Dict, List, Tuple
import socket
import logging 
import peer_cli as CLI 
import json 
import logging
import time
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from file_manager import FileManager

class Node: 
    def __init__ (
            self,
            peers: List[tuple[str,int]], #   Contain IP and Ports from receiving Peers from Tracker 
            want_fragment: List[int],
            file_name: str, #   Wanted file by User, Not have been hash sadly for some reason
            len : int, 
            manage: FileManager,
            progress_callback=None
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
        self.count = 0
        self.local_lock = threading.Lock()
        
        #   Thread Safety
        self.lock = threading.Lock()  
        self.manage = manage

        self.progress_callback = progress_callback  # Store the callback
        self.downloaded_fragments = 0  # Track fragments downloaded

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
            start_time = time.time()
        #   DISCOVERY STAGE

             #   Create Threads for each peers to find out the peers which objects they own 
            with self.lock: 
                print("DISCOVERY STAGE")
            Discover_Threads = []
            for peer in self._Peers: 
                thread = threading.Thread(target = self.discovery,args = (peer,),daemon = True)
                Discover_Threads.append(thread) 
                thread.start()          

            for thread in Discover_Threads: 
                thread.join()

        #   CHOOSING  STAGE
            #   Dowload_list release dictionary of peers and corresponding fragments
            with self.lock: 
                print("GET LIST STAGE")
            dowload_list = self.rarest_first() 
            
            with self.lock: 
                print(f"Download List: {dowload_list}") 
                print("Download stage")
  
        #   DOWNLOAD  STAGE
            #   Ensure that there is parent files 
            self.manage.creatEmptyFile(self._File,self.len)
            Dowload_Threads = []

            #   Create Threads for each peers and corresponding fragments in Interger 
            for peer,frags in dowload_list.items(): 
                thread = threading.Thread(target = self.download, args = (peer,frags,))
                Dowload_Threads.append(thread)
                thread.start()

            for thread in Dowload_Threads: 
                thread.join()
                
            end_time = time.time()
            
            print(f"Downloading Complete!, time cost: {end_time-start_time}")

        except Exception as e: 
            print(f"Error code: {e}")

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
                s.connect((peer[0],peer[1]))  #   peer[0] = IP, peer[1] = Port
                message = CLI.discovery(self._File)
                s.send(json.dumps(message).encode('utf-8'))
                bitwise = s.recv(512*1024).decode() 
                bitwise = json.loads(bitwise)
                #   Expect to get the Bitwise in datas 
                with self.lock: 
                    self._BitTrack.update({(peer[0],peer[1]):bitwise["frags"]}) 
                    print(self._BitTrack)    
                
                    
        except Exception as e: 
            print(f" \n Error code: {e}")

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
            for i in range(1,self._Total_Fragment + 1): 
                if bittrack[i-1] == "1": 
                    count[i-1] += 1
        
        #   Using Sort to get Pieces that is rarest (on the [0] of the address)
        sorted_pieces = sorted(range(self._Total_Fragment), key = lambda piece : count[piece])
        peer_for_piece = {}
        for peer in self._Peers:
            peer_for_piece.update({(peer[0],peer[1]): []})   
        want_fragment = self._Want_Fragment
        for piece in sorted_pieces:

            #   If piece is not want by anyone then continue
            if piece + 1 not in want_fragment:
                continue

            #   Get all the users
            piece_for_peer = [peer for peer,bit in self._BitTrack.items() if bit[piece] == "1"] #   Add into List if Peer having the require bit]
            min_peer = min(piece_for_peer,key = lambda x :len(peer_for_piece[x]))
            peer_for_piece[min_peer].append(piece + 1) 
            want_fragment.remove(piece+1) 
            
        return peer_for_piece 
        
    def decode(
            self,
            frag:int
    ): 
        mess = ['0'] * self.len 
        mess[frag] = '1'
        return ''.join(mess)
    
    # def create_empty_file(self):
    #     with open(self._File, 'wb') as f:
    #         f.seek(self.len - 1)
    #         f.write(b'\0')
    

    def download(self, peer: Tuple[str, int], frags: list[int]):
        need = len(frags)
        total_fragments = len(frags)
        count = 0
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(peer)
                message = CLI.download(self._File,CLI.bit_encode(frags,self._Total_Fragment))
                s.send(json.dumps(message).encode('utf-8'))
                time.sleep(0.5)
                
                while count != need: 
                    fragment_data = b""
                    lol_data = b"" 
                    
                    print("sending the ACK")
                    s.send(b"OK")   # send OK
                    
                    print("Waiting for Reply")
                    s.recv(4)   # send that user have been received
                    
                    print("i have received the sent ACK and wait for size")
                    lol_data = s.recv(4)
                    expected_size = int.from_bytes(lol_data,'big')
                    print(f"expected for downloading: {expected_size}") 
                    
                    s.send(b"OK")
                    # mess = {
                    #         "frag": frag, 
                    #         "data": frags_data, 
                    #         "size": len(frags_data)
                    #     }
                    # fragment_data = s.recv(expected_size)
                    
                    
                    while len(fragment_data) < expected_size:
                        chunk = s.recv(expected_size - len(fragment_data))
                        fragment_data += chunk
                        if(len(fragment_data) == self.len - self.frag_size * (frags[len(frags) - 1] - 1)):
                            break
                    
                    print(f"Receiving {frags[count]} from {peer}")
                    
                    fragList = {
                             "info": f"{CLI.sha1_encode(self._File)}_{frags[count]}", 
                             "name": f"{CLI.sha1_encode(self._File)}_{frags[count]}",
                             "parent": CLI.sha1_encode(self._File), 
                             "size": expected_size,
                             "frag_num": frags[count] 
                         }
                                        
                    count += 1 
                    self.downloaded_fragments += 1

                    # Update progress every 1 fragments
                    if self.progress_callback and self.downloaded_fragments % 1 == 0:
                        self.progress_callback(count, total_fragments)

                    threading.Thread(
                        target=self.manage.addFragment, 
                        args=(fragList, fragment_data,), 
                        daemon=True
                    ).start()

        except ConnectionError as e:
            print(f"Connection error: {e}")
        except Exception as e:
            print(f"Error connecting to IP: {peer[0]} on Port: {peer[1]}.\nDetails: {e}")