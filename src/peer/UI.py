import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
from typing import Optional
from peer import Peer
import queue

class PeerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("P2P File Sharing Application")
        self.root.geometry("800x600")
        
        # Initialize queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        
        # Initialize peer
        self.peer: Optional[Peer] = None
        self.setup_gui()
        self.check_queue()

    def setup_gui(self):
        # Create main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Login Frame
        login_frame = ttk.LabelFrame(main_container, text="Login", padding="5")
        login_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(login_frame, text="Username:").grid(row=0, column=0, padx=5)
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.grid(row=0, column=1, padx=5)
        self.username_entry.insert(0, "guest")
        
        ttk.Button(login_frame, text="Connect", command=self.connect_peer).grid(row=0, column=2, padx=5)

        # File Operations Frame
        operations_frame = ttk.LabelFrame(main_container, text="File Operations", padding="5")
        operations_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Download Section
        ttk.Label(operations_frame, text="Download File:").grid(row=0, column=0, padx=5)
        self.download_entry = ttk.Entry(operations_frame)
        self.download_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(operations_frame, text="Download", command=self.start_download).grid(row=0, column=2, padx=5)
        
        # Announce Section
        ttk.Label(operations_frame, text="Announce File:").grid(row=1, column=0, padx=5)
        self.announce_entry = ttk.Entry(operations_frame)
        self.announce_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(operations_frame, text="Announce", command=self.announce_file).grid(row=1, column=2, padx=5)
        
        # Log Frame
        log_frame = ttk.LabelFrame(main_container, text="Activity Log", padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(2, weight=1)
        operations_frame.columnconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def connect_peer(self):
        username = self.username_entry.get()
        try:
            self.peer = Peer(username)
            self.log_message(f"Connected as {username}")
            threading.Thread(target=self._start_peer_listening, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")

    def _start_peer_listening(self):
        """Start the peer's listening thread"""
        try:
            self.peer._listen_handle()
        except Exception as e:
            self.log_message(f"Listening thread error: {str(e)}")

    def start_download(self):
        if not self.peer:
            messagebox.showwarning("Warning", "Please connect first!")
            return
            
        file = self.download_entry.get()
        if not file:
            messagebox.showwarning("Warning", "Please enter a file name!")
            return
            
        def download_thread():
            try:
                self.log_message(f"Starting download of {file}")
                self.peer.download(file)
                self.log_message(f"Download complete: {file}")
            except Exception as e:
                self.log_message(f"Download error: {str(e)}")
                
        threading.Thread(target=download_thread, daemon=True).start()

    def announce_file(self):
        if not self.peer:
            messagebox.showwarning("Warning", "Please connect first!")
            return
            
        file = self.announce_entry.get()
        if not file:
            messagebox.showwarning("Warning", "Please enter a file name!")
            return
            
        def announce_thread():
            try:
                self.log_message(f"Announcing file: {file}")
                self.peer.announce(file)
                self.log_message(f"File announced: {file}")
            except Exception as e:
                self.log_message(f"Announce error: {str(e)}")
                
        threading.Thread(target=announce_thread, daemon=True).start()

    def log_message(self, message: str):
        """Thread-safe logging to GUI"""
        self.message_queue.put(message)

    def check_queue(self):
        """Check for new messages to display"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.log_text.insert(tk.END, f"{message}\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)

def main():
    root = tk.Tk()
    app = PeerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()