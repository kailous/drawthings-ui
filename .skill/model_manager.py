#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config.json"
DEFAULT_MODELS_DIR = "local_studio/models"
USER_AGENT = "drawthings-ui-model-manager/1.0"
MODEL_EXTENSIONS = (".safetensors", ".ckpt", ".pt", ".pth", ".onnx", ".bin", ".gguf")


def load_config():
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def resolve_path(value, default=DEFAULT_MODELS_DIR):
    raw = str(value or default).strip() or default
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def models_dir(config, override=None):
    return resolve_path(override or os.getenv("MODELS_DIR") or config.get("models_dir"))


def request_json(url, token=None, timeout=30):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def safe_filename(value, fallback="model"):
    text = re.sub(r"[^\w.\-+() ]+", "_", str(value or "").strip())
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or fallback


def human_size(size_kb=None, size_bytes=None):
    size = size_bytes if size_bytes is not None else (size_kb or 0) * 1024
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return str(size)


def civitai_token():
    return os.getenv("CIVITAI_TOKEN") or os.getenv("CIVITAI_API_TOKEN")


def huggingface_token():
    return os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")


def civitai_search(args):
    params = {
        "query": args.query,
        "limit": args.limit,
        "sort": args.sort,
        "period": args.period,
        "nsfw": str(bool(args.include_nsfw)).lower(),
        "primaryFileOnly": "true",
    }
    if args.type:
        params["types"] = args.type
    if args.tag:
        params["tag"] = args.tag
    url = "https://civitai.com/api/v1/models?" + urlencode(params)
    data = request_json(url, civitai_token())
    items = data.get("items", []) if isinstance(data, dict) else []
    for model in items:
        versions = model.get("modelVersions") or []
        version = versions[0] if versions else {}
        files = version.get("files") or []
        primary = next((f for f in files if f.get("primary")), files[0] if files else {})
        print(
            f"[civitai] model={model.get('id')} version={version.get('id')} "
            f"type={model.get('type')} nsfw={model.get('nsfw')} "
            f"downloads={model.get('stats', {}).get('downloadCount')} "
            f"file={primary.get('name') or '-'} size={human_size(primary.get('sizeKB'))}"
        )
        print(f"  {model.get('name')}")
        print(f"  url: https://civitai.com/models/{model.get('id')}")


def civitai_detail(args):
    if args.version_id:
        url = f"https://civitai.com/api/v1/model-versions/{args.version_id}"
    else:
        url = f"https://civitai.com/api/v1/models/{args.model_id}"
    data = request_json(url, civitai_token())
    print(json.dumps(data, ensure_ascii=False, indent=2))


def civitai_version_from_model(model_id):
    data = request_json(f"https://civitai.com/api/v1/models/{model_id}", civitai_token())
    versions = data.get("modelVersions") or []
    if not versions:
        raise ValueError(f"No versions found for Civitai model {model_id}")
    return versions[0]


def is_safe_civitai_file(file_info):
    fmt = str(file_info.get("metadata", {}).get("format") or file_info.get("format") or "").lower()
    pickle_scan = str(file_info.get("pickleScanResult") or "").lower()
    virus_scan = str(file_info.get("virusScanResult") or "").lower()
    name = str(file_info.get("name") or "").lower()
    if name.endswith(".safetensors") or fmt == "safetensor":
        return virus_scan in ("", "success")
    return pickle_scan == "success" and virus_scan in ("", "success")


def choose_civitai_file(files, allow_unsafe=False):
    if not files:
        raise ValueError("No files are available for this model version")
    ordered = sorted(files, key=lambda f: (not f.get("primary"), not str(f.get("name", "")).lower().endswith(".safetensors")))
    for file_info in ordered:
        if allow_unsafe or is_safe_civitai_file(file_info):
            return file_info
    raise ValueError("No safe scanned file found. Re-run with --allow-unsafe only if you trust the source.")


def content_disposition_filename(headers):
    value = headers.get("Content-Disposition")
    if not value:
        return None
    msg = Message()
    msg["Content-Disposition"] = value
    filename = msg.get_param("filename", header="Content-Disposition")
    return filename


def download_url(url, target_dir, filename=None, token=None, timeout=120, dry_run=False):
    target_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    if dry_run:
        print(f"Would download: {url}")
        print(f"Target directory: {target_dir}")
        return None
    with urlopen(req, timeout=timeout) as resp:
        final_name = filename or content_disposition_filename(resp.headers) or Path(resp.url).name or "model"
        final_name = safe_filename(final_name)
        target_path = target_dir / final_name
        tmp_path = target_path.with_suffix(target_path.suffix + ".part")
        total = int(resp.headers.get("Content-Length") or 0)
        written = 0
        with tmp_path.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                written += len(chunk)
                if total:
                    pct = written * 100 / total
                    print(f"\rDownloading {final_name}: {pct:5.1f}% ({human_size(size_bytes=written)})", end="", flush=True)
        if total:
            print()
        tmp_path.replace(target_path)
    print(f"Saved: {target_path}")
    return target_path


def write_metadata(path, metadata):
    meta_path = path.with_suffix(path.suffix + ".json")
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Metadata: {meta_path}")


