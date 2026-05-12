# AI 图像生成 Skill: 通用生成流程

此文档定义了在本项目中生成插画的基础流程。

## 1. 核心流程

### 第一步：需求解析

*   识别主体、环境、构图、风格和画幅。
*   明确是否需要横图、竖图、近景、全身或背景细节。

### 第二步：提示词构建

*   使用清晰的主体描述和风格描述。
*   负面提示词应覆盖低画质、畸形、错误手部、文字水印、模糊等常见问题。
*   默认参数可使用：
    *   CFG: `4.5`
    *   Sampler: `Euler a`
    *   Res: `832x1216`
    *   Clip Skip: `2`

### 第三步：推送与生成

*   将生成的 JSON 写入 `local_studio/payload.json`。
*   调用 `.skill/push_to_api.py` 或 `.skill/direct_generate.py` 提交任务。

## 2. 自动化工具

### `.skill/push_to_api.py`

将 `local_studio/payload.json` 推送到本地 Web 服务。

### `.skill/composer.py`

根据用户描述生成基础 payload。

### `.skill/direct_generate.py`

不经过 Web UI，直接向 Draw Things HTTP API 提交任务。
