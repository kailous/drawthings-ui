#!/usr/bin/env python3
import ipaddress
import html
import json
import mimetypes
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import zlib
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import sleep as time_sleep
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse, urlunparse
from urllib.request import Request, urlopen

# --- 配置部分 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBUI_DIR = os.path.join(BASE_DIR, "webui")
INDEX_PATH = os.path.join(WEBUI_DIR, "index.html")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
CONFIG_EXAMPLE_PATH = os.path.join(BASE_DIR, "config.example.json")
LANG_DIR = os.path.join(WEBUI_DIR, "lang")

DEFAULT_CONFIG = {
    "draw_things_url": "http://127.0.0.1:3883",
    "history_dir": "local_studio/history",
    "studio_dir": "local_studio",
    "lan_ip": "",
    "port": 8080,
    "auto_launch_draw_things": True,
    "draw_things_app_name": "Draw Things",
    "draw_things_startup_wait": 12,
}

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

DEFAULT_PAYLOAD = {
    "prompt": "masterpiece, best quality, professional anime illustration, soft lighting, detailed background",
    "negative_prompt": "lowres, bad anatomy, bad hands, blurry, text, watermark",
    "steps": 30,
    "width": 832,
    "height": 1216,
    "cfg_scale": 4.5,
    "sampler": "Euler a",
    "clip_skip": 2,
    "seed": -1,
}

CLI_LANG = "zh"
CLI_TEXT = {}

def _parse_cli_lang(argv):
    for arg in argv[1:]:
        if arg in ("en", "zh"):
            return arg
        if arg.startswith("--lang="):
            value = arg.split("=", 1)[1].strip()
            if value in ("en", "zh"):
                return value
    return "zh"

def _load_cli_lang(lang_code):
    path = os.path.join(LANG_DIR, f"{lang_code}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except OSError:
        return {}

def _init_cli_lang(argv):
    global CLI_LANG, CLI_TEXT
    CLI_LANG = _parse_cli_lang(argv)
    CLI_TEXT = _load_cli_lang(CLI_LANG)

def _t(key, params=None):
    text = CLI_TEXT.get(key, key)
    if params:
        for k, v in params.items():
            text = text.replace(f"{{{k}}}", str(v))
    return text

def _safe_preview(value, limit=200):
    if isinstance(value, bytes):
        text = value.decode("utf-8", "replace")
    else:
        text = str(value)
    if len(text) > limit:
        text = text[:limit] + "..."
    return text

def _split_ip_list(value):
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, str):
        return [str(value).strip()]
    return [item.strip() for item in value.replace(",", " ").split() if item.strip()]

