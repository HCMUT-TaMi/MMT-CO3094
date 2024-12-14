import subprocess
import sys 
import os

os.chdir("./src/peer")
script_path = "./src/peer/peer.py"

if len(sys.argv) < 2: 
    subprocess.run(["python", "./peer.py"])
else:
    subprocess.run(["python", "./peer.py", sys.argv[1]])