def civitai_download(args, config):
    if args.version_id:
        version = request_json(f"https://civitai.com/api/v1/model-versions/{args.version_id}", civitai_token())
    elif args.model_id:
        version = civitai_version_from_model(args.model_id)
    else:
        raise ValueError("Civitai download requires --version-id or --model-id")
    files = version.get("files") or []
    file_info = choose_civitai_file(files, args.allow_unsafe)
    download_url_value = file_info.get("downloadUrl") or version.get("downloadUrl")
    if not download_url_value:
        raise ValueError("No download URL found for selected file")
    target_dir = models_dir(config, args.output_dir) / "civitai"
    filename = file_info.get("name") or f"civitai-{version.get('id')}.safetensors"
    saved = download_url(download_url_value, target_dir, filename, civitai_token(), args.timeout, args.dry_run)
    if saved:
        write_metadata(saved, {"provider": "civitai", "version": version, "file": file_info})


def hf_search(args):
    sort = args.sort
    if sort == "Most Downloaded":
        sort = "downloads"
    params = {
        "search": args.query,
        "limit": args.limit,
        "sort": sort,
        "direction": "-1",
        "full": "true",
    }
    if args.filter:
        params["filter"] = args.filter
    url = "https://huggingface.co/api/models?" + urlencode(params)
    data = request_json(url, huggingface_token())
    for model in data if isinstance(data, list) else []:
        siblings = model.get("siblings") or []
        files = [s.get("rfilename") for s in siblings if str(s.get("rfilename", "")).lower().endswith(MODEL_EXTENSIONS)]
        print(
            f"[hf] repo={model.get('modelId')} downloads={model.get('downloads')} "
            f"likes={model.get('likes')} files={len(files)}"
        )
        print(f"  tags: {', '.join((model.get('tags') or [])[:8])}")
        if files:
            print(f"  first model file: {files[0]}")
        print(f"  url: https://huggingface.co/{model.get('modelId')}")


def hf_detail(args):
    repo = quote(args.repo_id, safe="")
    data = request_json(f"https://huggingface.co/api/models/{repo}", huggingface_token())
    print(json.dumps(data, ensure_ascii=False, indent=2))


def choose_hf_file(repo_id, filename=None):
    if filename:
        return filename
    repo = quote(repo_id, safe="")
    data = request_json(f"https://huggingface.co/api/models/{repo}", huggingface_token())
    siblings = data.get("siblings") or []
    files = [s.get("rfilename") for s in siblings if str(s.get("rfilename", "")).lower().endswith(MODEL_EXTENSIONS)]
    safetensors = [f for f in files if str(f).lower().endswith(".safetensors")]
    chosen = (safetensors or files or [None])[0]
    if not chosen:
        raise ValueError("No model-like file found. Provide --filename explicitly.")
    return chosen


def hf_download(args, config):
    if not args.repo_id:
        raise ValueError("Hugging Face download requires --repo-id")
    filename = choose_hf_file(args.repo_id, args.filename)
    revision = args.revision or "main"
    url = f"https://huggingface.co/{args.repo_id}/resolve/{quote(revision, safe='')}/{quote(filename)}"
    target_dir = models_dir(config, args.output_dir) / "huggingface" / safe_filename(args.repo_id.replace("/", "__"))
    saved = download_url(url, target_dir, Path(filename).name, huggingface_token(), args.timeout, args.dry_run)
    if saved:
        write_metadata(saved, {"provider": "huggingface", "repo_id": args.repo_id, "revision": revision, "filename": filename})


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search and download model files into an ignored local directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search models.")
    search.add_argument("query")
    search.add_argument("--provider", choices=("civitai", "huggingface"), default="civitai")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--type", help="Civitai type, e.g. Checkpoint, LORA, Controlnet.")
    search.add_argument("--tag", help="Civitai tag filter.")
    search.add_argument("--include-nsfw", action="store_true", help="Civitai only. Default search uses nsfw=false.")
    search.add_argument("--sort", default="Most Downloaded", help="Civitai sort or Hugging Face sort.")
    search.add_argument("--period", default="AllTime", help="Civitai sort period.")
    search.add_argument("--filter", help="Hugging Face tag/task filter.")

    detail = subparsers.add_parser("detail", help="Print raw model metadata.")
    detail.add_argument("--provider", choices=("civitai", "huggingface"), default="civitai")
    detail.add_argument("--model-id", type=int, help="Civitai model id.")
    detail.add_argument("--version-id", type=int, help="Civitai model version id.")
    detail.add_argument("--repo-id", help="Hugging Face repo id.")

    download = subparsers.add_parser("download", help="Download a selected model file.")
    download.add_argument("--provider", choices=("civitai", "huggingface"), default="civitai")
    download.add_argument("--model-id", type=int, help="Civitai model id. Downloads newest version's selected file.")
    download.add_argument("--version-id", type=int, help="Civitai model version id.")
    download.add_argument("--repo-id", help="Hugging Face repo id.")
    download.add_argument("--filename", help="Hugging Face filename inside the repo.")
    download.add_argument("--revision", default="main", help="Hugging Face revision.")
    download.add_argument("--output-dir", help="Base output directory. Defaults to local_studio/models.")
    download.add_argument("--allow-unsafe", action="store_true", help="Allow files without successful scan metadata.")
    download.add_argument("--timeout", type=int, default=120)
    download.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    config = load_config()
    try:
        if args.command == "search":
            if args.provider == "civitai":
                civitai_search(args)
            else:
                hf_search(args)
        elif args.command == "detail":
            if args.provider == "civitai":
                if not args.model_id and not args.version_id:
                    raise ValueError("Civitai detail requires --model-id or --version-id")
                civitai_detail(args)
            else:
                if not args.repo_id:
                    raise ValueError("Hugging Face detail requires --repo-id")
                hf_detail(args)
        elif args.command == "download":
            if args.provider == "civitai":
                civitai_download(args, config)
            else:
                hf_download(args, config)
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
