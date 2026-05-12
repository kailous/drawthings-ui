import json
import os
import shutil
import sys
from datetime import datetime

def archive(case_name):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    studio_dir = os.path.join(base_dir, "studio")
    config_path = os.path.join(base_dir, "config.json")
    payload_path = os.path.join(studio_dir, "payload.json")
    good_cases_dir = os.path.join(studio_dir, "good_cases")
    
    # 1. Load config
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        history_dir = config.get("history_dir")
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    if not history_dir or not os.path.isdir(history_dir):
        print(f"Error: history_dir '{history_dir}' is not a valid directory.")
        return

    # 2. Find newest image in history_dir
    files = [os.path.join(history_dir, f) for f in os.listdir(history_dir) 
             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    if not files:
        print("No images found in history directory.")
        return
    
    latest_image = max(files, key=os.path.getmtime)
    
    # 3. Create target directory
    timestamp = datetime.now().strftime("%Y%m%d")
    folder_name = f"{timestamp}_{case_name}"
    target_dir = os.path.join(good_cases_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # 4. Copy files
    img_ext = os.path.splitext(latest_image)[1]
    shutil.copy2(latest_image, os.path.join(target_dir, f"result{img_ext}"))
    if os.path.exists(payload_path):
        shutil.copy2(payload_path, os.path.join(target_dir, "prompt.json"))
    
    print(f"Successfully archived to: {target_dir}")
    print(f"Archived image: {os.path.basename(latest_image)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 archiver.py 'case_name'")
    else:
        archive(sys.argv[1])
