# Model Manager Skill: 搜索和下载模型

此 skill 用于在项目内搜索和下载模型文件。下载内容默认进入 `local_studio/models/`，该目录被 `.gitignore` 忽略。

## 支持来源

- Civitai API
- Hugging Face Hub API

## 搜索 Civitai

```bash
python3 .skill/model_manager.py search "sdxl anime" --provider civitai --type Checkpoint --limit 10
```

默认会传 `nsfw=false`。如确实需要包含 Civitai 标记为 NSFW 的模型，必须显式加：

```bash
--include-nsfw
```

## 搜索 Hugging Face

```bash
python3 .skill/model_manager.py search "stable diffusion" --provider huggingface --limit 10
```

可按标签或任务过滤：

```bash
python3 .skill/model_manager.py search "sdxl" --provider huggingface --filter text-to-image
```

## 查看详情

```bash
python3 .skill/model_manager.py detail --provider civitai --model-id 12345
python3 .skill/model_manager.py detail --provider civitai --version-id 67890
python3 .skill/model_manager.py detail --provider huggingface --repo-id owner/repo
```

## 下载

Civitai:

```bash
python3 .skill/model_manager.py download --provider civitai --version-id 67890
```

Hugging Face:

```bash
python3 .skill/model_manager.py download --provider huggingface --repo-id owner/repo --filename model.safetensors
```

只预览下载目标，不实际下载：

```bash
python3 .skill/model_manager.py download --provider civitai --version-id 67890 --dry-run
```

## 凭据

私有、受限或需要登录的资源可用环境变量提供 token：

- `CIVITAI_TOKEN` 或 `CIVITAI_API_TOKEN`
- `HF_TOKEN` 或 `HUGGINGFACE_TOKEN`

不要把 token 写入仓库。

## 安全约定

- 模型文件默认保存到 `local_studio/models/`。
- 模型文件和下载元数据不应提交到公开仓库。
- Civitai 下载默认优先选择 `.safetensors` 和扫描通过的文件。
- 只有在确认来源可信时才使用 `--allow-unsafe`。
