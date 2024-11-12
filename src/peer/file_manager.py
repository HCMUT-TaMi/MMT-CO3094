import os
import hashlib
from typing import List, Dict, Optional
import logging

class FileManager:
    """
    class FileManager:
    - Manages file operations for downloads and uploads.
    - It provides methods to initialize downloads, 
    write pieces to files, and read pieces from files.
    - It also provides a method to get a list of files available for sharing.

    Attributes:
    @download_path: A string representing the path to store downloaded files.
    @upload_path: A string representing the path to store files available for sharing.
    """
    def __init__(self, download_path: str, upload_path: str):
        self.download_path = download_path
        self.upload_path = upload_path
        os.makedirs(download_path, exist_ok=True)
        os.makedirs(upload_path, exist_ok=True)

    def init_download(self, torrent_name: str, total_size: int) -> str:
        """
        Initialize a file for downloading
        """
        file_path = os.path.join(self.download_path, torrent_name)
        with open(file_path, 'wb') as f:
            f.truncate(total_size)
        return file_path

    def write_piece(self, file_path: str, piece_data: bytes, offset: int) -> bool:
        """
        Write a piece to the file at the specified offset
        """
        try:
            with open(file_path, 'r+b') as f:
                f.seek(offset)
                f.write(piece_data)
            return True
        except Exception as e:
            logging.error(f"Failed to write piece: {e}")
            return False

    def read_piece(self, file_path: str, offset: int, length: int) -> Optional[bytes]:
        """
        Read a piece from the file at the specified offset
        """
        try:
            with open(file_path, 'rb') as f:
                f.seek(offset)
                return f.read(length)
        except Exception as e:
            logging.error(f"Failed to read piece: {e}")
            return None

    def get_files_for_sharing(self) -> List[Dict]:
        """
        Get a list of files available for sharing
        """
        shared_files = []
        for filename in os.listdir(self.upload_path):
            file_path = os.path.join(self.upload_path, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                shared_files.append({
                    'name': filename,
                    'path': file_path,
                    'size': file_size
                })
        return shared_files