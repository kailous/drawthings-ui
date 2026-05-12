# Direct Generate Skill: 不经过 Web UI 直接提交生成

此 skill 用于在不打开网页、不操作 Web UI 的情况下，把提示词直接提交到 Draw Things HTTP API。

## 触发方式

当用户说：

- “直接生成……”
- “不用 webui 生成……”
- “通过 skill 提交提示词……”
- “把这个 prompt 直接发给 Draw Things”

优先使用此 skill。

## 工作流

1. 将用户的提示词作为命令参数传给 `.skill/direct_generate.py`。
2. 脚本读取 `config.json` 中的 `draw_things_url`，自动补全 `/sdapi/v1/txt2img` 或 `/sdapi/v1/img2img`。
3. 脚本用默认参数构造 payload，并写入 `local_studio/payload.json`，方便 Web UI 后续查看或复用。
4. 脚本直接 POST 到 Draw Things HTTP API，不经过 `webui/` 页面。
5. 如果 API 返回 base64 图片，脚本保存到 `local_studio/direct_outputs/`。

## 基本命令

```bash
python3 .skill/direct_generate.py "your prompt here"
```

## 常用参数

```bash
python3 .skill/direct_generate.py "your prompt here" \
  --negative "lowres, bad anatomy" \
  --steps 30 \
  --width 832 \
  --height 1216 \
  --cfg-scale 4.5 \
  --sampler "Euler a" \
  --clip-skip 2 \
  --seed -1
```

## 使用现有 payload

```bash
python3 .skill/direct_generate.py --payload-json local_studio/payload.json
```

## 只检查不提交

```bash
python3 .skill/direct_generate.py "your prompt here" --dry-run
```

## 输出位置

- 当前 payload: `local_studio/payload.json`
- 生成图片: `local_studio/direct_outputs/*.png`
- 响应摘要: `local_studio/direct_outputs/*_response.json`

## 隐私约定

`local_studio/` 默认被 `.gitignore` 忽略。不要把生成图、私有提示词、案例归档或响应 JSON 提交到公开仓库。
