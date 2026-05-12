# AI 图像生成 Skill: 指令集与自动化流程

此文档定义了 AI (Antigravity) 在本项目中生成插画的标准作业程序 (SOP)。每当用户要求生成图片时，AI 应遵循此 Skill。

---

## 1. 核心生成逻辑 (The Logic)

### 第一步：需求解析 (Analysis)
*   识别主体角色、动作、环境。
*   确认是否需要符合“幼态 (Preteen)”或“调教日志 (Training Log)”风格。

### 第二步：提示词构建 (Composition)
*   **强制启用 Janku-Mix V5 预设**:
    *   CFG: `4.5` | Sampler: `Euler a` | Res: `832x1216`.
*   **应用去油腻 (De-oiling) 词组**:
    *   Negative: `(plastic skin:1.3), (oily reflection:1.2), makeup`.
*   **注入物理/生理反馈**:
    *   使用 `mixture of fluids`, `muscle tension`, `skin reddening`.
*   **交互权重**: 关键动作权重设为 `1.4 - 1.6`。

### 第三步：推送与生成 (Execution)
*   将生成的 JSON 写入 `studio/payload.json`。
*   调用 `.skill/push_to_api.py` 提交任务。

### 第四步：自检与分析 (Analysis & Archiving)
每次生成后，必须引导用户完成以下闭环：
1.  **预期核对**: 告知用户本次生成的重点（如：混合流体质感、特定形变权重）。
2.  **结果归档**: 询问用户是否满意。若满意，立即调用 `.skill/archiver.py` 进行归档。
3.  **偏差分析**: 
    *   若不满意（坏案例），将其存入 `studio/bad_cases/` 并记录失败原因（如“油腻”、“畸形”）。
    *   分析为何提示词未能达到预期，并在下一次生成中修正权重。

---

## 2. 自动化工具 (The Tools)

### `.skill/push_to_api.py`
将任务推送到生成队列。

### `.skill/composer.py`
AI 提示词作曲家，应用 [KNOWLEDGE_BASE.md](file:///Users/lipeng/Documents/Repository/drawthings-ui/studio/KNOWLEDGE_BASE.md) 规则。

### `.skill/archiver.py`
成功案例的自动化搬运工。

---

## 3. 使用指令 (Usage for AI)

当用户说“生成...”时，AI 执行：
1.  **Compose**: 编写提示词 -> `studio/payload.json`。
2.  **Push**: `python3 .skill/push_to_api.py`。
3.  **Wait & Analyze**: 告知用户预期效果，并等待反馈以进行下一步归档。
