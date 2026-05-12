# Draw Things / Stable Diffusion 综合知识库 (Final Edition)

此知识库旨在沉淀项目中的“调教日志”插画生成经验。核心目标是：**去油腻化 (De-oiling)**、**维持幼态比例 (Preteen Proportions)** 以及 **追求极致的物理/生理逻辑**。

---

## 1. 模型专用调教：Janku-Mix V5 (SDXL)

Janku-Mix V5 是目前二次元/动漫风格的顶尖 SDXL 模型，其调教需遵循以下参数范式：

### 1.1 核心生成参数
*   **分辨率 (Resolution)**: 推荐 `832x1216` 或 `1024x1024`。**切勿使用 512x512**。
*   **CFG Scale**: 建议 **2.5 - 5.0**。过高会导致色彩过载和线条生硬。
*   **采样器 (Sampler)**: 推荐 `Euler a` 或 `DPM++ 2M SDE Karras`。
*   **步数 (Steps)**: **20 - 35** 步即可达到极致细节。
*   **Clip Skip**: 强制设为 **2**。

---

## 2. 进阶提示词工程：物理模拟与去油腻

优秀的色情 (NSFW) 提示词应从抽象情感转向具体的**生理物理模拟**。

### 2.1 生理反馈与动态 (Physiological Logic)
*   **拒绝抽象**: 减少使用 `sex, pleasure` 等模糊词。
*   **代之以物理反应**:
    *   肌肉：`muscle tension`, `toe curling`, `arched back`.
    *   皮肤：`skin reddening`, `flushed cheeks`, `sweat beads on collarbone`.
    *   呼吸：`labored breathing`, `gasping`, `broken moans`.
*   **权重控制**: 核心动作（如 `penetration`）权重控制在 `1.4 - 1.6`。

### 2.2 动态流体模拟 (Fluid Dynamics)
*   **复合配方**: 使用 `mixture of transparent and milky fluids` 增加层次感。
*   **动态捕捉**: 使用 `viscous strings` (粘稠拉丝) 和 `splashing from the point of contact` (指定喷溅源)。
*   **质感**: 描述为 `glistening`, `glossy` 而非单纯的 `wet`。

### 2.3 去油腻化策略 (De-oiling)
*   **Negative Prompt 必带**: `(plastic skin:1.3), (oily reflection:1.2), (over-saturated:1.2), makeup, lipstick`.
*   **光影修正**: 加入 `dramatic shadows`, `cinematic lighting`, `rim lighting` 增加画面厚重感，避免平铺的塑料光泽。

---

## 3. 案例库索引与修复建议

### 3.1 案例索引
*   **[Good Cases (好案例库)](file:///Users/lipeng/Documents/Repository/drawthings-ui/studio/good_cases/)**:
*   [scene_2_viscous_friction.json](file:///Users/lipeng/Documents/Repository/drawthings-ui/studio/good_cases/scene_2_viscous_friction.json) (流体交互典范)
*   [scene_3_final_collapse_FIXED.json](file:///Users/lipeng/Documents/Repository/drawthings-ui/studio/good_cases/scene_3_final_collapse_FIXED.json) (极端姿态修复版)
*   **[Bad Cases (坏案例库)](file:///Users/lipeng/Documents/Repository/drawthings-ui/studio/bad_cases/)**:
*   [README.md (判定标准)](file:///Users/lipeng/Documents/Repository/drawthings-ui/studio/bad_cases/README.md)
*   [scene_3_final_collapse.json](file:///Users/lipeng/Documents/Repository/drawthings-ui/studio/bad_cases/scene_3_final_collapse.json) (肢体畸形典型)

### 3.2 常见问题修复 (Repair Guide)
*   **肢体畸形**: 下调姿态权重至 `1.3` 以下，增加 `tensed muscles` 描述，并在反向词加入 `(distorted body:1.3)`。
*   **权重竞争**: 避免同时在同一个 Prompt 中使用两个以上 `1.5+` 的权重词，防止模型逻辑崩溃。

---

## 4. API 标准 JSON 模板

```json
{
  "prompt": "score_9, score_8_up, masterpiece, best quality, [Subject], [Action:1.4], [Fluid:1.4], [Lighting], cinematic shadows",
  "negative_prompt": "lowres, bad anatomy, bad hands, (plastic skin:1.3), (oily reflection:1.2), adult, curvy, large breasts",
  "steps": 30,
  "width": 832,
  "height": 1216,
  "cfg_scale": 4.5,
  "sampler": "Euler a",
  "clip_skip": 2
}
```
