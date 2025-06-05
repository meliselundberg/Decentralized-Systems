import webbrowser
import subprocess
import time
import requests

# Ask user for the port number, either 5001 or 5002, used to simulate two nodes
port = input("Enter the port number (e.g., 5001 or 5002): ")
other_ports = {
    "5001": "5002",
    "5002": "5001",
}

# Start Flask server in background with the chosen port
subprocess.Popen(["python3", "blockchain.py", "-p", port])

# Wait a bit to ensure server starts
time.sleep(2)

# Automatically register the peer node
if port in other_ports:
    try:
        peer_port = other_ports[port]
        requests.post(
            f"http://localhost:{port}/nodes/register",
            json={"nodes": f"localhost:{peer_port}"}
        )
        print(f"Registered localhost:{peer_port} as a peer of localhost:{port}")
        
        # NEW: trigger immediate sync
        requests.get(f"http://localhost:{port}/nodes/resolve")
        print("Initial sync complete.")
    except Exception as e:
        print(f"Could not register peer or sync: {e}")

# Open browser to GUI
print(f"[DEBUG] Node running on http://localhost:{port}")
webbrowser.open(f"http://localhost:{port}/gui")
