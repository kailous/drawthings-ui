#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config.json"
USER_AGENT = "drawthings-ui-probe/1.0"


def load_config():
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_path(value, default):
    raw = str(value or default).strip() or default
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def studio_dir(config):
    return resolve_path(os.getenv("STUDIO_DIR") or config.get("studio_dir"), "local_studio")


def registry_path(config, override=None):
    if override:
        return resolve_path(override, override)
    return studio_dir(config) / "model_registry.json"


def base_url(config):
    raw = str(os.getenv("DRAW_THINGS_URL") or config.get("draw_things_url") or "http://127.0.0.1:3883").strip()
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", "")).rstrip("/")


def request_json(url, timeout=5):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
    if not body.strip():
        return None
    return json.loads(body)


def current_settings(config, timeout=5):
    root = base_url(config)
    errors = []
    for suffix in ("/sdapi/v1/options", "/"):
        url = root + suffix
        try:
            data = request_json(url, timeout)
            if isinstance(data, dict):
                return data, url
        except (HTTPError, URLError, OSError, json.JSONDecodeError) as e:
            errors.append(f"{url}: {e}")
    raise RuntimeError("; ".join(errors) or "Draw Things API did not return JSON settings")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_registry(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("models", {})
            data.setdefault("loras", {})
            data.setdefault("settings_seen", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {
        "version": 1,
        "models": {},
        "loras": {},
        "settings_seen": [],
    }


def update_item(bucket, name, timestamp, source_url):
    item = bucket.get(name) or {
        "name": name,
        "first_seen": timestamp,
        "seen_count": 0,
        "sources": [],
    }
    item["last_seen"] = timestamp
    item["seen_count"] = int(item.get("seen_count", 0)) + 1
    sources = item.setdefault("sources", [])
    if source_url not in sources:
        sources.append(source_url)
    bucket[name] = item
    return item["seen_count"] == 1


def normalize_loras(value):
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, str):
            name = item.strip()
        elif isinstance(item, dict):
            name = str(item.get("file") or item.get("name") or item.get("model") or "").strip()
        else:
            name = ""
        if name:
            result.append(name)
    return result


def register_current(config, settings, source_url, path):
    timestamp = now_iso()
    registry = load_registry(path)
    registry["updated_at"] = timestamp

    new_models = []
    model = str(settings.get("model") or "").strip()
    if model and update_item(registry["models"], model, timestamp, source_url):
        new_models.append(model)

    new_loras = []
    for lora in normalize_loras(settings.get("loras")):
        if update_item(registry["loras"], lora, timestamp, source_url):
            new_loras.append(lora)

    seen_entry = {
        "seen_at": timestamp,
        "source": source_url,
        "model": model or None,
        "loras": normalize_loras(settings.get("loras")),
        "sampler": settings.get("sampler"),
        "width": settings.get("width"),
        "height": settings.get("height"),
        "steps": settings.get("steps"),
        "guidance_scale": settings.get("guidance_scale"),
        "clip_skip": settings.get("clip_skip"),
    }
    registry["settings_seen"].append(seen_entry)
    registry["settings_seen"] = registry["settings_seen"][-200:]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    return new_models, new_loras, registry


def print_current(settings, source_url):
    fields = (
        ("source", source_url),
        ("model", settings.get("model")),
        ("loras", normalize_loras(settings.get("loras"))),
        ("sampler", settings.get("sampler")),
        ("width", settings.get("width")),
        ("height", settings.get("height")),
        ("steps", settings.get("steps")),
        ("guidance_scale", settings.get("guidance_scale")),
        ("clip_skip", settings.get("clip_skip")),
        ("seed", settings.get("seed")),
    )
    for key, value in fields:
        print(f"{key}: {value}")


def print_registry(registry):
    models = registry.get("models", {})
    loras = registry.get("loras", {})
    print(f"Models ({len(models)}):")
    for name, item in sorted(models.items(), key=lambda kv: kv[0].lower()):
        print(f"- {name} (seen {item.get('seen_count', 0)}x, last {item.get('last_seen')})")
    print()
    print(f"LoRAs ({len(loras)}):")
    for name, item in sorted(loras.items(), key=lambda kv: kv[0].lower()):
        print(f"- {name} (seen {item.get('seen_count', 0)}x, last {item.get('last_seen')})")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Probe Draw Things current settings and keep a local model registry.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    current = subparsers.add_parser("current", help="Show current Draw Things model/settings.")
    current.add_argument("--register", action="store_true", help="Record model and LoRAs in the local registry.")
    current.add_argument("--raw", action="store_true", help="Print raw settings JSON.")
    current.add_argument("--registry", help="Override registry JSON path.")
    current.add_argument("--timeout", type=int, default=5)

    register = subparsers.add_parser("register", help="Probe current settings and update the local registry.")
    register.add_argument("--registry", help="Override registry JSON path.")
    register.add_argument("--timeout", type=int, default=5)

    list_cmd = subparsers.add_parser("list", help="List locally discovered models and LoRAs.")
    list_cmd.add_argument("--registry", help="Override registry JSON path.")
    list_cmd.add_argument("--json", action="store_true", help="Print registry JSON.")

    args = parser.parse_args(argv)
    config = load_config()
    path = registry_path(config, getattr(args, "registry", None))

    try:
        if args.command == "list":
            registry = load_registry(path)
            if args.json:
                print(json.dumps(registry, ensure_ascii=False, indent=2))
            else:
                print_registry(registry)
            return 0

        settings, source_url = current_settings(config, args.timeout)
        if getattr(args, "raw", False):
            print(json.dumps(settings, ensure_ascii=False, indent=2))
        else:
            print_current(settings, source_url)

        if args.command == "register" or getattr(args, "register", False):
            new_models, new_loras, _ = register_current(config, settings, source_url, path)
            print(f"Registry: {path}")
            print(f"New models: {', '.join(new_models) if new_models else '-'}")
            print(f"New LoRAs: {', '.join(new_loras) if new_loras else '-'}")
    except (RuntimeError, OSError, HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
