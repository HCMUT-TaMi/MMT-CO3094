from rich.console import Console
from rich.table import Table
import hashlib

console = Console()
#   For Peer_Node

def HelloWord(
    name: str
)->dict:
    return{
        "type": "hello",
        "info": name
    }


def discovery (
    file: str
)->dict:
    return {
        "type": "discovery",
        "info": file 
    }

#   For Peer_Node
def download(
    file:str, 
    frags:str
)->dict:
    return {
        "type": "download",
        "info": file,
        "fragments": frags
    }

#   For Peer
def announce(
    file:str,     
)->dict:
    return {
        "type": "announce",
        "info": file, 
    }

#   For Peer and Peer_Node
def bit_encode(
    frags: list[int], 
    noFrags: int  
)->str:
    mess = '0' * noFrags
    for frag in frags: 
        mess[frag] = '1'
    return mess 

#   For Peer and Peer_Node
def bit_decode(
    bits: str 
)->list[int]:
    return [i + 1 for i in range(len(bits)) if bits[i] == '1'] 
    
def ret_discovery(
    file: str, 
    frags: list[int], 
):
    return {
        "type": "discovery_return",
        "info": file,
        "frags": bit_encode(frags), 
    }

def out():
    return {
        "type": "out",
    }

def peer_ask_tracker(file: str) -> dict: 
    return {
        "type": "discover", 
        "info": file,
    }

def main_menu():
    table = Table(title="Main Menu")
    table.add_column("Option", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")
    
    table.add_row("1", "View Items")
    table.add_row("2", "Add Item")
    table.add_row("3", "Delete Item")
    table.add_row("q", "Quit")
    
    console.print(table)


def handle_input():
    while True:
        console.print("[bold green]Enter your choice:[/]", end=" ")
        choice = input()
        if choice == "1":
            console.print("[cyan]Viewing items...[/]")
        elif choice == "2":
            console.print("[magenta]Adding item...[/]")
        elif choice == "3":
            console.print("[red]Deleting item...[/]")
        elif choice == "q":
            console.print("[bold yellow]Exiting...[/]")
            break
        else:
            console.print("[bold red]Invalid choice. Try again![/]")

"""
    TODO LIST
    1. Create Download UI 
    2. Create Interaction UI between User and Tracker 
    3. Pray for it to works out 
"""

def sha1_encode(input_string:str):
    encoded_string = input_string.encode('utf-8')
    sha1_hash = hashlib.sha1(encoded_string)
    return sha1_hash.hexdigest()
