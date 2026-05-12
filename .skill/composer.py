import json
import os
import subprocess
import sys

# 这是一个 AI 专用的自动化生成脚本
# 它会读取 KNOWLEDGE_BASE 中的规则，并应用到提示词中

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(BASE_DIR) == ".skill":
    BASE_DIR = os.path.dirname(BASE_DIR)

PAYLOAD_PATH = os.path.join(BASE_DIR, "studio", "payload.json")

def generate(description):
    # 标准 Janku V5 NSFW 预设
    payload = {
        "prompt": f"score_9, score_8_up, masterpiece, best quality, {description}, (vivid colors:1.1), dramatic shadows, cinematic lighting",
        "negative_prompt": "lowres, bad anatomy, bad hands, (plastic skin:1.3), (oily reflection:1.2), makeup, lipstick, adult, curvy, large breasts",
        "steps": 30,
        "width": 832,
        "height": 1216,
        "cfg_scale": 4.5,
        "sampler": "Euler a",
        "clip_skip": 2,
        "seed": -1
    }
    
    with open(PAYLOAD_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"--- Payload Generated ---\n{json.dumps(payload, indent=2)}\n")
    print("Writing to studio/payload.json... Done.")
    print("Ready to be pushed to API.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 generate_image.py 'your description'")
    else:
        generate(sys.argv[1])
