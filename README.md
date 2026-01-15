# drawthings-ui
Draw Things HTTP API 的web ui，直接提交json参数，省略复杂的配置。

## 配置
服务器参数支持 `config.json`，可配置 API 地址、历史记录路径与端口：

```json
{
  "draw_things_url": "http://127.0.0.1:3883/sdapi/v1/txt2img",
  "history_dir": "/Volumes/AIGC/Output",
  "port": 8080
}
```

如需临时覆盖，可使用环境变量 `DRAW_THINGS_URL`、`HISTORY_DIR`、`PORT`。
