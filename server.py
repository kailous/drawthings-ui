#!/usr/bin/env python3
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

# --- 配置部分 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAYLOAD_PATH = os.path.join(BASE_DIR, "payload.json")
INDEX_PATH = os.path.join(BASE_DIR, "index.html")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "draw_things_url": "http://127.0.0.1:3883/sdapi/v1/txt2img",
    "history_dir": "/Volumes/AIGC/Output",
    "port": 8080,
}

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
        print("Warning: failed to read config.json, using defaults.")

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

_CONFIG = _load_config()
DRAW_THINGS_URL = _CONFIG["draw_things_url"]
HISTORY_DIR = _CONFIG["history_dir"]
PORT = _CONFIG["port"]

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
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
            
            req = Request(
                DRAW_THINGS_URL,
                data=json.dumps(json_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=300) as resp:
                self._send(200, resp.read(), "application/json")
        except Exception as e:
            self._send(500, str(e).encode("utf-8"))

def main():
    for offset in range(0, 10):
        try:
            server = ThreadingHTTPServer(("0.0.0.0", PORT + offset), Handler)
            print(f"Server running at http://127.0.0.1:{PORT + offset}")
            server.serve_forever()
            return
        except OSError:
            continue
    print("Could not find open port")

if __name__ == "__main__":
    main()
