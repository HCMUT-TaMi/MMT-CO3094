import hashlib
import Torrent
import random 

#   Where we defide the Torrent data

class torrent:
    def __init__ (
        self, 
        info, 
        announce, #use for multiple tracker 
        create_date, 
        comment, 
    ):

        ##################################
        # INFO CONTAINS ALL OF THIS IN A DICTIONARY
        #   info = 
        #   [
        #       "Piece_len": #interger
        #       "Pieces": #strings of 20 byte SHA1 hash values
        #       "File_len": #interger
        #       "Path":  #File locations 
        #   ]
        #
        ##################################
        self.info = info    
        self.annouce = announce
        self.create_data = create_date
        #   Comment is used for Tracker -> Peer
        self.comment = comment 
        


        
        