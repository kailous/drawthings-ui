# Draw Things Probe Skill: 当前模型登记簿

Draw Things 当前本地 HTTP API 不一定暴露“全部已安装模型列表”，但通常可以通过 `/sdapi/v1/options` 或 `/` 获取当前设置。

此 skill 会读取当前 `model` 和 `loras`，并将每次见到的新模型记录到本地登记簿。

## 查看当前设置

```bash
python3 .skill/drawthings_probe.py current
```

## 登记当前模型

```bash
python3 .skill/drawthings_probe.py register
```

或查看同时登记：

```bash
python3 .skill/drawthings_probe.py current --register
```

## 查看已发现模型

```bash
python3 .skill/drawthings_probe.py list
```

输出 JSON：

```bash
python3 .skill/drawthings_probe.py list --json
```

## 数据位置

默认写入：

```text
local_studio/model_registry.json
```

`local_studio/` 默认被 `.gitignore` 忽略，不会上传到公开仓库。