def _bool_config(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    return default

def _ipv4_priority(ip):
    try:
        addr = ipaddress.IPv4Address(ip)
    except ipaddress.AddressValueError:
        return None
    if addr.is_loopback or addr.is_unspecified or addr.is_multicast or addr.is_link_local:
        return None
    if ipaddress.IPv4Address("198.18.0.0") <= addr <= ipaddress.IPv4Address("198.19.255.255"):
        return None
    if addr in ipaddress.IPv4Network("192.0.2.0/24") or addr in ipaddress.IPv4Network("198.51.100.0/24") or addr in ipaddress.IPv4Network("203.0.113.0/24"):
        return None
    if addr in ipaddress.IPv4Network("192.168.0.0/16"):
        return 0
    if addr in ipaddress.IPv4Network("10.0.0.0/8"):
        return 1
    if addr in ipaddress.IPv4Network("172.16.0.0/12"):
        return 2
    if addr in ipaddress.IPv4Network("100.64.0.0/10"):
        return 3
    if addr.is_private:
        return 4
    if addr.is_global:
        return 5
    return 6

def _read_cmd_output(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.stdout or ""
    except Exception:
        return ""

def _collect_ips_from_ip():
    exe = shutil.which("ip")
    if not exe:
        return []
    output = _read_cmd_output([exe, "-4", "addr", "show"])
    ips = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("inet "):
            parts = line.split()
            if len(parts) >= 2:
                ips.append(parts[1].split("/")[0])
    return ips

def _collect_ips_from_ifconfig():
    exe = shutil.which("ifconfig")
    if not exe:
        return []
    output = _read_cmd_output([exe])
    ips = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("inet "):
            parts = line.split()
            if len(parts) >= 2:
                ips.append(parts[1])
    return ips

def _collect_candidate_ips():
    ips = []

    def add(ip):
        if ip and ip not in ips:
            ips.append(ip)

    for ip in _split_ip_list(LAN_IP):
        add(ip)

    for host in (("8.8.8.8", 80), ("1.1.1.1", 80)):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(host)
            add(sock.getsockname()[0])
        except OSError:
            pass
        finally:
            try:
                sock.close()
            except Exception:
                pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass

    for ip in _collect_ips_from_ip():
        add(ip)
    for ip in _collect_ips_from_ifconfig():
        add(ip)

    return ips

def _lan_ipv4_list():
    override_ips = _split_ip_list(LAN_IP)
    if override_ips:
        valid_override = []
        for ip in override_ips:
            if _ipv4_priority(ip) is not None:
                valid_override.append(ip)
        if valid_override:
            return valid_override

    candidates = []
    for ip in _collect_candidate_ips():
        priority = _ipv4_priority(ip)
        if priority is None:
            continue
        candidates.append((priority, ip))
    if not candidates:
        return []
    candidates.sort(key=lambda item: (item[0], item[1]))
    ordered = []
    for _, ip in candidates:
        if ip not in ordered:
            ordered.append(ip)
    return ordered

def _print_qr(url):
    try:
        import qrcode  # type: ignore

        qr = qrcode.QRCode(border=2, box_size=1)
        qr.add_data(url)
        qr.make(fit=True)
        for row in qr.get_matrix():
            print("".join("██" if cell else "  " for cell in row))
        return True
    except Exception:
        pass

    exe = shutil.which("qrencode")
    if exe:
        try:
            subprocess.run([exe, "-t", "UTF8", url], check=True)
            return True
        except Exception:
            pass

    return False

def _load_config():
    config = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key, value in data.items():
                if value is not None:
                    config[key] = value
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError):
        print(_t("cli_config_invalid"))

    env_url = os.getenv("DRAW_THINGS_URL")
    if env_url:
        config["draw_things_url"] = env_url

    env_history = os.getenv("HISTORY_DIR")
    if env_history:
        config["history_dir"] = env_history

    env_studio_dir = os.getenv("STUDIO_DIR")
    if env_studio_dir:
        config["studio_dir"] = env_studio_dir

    env_lan_ip = os.getenv("LAN_IP")
    if env_lan_ip:
        config["lan_ip"] = env_lan_ip

    env_port = os.getenv("PORT")
    if env_port:
        try:
            config["port"] = int(env_port)
        except ValueError:
            pass

    env_auto_launch = os.getenv("AUTO_LAUNCH_DRAW_THINGS")
    if env_auto_launch:
        config["auto_launch_draw_things"] = _bool_config(env_auto_launch, DEFAULT_CONFIG["auto_launch_draw_things"])

    env_app_name = os.getenv("DRAW_THINGS_APP_NAME")
    if env_app_name:
        config["draw_things_app_name"] = env_app_name

    env_startup_wait = os.getenv("DRAW_THINGS_STARTUP_WAIT")
    if env_startup_wait:
        try:
            config["draw_things_startup_wait"] = int(env_startup_wait)
        except ValueError:
            pass

    try:
        config["port"] = int(config.get("port", DEFAULT_CONFIG["port"]))
    except (TypeError, ValueError):
        config["port"] = DEFAULT_CONFIG["port"]

    config["auto_launch_draw_things"] = _bool_config(
        config.get("auto_launch_draw_things"),
        DEFAULT_CONFIG["auto_launch_draw_things"],
    )
    try:
        config["draw_things_startup_wait"] = int(config.get("draw_things_startup_wait", DEFAULT_CONFIG["draw_things_startup_wait"]))
    except (TypeError, ValueError):
        config["draw_things_startup_wait"] = DEFAULT_CONFIG["draw_things_startup_wait"]

    return config

def _resolve_local_path(value, default):
    raw = str(value or default).strip()
    if not raw:
        raw = default
    if os.path.isabs(raw):
        return raw
    return os.path.join(BASE_DIR, raw)

def _normalize_draw_things_url(value):
    if not isinstance(value, str):
        return DEFAULT_CONFIG["draw_things_url"]
    raw = value.strip()
    if not raw:
        return DEFAULT_CONFIG["draw_things_url"]
    return raw

def _draw_things_url_for_payload(payload):
    raw = DRAW_THINGS_URL
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw

    path = parsed.path or ""
    is_img2img = isinstance(payload, dict) and bool(payload.get("init_images"))
    endpoint = "img2img" if is_img2img else "txt2img"

    base_path = ""
    trimmed = path.rstrip("/")
    if trimmed in ("", "/"):
        base_path = ""
    elif trimmed.endswith("/sdapi/v1/txt2img"):
        base_path = trimmed[:-len("/txt2img")]
    elif trimmed.endswith("/sdapi/v1/img2img"):
        base_path = trimmed[:-len("/img2img")]
    elif trimmed.endswith("/sdapi/v1"):
        base_path = trimmed
    else:
        return raw

    if not base_path:
        full_path = f"/sdapi/v1/{endpoint}"
    else:
        full_path = f"{base_path}/{endpoint}"

    return urlunparse((parsed.scheme, parsed.netloc, full_path, parsed.params, parsed.query, parsed.fragment))

def _draw_things_probe_url():
    parsed = urlparse(DRAW_THINGS_URL)
    if not parsed.scheme or not parsed.netloc:
        return DRAW_THINGS_URL
    return urlunparse((parsed.scheme, parsed.netloc, "/", "", "", ""))

def _is_local_draw_things_url():
    parsed = urlparse(DRAW_THINGS_URL)
    host = (parsed.hostname or "").lower()
    return host in ("", "localhost", "127.0.0.1", "::1")

def _draw_things_api_reachable(timeout=1.5):
    try:
        req = Request(_draw_things_probe_url(), method="GET")
        with urlopen(req, timeout=timeout):
            return True
    except HTTPError:
        return True
    except (OSError, URLError, ValueError):
        return False

def _launch_draw_things_app():
    if sys.platform != "darwin":
        print(_t("cli_draw_auto_skip_platform"))
        return False
    if not shutil.which("open"):
        print(_t("cli_draw_auto_skip_open"))
        return False
    try:
        subprocess.Popen(["open", "-a", DRAW_THINGS_APP_NAME])
        print(_t("cli_draw_launching", {"app": DRAW_THINGS_APP_NAME}))
        return True
    except Exception as e:
        print(_t("cli_draw_launch_failed", {"error": e}))
        return False

def _ensure_draw_things_available():
    if not AUTO_LAUNCH_DRAW_THINGS:
        return
    if not _is_local_draw_things_url():
        print(_t("cli_draw_auto_skip_remote", {"url": DRAW_THINGS_URL}))
        return
    if _draw_things_api_reachable():
        print(_t("cli_draw_api_ready", {"url": _draw_things_probe_url()}))
        return

    if not _launch_draw_things_app():
        print(_t("cli_draw_api_unavailable", {"url": DRAW_THINGS_URL}))
        return

    wait_seconds = max(0, int(DRAW_THINGS_STARTUP_WAIT))
    for _ in range(wait_seconds * 2):
        if _draw_things_api_reachable():
            print(_t("cli_draw_api_ready", {"url": _draw_things_probe_url()}))
            return
        time_sleep(0.5)
    print(_t("cli_draw_api_not_ready", {"url": DRAW_THINGS_URL}))

DRAW_THINGS_URL = DEFAULT_CONFIG["draw_things_url"]
HISTORY_DIR = _resolve_local_path(DEFAULT_CONFIG["history_dir"], DEFAULT_CONFIG["history_dir"])
STUDIO_DIR = _resolve_local_path(DEFAULT_CONFIG["studio_dir"], DEFAULT_CONFIG["studio_dir"])
PAYLOAD_PATH = os.path.join(STUDIO_DIR, "payload.json")
LAN_IP = DEFAULT_CONFIG["lan_ip"]
PORT = DEFAULT_CONFIG["port"]
AUTO_LAUNCH_DRAW_THINGS = DEFAULT_CONFIG["auto_launch_draw_things"]
DRAW_THINGS_APP_NAME = DEFAULT_CONFIG["draw_things_app_name"]
DRAW_THINGS_STARTUP_WAIT = DEFAULT_CONFIG["draw_things_startup_wait"]

def _apply_config(config):
    global DRAW_THINGS_URL, HISTORY_DIR, STUDIO_DIR, PAYLOAD_PATH, LAN_IP, PORT, AUTO_LAUNCH_DRAW_THINGS, DRAW_THINGS_APP_NAME, DRAW_THINGS_STARTUP_WAIT
    DRAW_THINGS_URL = _normalize_draw_things_url(config.get("draw_things_url"))
    HISTORY_DIR = _resolve_local_path(config.get("history_dir"), DEFAULT_CONFIG["history_dir"])
    STUDIO_DIR = _resolve_local_path(config.get("studio_dir"), DEFAULT_CONFIG["studio_dir"])
    PAYLOAD_PATH = os.path.join(STUDIO_DIR, "payload.json")
    LAN_IP = config.get("lan_ip", DEFAULT_CONFIG["lan_ip"])
    PORT = config.get("port", DEFAULT_CONFIG["port"])
    AUTO_LAUNCH_DRAW_THINGS = config.get("auto_launch_draw_things", DEFAULT_CONFIG["auto_launch_draw_things"])
    DRAW_THINGS_APP_NAME = config.get("draw_things_app_name", DEFAULT_CONFIG["draw_things_app_name"])
    DRAW_THINGS_STARTUP_WAIT = config.get("draw_things_startup_wait", DEFAULT_CONFIG["draw_things_startup_wait"])

def _print_startup():
    line = "=" * 40
    print(line)
    print(_t("cli_title"))
    print(_t("cli_lang", {"lang": CLI_LANG}))
    print(_t("cli_config_path", {"path": CONFIG_PATH}))
    print(_t("cli_draw_url", {"url": DRAW_THINGS_URL}))
    print(_t("cli_history_dir", {"path": HISTORY_DIR}))
    print(_t("cli_port_hint", {"port": PORT}))
    print(line)

def _print_access_info(port):
    print(_t("cli_access_header"))
    print(_t("cli_access_local", {"port": port}))
    ips = _lan_ipv4_list()
    if ips:
        ip = ips[0]
        print(_t("cli_access_lan", {"url": f"http://{ip}:{port}"}))
        if len(ips) > 1:
            extras = ", ".join(f"http://{item}:{port}" for item in ips[1:4])
            print(_t("cli_access_lan_other", {"urls": extras}))
    else:
        print(_t("cli_access_lan_none"))

    url = f"http://{ips[0]}:{port}" if ips else f"http://127.0.0.1:{port}"
    print(_t("cli_qr_label", {"url": url}))
    if not _print_qr(url):
        print(_t("cli_qr_unavailable"))
        print(_t("cli_qr_hint"))

def _history_state():
    if not HISTORY_DIR or not os.path.isdir(HISTORY_DIR):
        return {"enabled": False, "error": "HISTORY_DIR not found", "items": []}
    items = []
    try:
        with os.scandir(HISTORY_DIR) as it:
            for entry in it:
                if entry.is_file() and entry.name.lower().endswith(IMAGE_EXTENSIONS):
                    items.append((entry.stat().st_mtime, entry.name))
    except OSError:
        pass
    items.sort(key=lambda x: x[0], reverse=True)
    result = [
        {
            "name": name,
            "url": f"/history/image?name={quote(name)}",
            "prompt_url": f"/history/prompt?name={quote(name)}",
        }
        for _, name in items
    ]
    return {"enabled": True, "error": "", "items": result}

def _history_file_path(name):
    if not name or name != os.path.basename(name) or ".." in name:
        return None
    return os.path.join(HISTORY_DIR, name)

def _read_png_text_chunks(file_path):
    chunks = []
    try:
        with open(file_path, "rb") as f:
            if f.read(8) != b"\x89PNG\r\n\x1a\n":
                return chunks
            while True:
                header = f.read(8)
                if len(header) < 8:
                    break
                size, chunk_type = struct.unpack(">I4s", header)
                if chunk_type in (b"iTXt", b"tEXt", b"zTXt") and size <= 2_000_000:
                    data = f.read(size)
                    if chunk_type == b"zTXt":
                        try:
                            _, rest = data.split(b"\x00", 1)
                            compressed = rest[1:]
                            chunks.append(zlib.decompress(compressed).decode("utf-8", "replace"))
                        except Exception:
                            pass
                    else:
                        chunks.append(data.decode("utf-8", "replace"))
                else:
                    f.seek(size, os.SEEK_CUR)
                f.seek(4, os.SEEK_CUR)
                if chunk_type == b"IEND":
                    break
    except OSError:
        pass
    return chunks

def _json_objects_from_text(text):
    decoder = json.JSONDecoder()
    clean = html.unescape(text).replace("\x00", " ")
    for match in re.finditer(r"\{", clean):
        try:
            obj, _ = decoder.raw_decode(clean[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj

def _payload_from_metadata_text(text):
    for obj in _json_objects_from_text(text):
        if isinstance(obj.get("c"), str):
            try:
                nested = json.loads(obj["c"])
                if isinstance(nested, dict) and "prompt" in nested:
                    return nested
            except json.JSONDecodeError:
                payload = {"prompt": obj["c"]}
                if isinstance(obj.get("uc"), str):
                    payload["negative_prompt"] = obj["uc"]
                if "steps" in obj:
                    payload["steps"] = obj["steps"]
                if "seed" in obj:
                    payload["seed"] = obj["seed"]
                if "sampler" in obj:
                    payload["sampler"] = obj["sampler"]
                if "scale" in obj:
                    payload["cfg_scale"] = obj["scale"]
                if "clip_skip" in obj:
                    payload["clip_skip"] = obj["clip_skip"]
                if isinstance(obj.get("size"), str):
                    match = re.match(r"^(\d+)x(\d+)$", obj["size"])
                    if match:
                        payload["width"] = int(match.group(1))
                        payload["height"] = int(match.group(2))
                return payload
        if "prompt" in obj:
            return obj
    return None

def _summary_from_metadata_text(text):
    clean = html.unescape(text)
    summary = {}
    patterns = {
        "actual_seed": r"\bSeed:\s*([^,\n<]+)",
        "model": r"\bModel:\s*([^,\n<]+)",
        "size": r"\bSize:\s*([^,\n<]+)",
        "sampler": r"\bSampler:\s*([^,\n<]+)",
        "guidance_scale": r"\bGuidance Scale:\s*([^,\n<]+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, clean)
        if match:
            summary[key] = match.group(1).strip()
    return summary

def _history_prompt_state(name):
    fpath = _history_file_path(name)
    if not fpath or not os.path.isfile(fpath):
        return {"enabled": False, "error": "Image not found", "payload": None, "metadata": {}}
    if not fpath.lower().endswith(".png"):
        return {"enabled": False, "error": "Prompt metadata is only supported for PNG history images", "payload": None, "metadata": {}}

    metadata = {}
    for text in _read_png_text_chunks(fpath):
        payload = _payload_from_metadata_text(text)
        metadata.update(_summary_from_metadata_text(text))
        if payload:
            return {"enabled": True, "error": "", "payload": payload, "metadata": metadata}
    return {"enabled": False, "error": "Prompt metadata not found", "payload": None, "metadata": metadata}

def _safe_case_slug(value, limit=64):
    text = os.path.splitext(os.path.basename(str(value)))[0].lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text).strip("-")
    return (text[:limit].strip("-") or "case")

def _archive_rating_case(name, rating, note):
    if rating not in ("good", "bad"):
        return {"enabled": False, "error": "Invalid rating"}

    fpath = _history_file_path(name)
    if not fpath or not os.path.isfile(fpath):
        return {"enabled": False, "error": "Image not found"}

    prompt_state = _history_prompt_state(name)
    if not prompt_state.get("enabled") or not prompt_state.get("payload"):
        return {"enabled": False, "error": "Prompt metadata not found"}

    target_root = os.path.join(STUDIO_DIR, "good_cases" if rating == "good" else "bad_cases")
    os.makedirs(target_root, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = os.path.join(target_root, f"{timestamp}_{_safe_case_slug(name)}")
    os.makedirs(target_dir, exist_ok=False)

    image_ext = os.path.splitext(fpath)[1].lower() or ".png"
    shutil.copy2(fpath, os.path.join(target_dir, f"result{image_ext}"))

    with open(os.path.join(target_dir, "prompt.json"), "w", encoding="utf-8") as f:
        json.dump(prompt_state["payload"], f, ensure_ascii=False, indent=2)

    feedback = {
        "rating": rating,
        "note": str(note or "").strip(),
        "source_image": name,
        "metadata": prompt_state.get("metadata", {}),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    with open(os.path.join(target_dir, "feedback.json"), "w", encoding="utf-8") as f:
        json.dump(feedback, f, ensure_ascii=False, indent=2)

    return {"enabled": True, "error": "", "dir": os.path.relpath(target_dir, BASE_DIR)}

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="text/plain; charset=utf-8", headers=None):
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if headers:
                for key, value in headers.items():
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return False
        return True

    def _send_file_cached(self, file_path, content_type, cache_seconds):
        try:
            stat = os.stat(file_path)
        except OSError:
            self._send(404, b"Not Found")
            return

        etag = f"\"{stat.st_mtime_ns}-{stat.st_size}\""
        headers = {
            "ETag": etag,
            "Cache-Control": f"public, max-age={cache_seconds}",
        }
        if self.headers.get("If-None-Match") == etag:
            self._send(304, b"", content_type, headers)
            return

        try:
            with open(file_path, "rb") as f:
                body = f.read()
            self._send(200, body, content_type, headers)
        except OSError:
            self._send(500, b"Read Error")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            try:
                with open(INDEX_PATH, "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, b"index.html not found")
            return

        # Only serve allowlisted Web UI asset paths.
        is_webui_asset = (
            path.startswith("/css/") and path.endswith(".css")
            or path.startswith("/js/") and path.endswith(".js")
            or path.startswith("/lang/") and path.endswith(".json")
        )
        if is_webui_asset:
            if ".." in path:
                self._send(403, b"Forbidden")
                return

            file_path = os.path.normpath(os.path.join(WEBUI_DIR, path.lstrip("/")))
            if not file_path.startswith(os.path.abspath(WEBUI_DIR) + os.sep):
                self._send(403, b"Forbidden")
                return

            if os.path.isfile(file_path):
                mime = "text/plain"
                if path.endswith(".css"): mime = "text/css"
                elif path.endswith(".js"): mime = "application/javascript"
                elif path.endswith(".json"): mime = "application/json"
                self._send_file_cached(file_path, mime, cache_seconds=0)
            else:
                self._send(404, b"Not Found")
            return

        if path == "/payload":
            try:
                with open(PAYLOAD_PATH, "rb") as f:
                    self._send(200, f.read(), "application/json; charset=utf-8", {"Cache-Control": "no-store"})
            except FileNotFoundError:
                body = json.dumps(DEFAULT_PAYLOAD, ensure_ascii=False, indent=2).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8", {"Cache-Control": "no-store"})
            return

        if path == "/history":
            state = _history_state()
            self._send(200, json.dumps(state).encode("utf-8"), "application/json", {"Cache-Control": "no-store"})
            return

        if path == "/history/prompt":
            query = parse_qs(parsed.query)
            name = query.get("name", [""])[0]
            state = _history_prompt_state(name)
            status = 200 if state.get("enabled") else 404
            self._send(status, json.dumps(state, ensure_ascii=False).encode("utf-8"), "application/json", {"Cache-Control": "no-store"})
            return

        if path == "/history/image":
            query = parse_qs(parsed.query)
            name = query.get("name", [""])[0]
            fpath = _history_file_path(name)
            if fpath and os.path.isfile(fpath):
                mime = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
                self._send_file_cached(fpath, mime, cache_seconds=86400)
            else:
                self._send(404, b"Not Found")
            return

        self._send(404, b"Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/history/rating":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8", "replace")
                data = json.loads(raw or "{}")
                state = _archive_rating_case(
                    data.get("name", ""),
                    data.get("rating", ""),
                    data.get("note", ""),
                )
                status = 200 if state.get("enabled") else 400
                self._send(status, json.dumps(state, ensure_ascii=False).encode("utf-8"), "application/json", {"Cache-Control": "no-store"})
            except json.JSONDecodeError:
                self._send(400, b"Invalid JSON")
            except FileExistsError:
                self._send(409, b"Case already exists")
            except Exception as e:
                self._send(500, str(e).encode("utf-8"))
                print(_t("cli_server_error", {"error": e}))
            return

        if path != "/generate":
            self._send(404, b"Not Found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", "replace")
            payload_text = raw if raw.strip().startswith("{") else parse_qs(raw).get("payload", [""])[0]
            
            if not payload_text:
                self._send(400, b"Missing payload")
                return

            try:
                json_payload = json.loads(payload_text)
            except json.JSONDecodeError:
                self._send(400, b"Invalid JSON")
                return
            
            target_url = _draw_things_url_for_payload(json_payload)
            req = Request(
                target_url,
                data=json.dumps(json_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(req, timeout=300) as resp:
                    self._send(200, resp.read(), "application/json")
            except HTTPError as e:
                body = e.read() if hasattr(e, "read") else b""
                if not body:
                    body = str(e).encode("utf-8")
                content_type = e.headers.get("Content-Type", "text/plain; charset=utf-8")
                self._send(e.code, body, content_type)
                print(_t("cli_upstream_error", {
                    "code": e.code,
                    "url": target_url,
                    "body": _safe_preview(body),
                }))
            except URLError as e:
                msg = str(e).encode("utf-8")
                self._send(502, msg)
                print(_t("cli_upstream_connect", {"error": e}))
        except Exception as e:
            self._send(500, str(e).encode("utf-8"))
            print(_t("cli_server_error", {"error": e}))

def main():
    _init_cli_lang(sys.argv)
    config = _load_config()
    _apply_config(config)
    _print_startup()
    _ensure_draw_things_available()
    for offset in range(0, 10):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", PORT + offset), Handler)
            actual_port = PORT + offset
            print(_t("cli_server_start", {"port": actual_port}))
            _print_access_info(actual_port)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print(_t("cli_server_stop"))
            finally:
                server.server_close()
            return
        except OSError:
            continue
    print(_t("cli_no_port"))

if __name__ == "__main__":
    main()
