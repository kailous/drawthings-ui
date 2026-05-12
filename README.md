# drawthings-ui
Draw Things HTTP API 的web ui，直接提交json参数，省略复杂的配置。

## 配置
服务器参数支持 `config.json`，可配置 API 地址、历史记录路径与端口：

```json
{
  "draw_things_url": "http://127.0.0.1:3883",
  "history_dir": "/Volumes/AIGC/Output",
  "lan_ip": "192.168.1.10",
  "port": 8080,
  "auto_launch_draw_things": true,
  "draw_things_app_name": "Draw Things",
  "draw_things_startup_wait": 12
}
```

`draw_things_url` 可填写完整接口或仅填基础地址（如 `http://127.0.0.1:3883`）。
当请求 payload 中包含 `init_images` 时会自动走 `/sdapi/v1/img2img`，否则走 `/sdapi/v1/txt2img`。

如需临时覆盖，可使用环境变量 `DRAW_THINGS_URL`、`HISTORY_DIR`、`LAN_IP`、`PORT`。
`lan_ip`/`LAN_IP` 可用于手动指定局域网访问地址，避免代理/虚拟网卡导致检测错误。
`auto_launch_draw_things` 会在 macOS 上启动本服务时自动打开 Draw Things，并轮询 HTTP API 是否可用。
注意：目前未发现官方支持从外部命令直接切换 Draw Things App 内 API Server 开关；如果自动打开后仍不可用，需要在 Draw Things 中手动启用 API Server。
可用 `AUTO_LAUNCH_DRAW_THINGS=false` 临时关闭自动打开。

## 项目结构
*   `studio/`: 存放提示词工作资料，包含案例库、知识库、当前生成参数与反馈分析工具。
*   `webui/`: 存放网页前端资源，包含入口页、样式、脚本和语言包。
*   [KNOWLEDGE_BASE.md](file:///Users/lipeng/Documents/Repository/drawthings-ui/studio/KNOWLEDGE_BASE.md): **核心知识库**。包含 Janku V5 调教、进阶提示词工程及修复策略。
*   `.skill/`: 存放 AI 自动化生成与归档指令 ([generate_image.md](file:///Users/lipeng/Documents/Repository/drawthings-ui/.skill/generate_image.md), [archive_case.md](file:///Users/lipeng/Documents/Repository/drawthings-ui/.skill/archive_case.md))。
*   [API.md](file:///Users/lipeng/Documents/Repository/drawthings-ui/API.md): Draw Things HTTP API 接口说明。
*   `studio/good_cases/`: 记录成功的生成案例与分析报告。
*   `studio/bad_cases/`: 记录失败尝试与避坑指南。
*   `studio/payload.json`: 当前使用的提示词参数模板。

## 运行
默认终端输出为中文，可使用 `python3 server.py en` 切换为英文输出。
启动后会显示局域网访问地址，并尝试输出二维码；如需二维码，可安装 `qrcode`（`pip3 install qrcode`）。
