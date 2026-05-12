# drawthings-ui

A small local Web UI and command-line helper set for submitting JSON payloads to the Draw Things HTTP API.

The project is designed for local use first: generated images, prompt drafts, API responses, and case notes are ignored by Git by default.

## Features

- Browser UI for editing and submitting Draw Things payload JSON.
- Local history browser backed by a configurable output directory.
- Prompt metadata viewer for PNG history images when metadata is available.
- Optional local case rating workflow.
- Direct CLI submission without opening the Web UI.
- Model search and download helper for Civitai and Hugging Face.
- Draw Things current-model probe with a local discovered-model registry.
- LAN address display and optional terminal QR code.

## Quick Start

1. Enable the HTTP API server in Draw Things.
2. Create a local config:

```bash
cp config.example.json config.json
```

3. Adjust `config.json` for your machine.
4. Start the server:

```bash
python3 server.py
```

5. Open:

```text
http://127.0.0.1:8080
```

The default terminal language is Chinese. Use English output with:

```bash
python3 server.py en
```

## Configuration

Only `config.example.json` is committed. Your real `config.json` is ignored so machine paths and private settings do not get uploaded.

```json
{
  "draw_things_url": "http://127.0.0.1:3883",
  "history_dir": "local_studio/history",
  "studio_dir": "local_studio",
  "models_dir": "local_studio/models",
  "lan_ip": "",
  "port": 8080,
  "auto_launch_draw_things": true,
  "draw_things_app_name": "Draw Things",
  "draw_things_startup_wait": 12
}
```

Environment overrides:

- `DRAW_THINGS_URL`
- `HISTORY_DIR`
- `STUDIO_DIR`
- `MODELS_DIR`
- `LAN_IP`
- `PORT`
- `AUTO_LAUNCH_DRAW_THINGS`
- `DRAW_THINGS_APP_NAME`
- `DRAW_THINGS_STARTUP_WAIT`

## Direct Generation

Submit a prompt directly to Draw Things without using the Web UI:

```bash
python3 .skill/direct_generate.py "masterpiece, best quality, scenic landscape"
```

Useful options:

```bash
python3 .skill/direct_generate.py "prompt text" \
  --steps 30 \
  --width 832 \
  --height 1216 \
  --cfg-scale 4.5 \
  --sampler "Euler a" \
  --timeout 900
```

Dry run without submitting:

```bash
python3 .skill/direct_generate.py "prompt text" --dry-run
```

By default, direct generation writes local files under `local_studio/`, which is ignored by Git.

## Model Search And Download

Search Civitai:

```bash
python3 .skill/model_manager.py search "sdxl anime" --provider civitai --type Checkpoint --limit 10
```

Search Hugging Face:

```bash
python3 .skill/model_manager.py search "stable diffusion" --provider huggingface --limit 10
```

Download a selected Civitai model version:

```bash
python3 .skill/model_manager.py download --provider civitai --version-id 123456
```

Download a selected Hugging Face file:

```bash
python3 .skill/model_manager.py download --provider huggingface --repo-id owner/repo --filename model.safetensors
```

Model downloads default to `local_studio/models/`, which is ignored by Git. Use `CIVITAI_TOKEN`, `CIVITAI_API_TOKEN`, `HF_TOKEN`, or `HUGGINGFACE_TOKEN` for resources that require authentication.

## Current Model Registry

Some Draw Things versions do not expose a full installed-model list through the local HTTP API. The project can still record models as they appear in the current settings.

Show the current model and generation settings:

```bash
python3 .skill/drawthings_probe.py current
```

Record the current model and LoRA list:

```bash
python3 .skill/drawthings_probe.py register
```

List locally discovered models:

```bash
python3 .skill/drawthings_probe.py list
```

The registry is stored at `local_studio/model_registry.json`, which is ignored by Git.

## Project Layout

- `server.py`: local HTTP server and Draw Things API proxy.
- `webui/`: browser UI files.
- `.skill/`: local helper scripts and workflow docs.
- `studio/`: public tooling placeholders and feedback-analysis code.
- `local_studio/`: private local payloads, outputs, and archives. This directory is ignored.
- `local_studio/models/`: private downloaded models. This directory is ignored.
- `config.example.json`: public configuration template.
- `config.json`: private local configuration. This file is ignored.

## Privacy Defaults

The following are ignored by default:

- `config.json`
- `local_studio/`
- `models/`
- common model file extensions such as `.safetensors`, `.ckpt`, `.pt`, `.onnx`, `.bin`, and `.gguf`
- `studio/direct_outputs/`
- generated images in `studio/good_cases/` and `studio/bad_cases/`
- Python caches and `.DS_Store`

Do not commit generated images, raw API responses, private prompt drafts, or local case archives to a public repository.

## Troubleshooting

If Draw Things appears to run but no preview appears, check that the configured output/history disk is mounted and writable. External disks can make generation appear stuck if Draw Things cannot write to the target directory.

For a minimal API sanity test, use a small payload:

```bash
python3 .skill/direct_generate.py "masterpiece, best quality, simple landscape" \
  --steps 4 \
  --width 512 \
  --height 512 \
  --timeout 120
```
