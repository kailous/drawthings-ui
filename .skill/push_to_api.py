import json
import urllib.request
import sys
import os

def push_payload():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # go up one level if we are in .skill/
    if os.path.basename(base_dir) == ".skill":
        base_dir = os.path.dirname(base_dir)
    
    payload_path = os.path.join(base_dir, "local_studio", "payload.json")
    config_path = os.path.join(base_dir, "config.json")
    
    # Load config to get port
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        port = config.get("port", 8080)
    except:
        port = 8080
        
    url = f"http://127.0.0.1:{port}/generate"
    
    if not os.path.exists(payload_path):
        print(f"Error: {payload_path} not found.")
        return

    with open(payload_path, "r", encoding="utf-8") as f:
        payload_data = f.read()

    req = urllib.request.Request(
        url,
        data=payload_data.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    print(f"Pushing payload to {url}...")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("Successfully submitted to generation queue!")
            print(f"Response: {resp.read().decode('utf-8')[:200]}...")
    except Exception as e:
        print(f"Failed to submit: {e}")

if __name__ == "__main__":
    push_payload()
