# Draw Things HTTP API

> 说明：Draw Things 官方目前没有公开完整的 HTTP API 文档。
> 下面的“已确认接口”来自公开示例与社区信息；
> “A1111 兼容端点”来自 AUTOMATIC1111 的 API 路由清单，仅作参考，是否可用以本机实际返回为准。

## 已确认接口（社区/示例）

- GET `/`
  - 返回当前 Draw Things 的配置/状态（社区示例显示为 JSON）。
- POST `/sdapi/v1/txt2img`
  - 文生图。
- POST `/sdapi/v1/img2img`
  - 图生图。

## A1111 兼容端点（可能支持）

以下清单来自 AUTOMATIC1111 `modules/api/api.py` 的路由定义，Draw Things 可能只实现其中一部分。
功能说明按 A1111 语义整理，仅供参考。

### GET
- `/sdapi/v1/progress`：查询当前生成进度与预览图。
- `/sdapi/v1/options`：获取当前配置项。
- `/sdapi/v1/cmd-flags`：获取启动参数与标志。
- `/sdapi/v1/samplers`：列出采样器。
- `/sdapi/v1/schedulers`：列出调度器。
- `/sdapi/v1/upscalers`：列出放大模型。
- `/sdapi/v1/latent-upscale-modes`：列出潜空间放大模式。
- `/sdapi/v1/sd-models`：列出可用模型（checkpoint）。
- `/sdapi/v1/sd-vae`：列出可用 VAE。
- `/sdapi/v1/hypernetworks`：列出 Hypernetwork。
- `/sdapi/v1/face-restorers`：列出人脸修复模型。
- `/sdapi/v1/realesrgan-models`：列出 RealESRGAN 模型。
- `/sdapi/v1/prompt-styles`：列出提示词样式。
- `/sdapi/v1/embeddings`：列出文本嵌入（embedding）。
- `/sdapi/v1/memory`：查询内存/显存状态。
- `/sdapi/v1/scripts`：列出脚本名称。
- `/sdapi/v1/script-info`：列出脚本参数说明。
- `/sdapi/v1/extensions`：列出扩展信息。

### POST
- `/sdapi/v1/txt2img`：文生图。
- `/sdapi/v1/img2img`：图生图/局部重绘（inpaint）。
- `/sdapi/v1/extra-single-image`：单张图像放大/修复。
- `/sdapi/v1/extra-batch-images`：批量图像放大/修复。
- `/sdapi/v1/png-info`：解析 PNG 元数据（提示词/参数）。
- `/sdapi/v1/interrogate`：图像反推提示词（CLIP/DeepBooru）。
- `/sdapi/v1/interrupt`：中断当前生成任务。
- `/sdapi/v1/skip`：跳过当前生成步骤/任务。
- `/sdapi/v1/options`：更新配置项（持久化）。
- `/sdapi/v1/refresh-embeddings`：刷新 embedding 列表。
- `/sdapi/v1/refresh-checkpoints`：刷新模型列表。
- `/sdapi/v1/refresh-vae`：刷新 VAE 列表。
- `/sdapi/v1/create/embedding`：创建 embedding。
- `/sdapi/v1/create/hypernetwork`：创建 hypernetwork。
- `/sdapi/v1/train/embedding`：训练 embedding。
- `/sdapi/v1/train/hypernetwork`：训练 hypernetwork。
- `/sdapi/v1/unload-checkpoint`：卸载当前模型。
- `/sdapi/v1/reload-checkpoint`：重新加载当前模型。
- `/sdapi/v1/server-kill`：强制结束服务进程。
- `/sdapi/v1/server-restart`：重启服务。
- `/sdapi/v1/server-stop`：停止服务。

## 自查建议

如果你在本机开启了 Draw Things 的 HTTP API，可尝试访问：
- `/docs` 或 `/openapi.json`（若 Draw Things 兼容 FastAPI 文档输出，会返回完整接口）
