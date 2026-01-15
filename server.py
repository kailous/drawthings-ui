#!/usr/bin/env python3
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse, urlunparse
from urllib.request import Request, urlopen

# --- 配置部分 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAYLOAD_PATH = os.path.join(BASE_DIR, "payload.json")
INDEX_PATH = os.path.join(BASE_DIR, "index.html")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LANG_DIR = os.path.join(BASE_DIR, "lang")

DEFAULT_CONFIG = {
    "draw_things_url": "http://127.0.0.1:3883",
    "history_dir": "/Volumes/AIGC/Output",
    "port": 8080,
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

    env_port = os.getenv("PORT")
    if env_port:
        try:
            config["port"] = int(env_port)
        except ValueError:
            pass

    try:
        config["port"] = int(config.get("port", DEFAULT_CONFIG["port"]))
    except (TypeError, ValueError):
        config["port"] = DEFAULT_CONFIG["port"]

    return config

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

DRAW_THINGS_URL = DEFAULT_CONFIG["draw_things_url"]
HISTORY_DIR = DEFAULT_CONFIG["history_dir"]
PORT = DEFAULT_CONFIG["port"]

def _apply_config(config):
    global DRAW_THINGS_URL, HISTORY_DIR, PORT
    DRAW_THINGS_URL = _normalize_draw_things_url(config.get("draw_things_url"))
    HISTORY_DIR = config.get("history_dir", DEFAULT_CONFIG["history_dir"])
    PORT = config.get("port", DEFAULT_CONFIG["port"])

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

def _history_state():
    if not HISTORY_DIR or not os.path.isdir(HISTORY_DIR):
        return {"enabled": False, "error": "HISTORY_DIR not found", "items": []}
    items = []
    try:
        with os.scandir(HISTORY_DIR) as it:
            for entry in it:
                if entry.is_file() and entry.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    items.append((entry.stat().st_mtime, entry.name))
    except OSError:
        pass
    items.sort(key=lambda x: x[0], reverse=True)
    result = [{"name": name, "url": f"/history/image?name={quote(name)}"} for _, name in items]
    return {"enabled": True, "error": "", "items": result}

def _history_file_path(name):
    if not name or name != os.path.basename(name) or ".." in name:
        return None
    return os.path.join(HISTORY_DIR, name)

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="text/plain; charset=utf-8"):
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return False
        return True

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

        # 强制指定 MIME 类型，防止浏览器不加载 CSS/JS
        if path.endswith(".css") or path.endswith(".js") or path.endswith(".json"):
            file_path = os.path.join(BASE_DIR, path.lstrip("/"))
            if ".." in path: 
                self._send(403, b"Forbidden")
                return

            if os.path.isfile(file_path):
                mime = "text/plain"
                if path.endswith(".css"): mime = "text/css"
                elif path.endswith(".js"): mime = "application/javascript"
                elif path.endswith(".json"): mime = "application/json"
                
                try:
                    with open(file_path, "rb") as f:
                        self._send(200, f.read(), mime)
                except OSError:
                    self._send(500, b"Read Error")
            else:
                self._send(404, b"Not Found")
            return

        if path == "/payload":
            try:
                with open(PAYLOAD_PATH, "rb") as f:
                    self._send(200, f.read(), "application/json; charset=utf-8")
            except FileNotFoundError:
                self._send(404, b"{}")
            return

        if path == "/history":
            state = _history_state()
            self._send(200, json.dumps(state).encode("utf-8"), "application/json")
            return

        if path == "/history/image":
            query = parse_qs(parsed.query)
            name = query.get("name", [""])[0]
            fpath = _history_file_path(name)
            if fpath and os.path.isfile(fpath):
                mime = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
                try:
                    with open(fpath, "rb") as f:
                        self._send(200, f.read(), mime)
                except OSError:
                    self._send(500, b"Read Error")
            else:
                self._send(404, b"Not Found")
            return

        self._send(404, b"Not Found")

    def do_POST(self):
        if self.path != "/generate":
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
    for offset in range(0, 10):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", PORT + offset), Handler)
            print(_t("cli_server_start", {"port": PORT + offset}))
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
