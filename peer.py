import subprocess
import sys 

script_path = "./src/peer/peer.py"

if len(sys.argv) < 2: 
    subprocess.run(["python", script_path])
else:
    subprocess.run(["python", script_path, sys.argv[1]])


        
        