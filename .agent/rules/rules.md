---
trigger: model_decision
description: 开发过程中涉及到那个环节，用哪部分约束
---

# 项目规则（RULES.md）

以下为本仓库必须遵守的最小约束集；目标是保证代码可维护、可复现、便于多人协作。**只包含必要项**，请严格遵守。

---

## 1. 目的

简短说明：本仓库用于实现 **Carbon Cycle Diet Agent**（后端），展示 Agent 架构能力（Planner → Actor → Reflect → Adjust）。
所有实现应以工程可维护性为第一原则。

---

## 2. 技术栈与版本

* Python：**3.12+**
* Web 框架：**FastAPI**
* Agent 编排：**LangGraph**
* 数据校验：**Pydantic**
* 依赖文件：`requirements.txt

---

## 3. 运行与依赖（必要命令）

项目根目录下执行：

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

> 若使用 Poetry 或其他工具，请在 PR 中注明替代命令并保证等效环境。

---

## 4. 代码风格（必须）

* 使用 **type hints**（函数参数与返回值）；
* 所有核心函数/类必须包含简短 **docstring**（说明职责、参数、返回值）；
* 单一职责：**每个模块/文件尽量只包含一类责任**；
* 避免魔法字符串与魔法数字；常量放在模块顶部并以 `UPPER_SNAKE_CASE` 命名；
* 保持代码可读性，函数尽量短（< 80 行）；
* 推荐格式化工具（可选）：`black`, `isort`, `ruff`。提交前请运行格式化。

---

## 5. 目录/模块约束（不可随意变更）

仓库结构为规范版（见 README），**不得随意新增顶级目录或合并已有目录**。
如果确有必要新增结构，需要询问

关键目录职责简述（仅作约束）：

* `app/`：FastAPI 入口、路由、依赖注入、服务适配层（API 层）；
* `agent/`：LangGraph 图与各节点（`planner.py`、`actor.py`、`reflector.py`、`adjuster.py`）；
* `tools/`：工具能力实现（纯业务算法函数，不直接调用 LLM）；
* `memory/`：session/user memory 存取实现；
* `tests/`：单元/集成测试。

---

## 6. Agent 相关约束（必须）

* Agent 架构固定为：**Planner → Actor → Reflector → Adjuster**，节点职责应清晰、可测试；
* **LangGraph 用于编排**，避免把业务逻辑硬编码在路由层（FastAPI）；
* `tools/` 中的函数**不得**直接调用 LLM；若需 LLM，请通过 `llm/`（或专门封装层）进行统一调用和审计；
* 每次 Agent 调用必须产生日志或可审计的决策依据（至少为字符串说明），以便复现/排查。

---

## 7. 测试（必要）

* 新增或修改核心逻辑时必须补充或更新测试（`tests/`）；
* 测试框架：`pytest`；
* 推荐覆盖点：planner 输出格式、actor 行为解析、reflector 偏差判定、adjuster 策略修改；
* CI（可选）：PR 合并前保证测试通过。

---