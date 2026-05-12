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

DEFAULT_PAYLOAD = {
    "negative_prompt": "lowres, bad anatomy, bad hands, blurry, text, watermark",
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


def resolve_local_path(value, default):
    raw = str(value or default).strip()
    if not raw:
        raw = default
    if os.path.isabs(raw):
        return raw
    return os.path.join(BASE_DIR, raw)


def studio_dir(config):
    return resolve_local_path(os.getenv("STUDIO_DIR") or config.get("studio_dir"), "local_studio")


def payload_path(config):
    return os.path.join(studio_dir(config), "payload.json")


def output_dir(config, override=None):
    if override:
        return resolve_local_path(override, override)
    return os.path.join(studio_dir(config), "direct_outputs")


def history_dir(config):
    value = os.getenv("HISTORY_DIR") or config.get("history_dir")
    return resolve_local_path(value, "local_studio/history")


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


def save_payload(payload, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
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


def save_response_images(response, target_dir):
    images = response.get("images") if isinstance(response, dict) else None
    if not isinstance(images, list) or not images:
        return []

    os.makedirs(target_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = []
    for index, image_data in enumerate(images, start=1):
        raw = decode_image_data(image_data)
        if not raw:
            continue
        path = os.path.join(target_dir, f"{timestamp}_{index:02d}.png")
        with open(path, "wb") as f:
            f.write(raw)
        saved.append(path)

    meta_path = os.path.join(target_dir, f"{timestamp}_response.json")
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


def api_reachable(raw_url, timeout=3):
    parsed = urlparse(str(raw_url or "http://127.0.0.1:3883").strip())
    if not parsed.scheme or not parsed.netloc:
        probe = raw_url
    else:
        probe = urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))
    try:
        req = Request(probe, method="GET")
        with urlopen(req, timeout=timeout):
            return True
    except HTTPError:
        return True
    except (OSError, URLError, ValueError):
        return False


def warn_history_dir(path):
    if not path:
        return
    if not os.path.exists(path):
        print(f"Warning: history_dir does not exist: {path}", file=sys.stderr)
        print("If Draw Things is configured to write there, check that the disk is mounted.", file=sys.stderr)
        return
    if not os.path.isdir(path):
        print(f"Warning: history_dir is not a directory: {path}", file=sys.stderr)
        return
    if not os.access(path, os.W_OK):
        print(f"Warning: history_dir is not writable: {path}", file=sys.stderr)


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
    parser.add_argument("--output-dir", help="Directory for decoded API images. Defaults to local_studio/direct_outputs.")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip API and history directory checks.")
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
    out_dir = output_dir(config, args.output_dir)
    payload_file = payload_path(config)

    if args.dry_run:
        print(f"Endpoint: {target_url}")
        print(f"Payload file: {payload_file}")
        print(f"Output dir: {out_dir}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not args.skip_preflight:
        if not api_reachable(config.get("draw_things_url")):
            print(f"Draw Things API is not reachable: {config.get('draw_things_url') or 'http://127.0.0.1:3883'}", file=sys.stderr)
            return 1
        warn_history_dir(history_dir(config))

    if not args.no_save_payload:
        save_payload(payload, payload_file)

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

    saved = save_response_images(response, out_dir)
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
