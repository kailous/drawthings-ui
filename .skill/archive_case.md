# AI 案例归档 Skill: 结果保存与知识沉淀

此文档定义了如何将成功的生成结果归档到项目的案例库中。

---

## 1. 归档流程 (The Workflow)

### 第一步：定位结果 (Locate)
*   读取 `config.json` 中的 `history_dir`。
*   在该目录下找到最新生成的图片文件（通常是最后修改的文件）。

### 第二步：创建归档目录 (Create)
*   根据用户提供的名称或场景描述，在 `local_studio/good_cases/` 下创建一个新的子文件夹。
*   文件夹命名规范：`YYYYMMDD_SceneName`。

### 第三步：文件迁移 (Transfer)
*   将最新生成的图片复制到该文件夹中。
*   将当前的 `local_studio/payload.json` 复制到该文件夹中，重命名为 `prompt.json`。
*   生成一个简短的 `analysis.md`，记录该案例的成功点。

### 第四步：知识同步 (Sync)
*   （可选）在项目文档中添加新条目。

---

## 2. 自动化工具 (The Tools)

### `.skill/archiver.py`
自动执行文件查找、重命名和迁移逻辑的脚本。

---

## 3. 使用指令 (Usage for AI)

当用户说“归档这个案例，命名为 xxx”时，AI 应执行：
1.  **触发脚本**: `run_command` -> `python3 .skill/archiver.py "xxx"`。
2.  **确认归档**: 告知用户文件已移至 `local_studio/good_cases/xxx`。
