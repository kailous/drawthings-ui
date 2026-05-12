#!/usr/bin/env python3
import argparse
import base64
import json
import os
import sys
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
STUDIO_DIR = os.path.join(BASE_DIR, "studio")
PAYLOAD_PATH = os.path.join(STUDIO_DIR, "payload.json")
OUTPUT_DIR = os.path.join(STUDIO_DIR, "direct_outputs")

DEFAULT_PAYLOAD = {
    "negative_prompt": "lowres, bad anatomy, bad hands, (plastic skin:1.3), (oily reflection:1.2), makeup, lipstick",
    "steps": 30,
    "width": 832,
    "height": 1216,
    "cfg_scale": 4.5,
    "sampler": "Euler a",
    "clip_skip": 2,
    "seed": -1,
}


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def endpoint_for_payload(raw_url, payload):
    raw = str(raw_url or "http://127.0.0.1:3883").strip()
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw

    path = (parsed.path or "").rstrip("/")
    endpoint = "img2img" if payload.get("init_images") else "txt2img"

    if path in ("", "/"):
        full_path = f"/sdapi/v1/{endpoint}"
    elif path.endswith("/sdapi/v1/txt2img"):
        full_path = path[: -len("/txt2img")] + f"/{endpoint}"
    elif path.endswith("/sdapi/v1/img2img"):
        full_path = path[: -len("/img2img")] + f"/{endpoint}"
    elif path.endswith("/sdapi/v1"):
        full_path = f"{path}/{endpoint}"
    else:
        full_path = path

    return urlunparse((parsed.scheme, parsed.netloc, full_path, "", "", ""))


def payload_from_args(args):
    if args.payload_json:
        with open(args.payload_json, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            raise ValueError("--payload-json must contain a JSON object")
    else:
        prompt = " ".join(args.prompt).strip()
        if not prompt:
            raise ValueError("Prompt is required unless --payload-json is provided")
        payload = dict(DEFAULT_PAYLOAD)
        payload["prompt"] = prompt

    if args.negative is not None:
        payload["negative_prompt"] = args.negative
    for arg_name, payload_name in (
        ("steps", "steps"),
        ("width", "width"),
        ("height", "height"),
        ("cfg_scale", "cfg_scale"),
        ("sampler", "sampler"),
        ("clip_skip", "clip_skip"),
        ("seed", "seed"),
    ):
        value = getattr(args, arg_name)
        if value is not None:
            payload[payload_name] = value
    return payload


def save_payload(payload):
    os.makedirs(STUDIO_DIR, exist_ok=True)
    with open(PAYLOAD_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def decode_image_data(value):
    if not isinstance(value, str):
        return None
    data = value
    if "," in data and data.split(",", 1)[0].startswith("data:image/"):
        data = data.split(",", 1)[1]
    try:
        return base64.b64decode(data)
    except Exception:
        return None


def save_response_images(response):
    images = response.get("images") if isinstance(response, dict) else None
    if not isinstance(images, list) or not images:
        return []

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = []
    for index, image_data in enumerate(images, start=1):
        raw = decode_image_data(image_data)
        if not raw:
            continue
        path = os.path.join(OUTPUT_DIR, f"{timestamp}_{index:02d}.png")
        with open(path, "wb") as f:
            f.write(raw)
        saved.append(path)

    meta_path = os.path.join(OUTPUT_DIR, f"{timestamp}_response.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        scrubbed = dict(response)
        scrubbed["images"] = [f"<base64 image {i + 1}>" for i in range(len(images))]
        json.dump(scrubbed, f, ensure_ascii=False, indent=2)
    return saved


def submit(payload, url, timeout):
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw_response": body}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Submit a prompt directly to Draw Things HTTP API without using the Web UI.",
    )
    parser.add_argument("prompt", nargs="*", help="Prompt text to submit.")
    parser.add_argument("--payload-json", help="Use an existing payload JSON file instead of prompt text.")
    parser.add_argument("--negative", help="Override negative_prompt.")
    parser.add_argument("--steps", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--cfg-scale", dest="cfg_scale", type=float)
    parser.add_argument("--sampler")
    parser.add_argument("--clip-skip", dest="clip_skip", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--no-save-payload", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print payload and endpoint without submitting.")
    args = parser.parse_args(argv)

    try:
        payload = payload_from_args(args)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    config = load_config()
    target_url = endpoint_for_payload(config.get("draw_things_url"), payload)

    if args.dry_run:
        print(f"Endpoint: {target_url}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not args.no_save_payload:
        save_payload(payload)

    print(f"Submitting to {target_url}...")
    try:
        response = submit(payload, target_url, args.timeout)
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace") if hasattr(e, "read") else str(e)
        print(f"HTTP {e.code}: {body[:1000]}", file=sys.stderr)
        return 1
    except (OSError, URLError) as e:
        print(f"Submit failed: {e}", file=sys.stderr)
        return 1

    saved = save_response_images(response)
    if saved:
        print("Saved images:")
        for path in saved:
            print(f"- {path}")
    else:
        preview = json.dumps(response, ensure_ascii=False)[:1000]
        print(f"No image array found in response: {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
