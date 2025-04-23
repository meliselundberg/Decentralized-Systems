import webbrowser
import subprocess
import time

# Start Flask server in background
subprocess.Popen(["python3", "blockchain.py", "-p", "5001"])

# Wait a bit to ensure server starts
time.sleep(2)

# Open browser to GUI
webbrowser.open("http://localhost:5001/gui")
