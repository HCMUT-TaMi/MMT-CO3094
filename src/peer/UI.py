import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
from typing import Optional, Dict
from peer import Peer
import queue
import uuid
import traceback

class DownloadProgressBar:
    def __init__(self, parent_frame, row, file_name):
        self.frame = ttk.Frame(parent_frame)
        self.frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=2)
        
        # File name label
        self.file_label = ttk.Label(self.frame, text=file_name, width=20)
        self.file_label.grid(row=0, column=0, padx=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(self.frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Percentage label
        self.percent_label = ttk.Label(self.frame, text="0%", width=10)
        self.percent_label.grid(row=0, column=2, padx=5)
        
        # Unique identifier
        self.id = str(uuid.uuid4())
        
    def update_progresses(self, downloaded, total):
        try:
            # Ensure thread-safe and safe division
            if total > 0:
                progress = min(100, max(0, (downloaded / total) * 100))
                
                # Use try-except to handle potential GUI update errors
                try:
                    self.progress_bar["value"] = progress
                    self.percent_label.config(text=f"{progress:.1f}%")
                except Exception as e:
                    print(f"GUI update error: {e}")
                    traceback.print_exc()
            
            # Ensure 100% is set for complete downloads
            if downloaded == total and total > 0:
                try:
                    self.progress_bar["value"] = 100
                    self.percent_label.config(text="100%")
                except Exception as e:
                    print(f"Final progress update error: {e}")
                    traceback.print_exc()
        
        except Exception as e:
            print(f"Unexpected error in update_progresses: {e}")
            traceback.print_exc()

class PeerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("P2P File Sharing Application")
        self.root.geometry("800x700")
        
        # Initialize queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        self.login_state = False

        # Initialize peer
        self.peer: Optional[Peer] = None
        self.login_button = None  # Will store the connect/disconnect button
        
        # Track multiple download progress bars
        self.download_bars: Dict[str, DownloadProgressBar] = {}
        
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
        
        # Create the login/disconnect button
        self.login_button = ttk.Button(login_frame, text="Connect", command=self.toggle_connection)
        self.login_button.grid(row=0, column=2, padx=5)

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
        
        # Downloads Frame
        downloads_frame = ttk.LabelFrame(main_container, text="Downloads", padding="5")
        downloads_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        self.downloads_frame = downloads_frame
        
        # Log Frame
        log_frame = ttk.LabelFrame(main_container, text="Activity Log", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(3, weight=1)
        operations_frame.columnconfigure(1, weight=1)
        downloads_frame.columnconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def toggle_connection(self):
        if not self.login_state:
            # Connect
            username = self.username_entry.get()
            try:
                self.peer = Peer(username)
                self.log_message(f"Connected as {username}")
                threading.Thread(target=self._start_peer_listening, daemon=True).start()
                
                # Update button and state
                self.login_button.configure(text="Disconnect")
                self.login_state = True
                self.username_entry.configure(state='disabled')
            except Exception as e:
                messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
        else:
            # Disconnect
            try:
                if self.peer:
                    self.peer.bye()
                    self.log_message("Disconnected")
                
                # Reset button and state
                self.login_button.configure(text="Connect")
                self.login_state = False
                self.username_entry.configure(state='normal')
                self.peer = None
            except Exception as e:
                messagebox.showerror("Disconnection Error", f"Failed to disconnect: {str(e)}")

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
        
        # Create a new download progress bar
        download_bar = DownloadProgressBar(self.downloads_frame, len(self.download_bars), file)
        self.download_bars[download_bar.id] = download_bar
        
        def thread_safe_progress_update(downloaded, total):
            """Wrapper to ensure thread-safe progress updates"""
            def update_gui():
                try:
                    download_bar.update_progresses(downloaded, total)
                except Exception as e:
                    print(f"Progress update error: {e}")
                    traceback.print_exc()
            
            # Use queue.put to ensure thread-safe GUI update
            self.message_queue.put(update_gui)
        
        def download_thread():
            try:
                self.log_message(f"Starting download of {file}")
                self.peer.download(file, progress_callback=thread_safe_progress_update)
                
                # After successful download
                def show_completion():
                    self.log_message(f"Download complete: {file}")
                    messagebox.showinfo("Download Complete", f"The file '{file}' has been downloaded successfully!")
                    self._remove_download_bar(download_bar.id)
                
                # Ensure completion message is shown on main thread
                self.message_queue.put(show_completion)
            
            except Exception as e:
                def show_error():
                    self.log_message(f"Download error: {str(e)}")
                    traceback.print_exc()
                    self._remove_download_bar(download_bar.id)
                
                # Ensure error message is shown on main thread
                self.message_queue.put(show_error)
        
        threading.Thread(target=download_thread, daemon=True).start()

    def _remove_download_bar(self, bar_id):
        """Remove a download progress bar"""
        if bar_id in self.download_bars:
            bar = self.download_bars[bar_id]
            bar.frame.destroy()
            del self.download_bars[bar_id]

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
                traceback.print_exc()
                
        threading.Thread(target=announce_thread, daemon=True).start()

    def log_message(self, message: str):
        """Thread-safe logging to GUI"""
        self.message_queue.put(message)

    def check_queue(self):
        """Check for new messages to display"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                # If message is a function, call it (for GUI updates)
                if callable(message):
                    message()
                else:
                    # Fallback to original string logging
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