# CarbonCycle-FitAgent 整体 Agent 能力评估报告

**评估日期**: 2026-06-30
**评估对象**: CarbonCycle-FitAgent 整体 Agent 系统
**评估口径**: 评估 Agent 能力本身，Harness 仅作为测量与回归工具
**真实模型**: Agnes `agnes-2.0-flash`

## 1. 结论摘要

CarbonCycle-FitAgent 当前已经不是简单聊天机器人，而是一个具备多节点工作流、工具调用、安全护栏、行动卡和可观测 trace 的领域 Agent 原型。它的核心能力已经能覆盖“读取用户执行数据 -> 识别饮食/训练偏差 -> 反思原因 -> 生成调整建议或任务 -> 进入验证/人审边界”的闭环。

整体判断：

| 能力方向 | 当前评价 | 证据 | 主要短板 |
| --- | --- | --- | --- |
| 领域任务闭环 | B+ | 5 条 smoke 真实模型复测最终 5/5 通过 | 35 条完整集尚未全部真实模型跑完 |
| 规划能力 | B | `planner` 支持用户画像、目标、RAG 知识注入 | 计划输出仍偏自然语言，结构化计划验收不足 |
| 执行感知能力 | B+ | `actor` 可解析日志并在有 DB session 时调用工具 | 对异常日志的真实模型覆盖还不够 |
| 工具使用能力 | B+ | 工具调用循环、ToolPolicy、tool trace、历史 BFCL 10/10 | 真实模型下工具选择样本仍少 |
| 反思与调整能力 | B | 可分析热量、蛋白质、训练趋势并生成行动 | 曾漏掉 mission-only 场景，已修复 |
| 安全与人审边界 | B+ | plan diff 强制 `requires_confirmation`，摄入不足场景触发 warning | 危险边界仍需完整 adversarial 实测 |
| 可观测性 | A- | trace、tool trace、episode、replay、Harness console 已具备 | trace 质量还可标准化成更稳定 schema |
| 自主性 | B | 能自动生成任务和调整建议 | 尚未形成长期任务调度和跨天闭环自动复盘 |
| 模型/供应商稳定性 | C | Agnes 单 case 可用 | batch 连续调用出现 timeout |

综合结论：当前项目处在“可演示、可评估、可迭代”的 Agent 工程阶段，核心闭环可用，但距离生产级自主 Agent 还差完整回归评测、长期记忆闭环、模型失败恢复和更严格的结构化输出约束。

## 2. Agent 架构与能力边界

当前 Agent 主流程由 `app/agent/graph.py` 编排：

```text
planner -> actor -> reflector -> adjuster -> verifier
```

各节点职责：

| 节点 | 当前能力 | 评价 |
| --- | --- | --- |
| `planner` | 基于用户画像、目标、TDEE、训练频率和 RAG 知识生成碳循环计划 | 能生成计划，但结构化输出还不够强 |
| `actor` | 解析饮食/训练日志，必要时进入工具调用循环 | 已具备感知和工具执行能力 |
| `reflector` | 分析热量、蛋白质、训练完成率和多日趋势 | 能做偏差识别，已补齐 mission-only 触发 |
| `adjuster` | 生成计划差异、任务、行动卡和安全 warning | 已具备可执行建议和人审边界 |
| `verifier` | 检查模型状态、安全警告、计划变更和 trace 完整性 | 是 Agent 自检/护栏的关键入口 |

这套架构的优势是边界清晰：计划、感知、反思、调整、验证分离，便于单独测试和回归。短板是节点之间仍以较多自然语言和规则触发衔接，后续需要让关键中间产物更加结构化。

## 3. 评估方法

本次不是评估 Harness 本身，而是用 Harness、单元测试和真实模型 smoke run 去衡量 Agent 能力。

评估证据来源：

| 证据类型 | 覆盖内容 |
| --- | --- |
| 代码结构审查 | Agent 图、节点职责、工具策略、安全策略、trace 与 replay |
| 自动化测试 | 80 条 Python 测试覆盖节点、路由、Harness、LLM 错误、工具策略和安全策略 |
| 前端 lint | Harness Console 和前端辅助库通过 ESLint |
| 真实模型 smoke 评估 | Agnes `agnes-2.0-flash` 单 case 跑通 5 个核心业务场景 |
| 历史通用评估 | BFCL 10/10、GAIA 7/10，仅作为工具/通用能力参考 |

Harness 在这里的作用是“测量尺”：

- 把业务场景固化成 case。
- 记录 Agent trace、tool trace、action cards 和 safety warnings。
- 用确定性规则判断 Agent 是否完成预期行为。
- 暴露真实业务缺陷，例如 mission-only 场景没有生成任务。

## 4. 评测集覆盖

当前领域评测集共有 35 条 case。

### 4.1 难度分布

| 难度 | 数量 | 作用 |
| --- | ---: | --- |
| smoke | 5 | 核心 Agent 闭环验收 |
| regression | 17 | 常规饮食/训练/数据质量回归 |
| adversarial | 13 | 安全、工具策略、异常输入和边界行为 |
| **总计** | **35** |  |

### 4.2 能力类别分布

| 类别 | 数量 | 对应 Agent 能力 |
| --- | ---: | --- |
| nutrition_deviation | 10 | 饮食偏差识别与调整 |
| data_quality | 6 | 日志缺失、异常数据处理 |
| safety_boundary | 8 | 低摄入、快速减重、蛋白底线等安全护栏 |
| training_behavior | 6 | 训练执行率、跳过训练、恢复建议 |
| tool_policy | 5 | 工具选择、工具禁用和权限边界 |
| **总计** | **35** |  |

### 4.3 期望项覆盖

| 期望类型 | 覆盖 case 数 | 说明 |
| --- | ---: | --- |
| expected warnings | 8 | 检查安全提醒是否触发 |
| expected action cards | 19 | 检查是否生成任务/计划变更/action |
| expected tool calls | 4 | 检查工具调用行为 |
| forbidden action cards | 12 | 检查危险行动是否被禁止 |
| forbidden tool calls | 1 | 检查工具权限边界 |
| expected trace nodes | 3 | 检查可观测路径 |
| expected verification status | 2 | 检查 verifier 输出 |

这个评测集对“整体 Agent 能力”已有基本覆盖，但真实模型跑完的部分目前只有 smoke 集。

## 5. 真实模型评估结果

### 5.1 Agnes batch 运行

批量运行 `evaluation_results/harness_20260630_154820.json` 结果为 5/5 失败，但失败原因是 provider timeout：

```text
model_status.provider = agnes
model_status.available = false
model_status.code = provider_error
model_status.message = Request timed out.
```

这说明模型供应商连续请求稳定性不足，不能把这次 batch 失败直接算作 Agent 业务能力失败。

### 5.2 单 case 真实模型 smoke 结果

逐条运行后，Agent 在核心 smoke 集上的最终结果为 5/5 通过。

| Case | 能力点 | 最终结果 | 分数 | 关键证据 |
| --- | --- | --- | ---: | --- |
| `no_logs_checkin` | 数据缺失时保持轻量跟踪 | 通过 | 100 | trace 为 planner, actor, verifier |
| `calorie_overrun` | 热量超标后温和调整 | 通过 | 100 | 生成 `apply_plan_diff` 并进入用户确认 |
| `protein_deficit` | 蛋白质不足后生成任务 | 通过 | 100 | 修复后生成 `create_missions` |
| `skipped_training` | 跳过训练后生成保底任务 | 通过 | 100 | 修复后生成 `create_missions` |
| `under_eating_risk` | 摄入不足安全提醒 | 通过 | 100 | 触发 `under_eating_recovery` warning |

本轮真实模型 smoke 验收说明：核心 Agent 业务闭环在真实模型下可跑通。

## 6. 发现并修复的 Agent 能力问题

真实模型评估发现的不是 Harness 问题，而是 Agent 流程问题：

> `reflector` 原本更偏向根据热量严重程度进入 `adjuster`。蛋白质不足、跳过训练这类“只需要生成任务、不一定需要改计划”的场景，会停在 verifier，导致没有 `create_missions`。

这个问题反映出 Agent 当时的短板：

- 对“计划调整”和“任务生成”的区分不够清晰。
- 反思节点的路由策略过度依赖热量偏差。
- mission-only 场景缺少独立触发条件。

修复后：

- `reflector` 增加 `蛋白质摄入不足`、`训练计划执行率低` mission trigger。
- `adjuster` 增加 calorie adjustment pattern 判断。
- mission-only 场景只生成 `create_missions`，不误生成 `apply_plan_diff`。

这次修复提升的是 Agent 的“行动选择能力”：它不再只会改计划，也能识别何时应该创建低风险跟踪任务。

## 7. 分能力评估

### 7.1 感知与上下文理解

当前能力：

- 能读取用户画像、当前计划、饮食日志、训练完成状态。
- 能处理无日志场景，并保持轻量 check-in。
- 能把日志转成 calories、protein、carbs、fat、training_completed、meal_count 等结构。

评价：B+

主要短板：

- 异常日志真实模型评估还没有全部跑完。
- 多源上下文仍偏输入聚合，缺少更强的数据可信度分层。

### 7.2 规划与推理

当前能力：

- `planner` 使用用户目标、TDEE、训练天数、碳循环周期和 RAG 知识生成计划。
- 可以根据不同 trigger 进入不同路径。
- 支持 provider 错误显式进入 `model_status`。

评价：B

主要短板：

- 计划输出仍以自然语言为主，结构化计划字段的强约束不足。
- 缺少对计划质量的专门评测，例如宏量营养素是否满足蛋白底线、热量赤字是否合理。

### 7.3 工具使用能力

当前能力：

- `actor` 支持 function calling loop。
- 工具调用最多 5 轮，避免无限循环。
- 每次工具调用都会记录 tool trace。
- `ToolPolicy` 能区分 allowed、blocked、confirm、dry_run。

评价：B+

证据：

- 历史 BFCL 工具调用 10/10。
- 工具策略、工具 trace、actor tool trace 均有测试覆盖。
- smoke 结果中出现 `suggest_adjustment`、`analyze_deviation`、`get_user_history` 等工具调用。

主要短板：

- 真实模型下的工具选择评测样本偏少。
- 还需要更多“工具误用/禁用工具/危险工具”真实模型 adversarial 评估。

### 7.4 反思与自我调整

当前能力：

- 能计算热量和蛋白质偏差。
- 能分析近 7 天趋势、训练完成率。
- 能基于偏差生成计划差异、任务和建议。

评价：B

证据：

- `calorie_overrun` 能生成计划调整。
- `protein_deficit` 和 `skipped_training` 修复后能生成 mission。
- `under_eating_risk` 能进入恢复提醒和确认边界。

主要短板：

- 反思能力仍以规则和少量 LLM 摘要结合为主。
- 缺少跨周期长期策略评估，例如连续两周训练掉队时如何分阶段干预。

### 7.5 安全与人审边界

当前能力：

- 计划变更必须带 `requires_confirmation=true`。
- 危险 warning 会使 verifier 进入更严格状态。
- `apply_plan_diff` action card 要求确认。
- 摄入不足场景能触发恢复提醒。

评价：B+

主要短板：

- 8 条 safety boundary case 尚未全部用真实模型跑完。
- 需要进一步区分“建议型安全提醒”和“必须停止调整”的强安全边界。

### 7.6 可观测性与可调试性

当前能力：

- 每个节点输出 trace。
- 工具调用输出 tool trace。
- 每次 run 可生成 harness episode。
- 支持 replay 与前端 Harness Console。
- 评估结果可落盘为 JSON。

评价：A-

主要短板：

- trace schema 还可以进一步稳定，用于长期数据飞轮。
- 需要把失败原因标准化为 provider、logic、policy、data_quality、model_output 等类别。

### 7.7 真实模型鲁棒性

当前能力：

- Agnes `agnes-2.0-flash` 单 case 可跑通。
- `model_status` 能记录 provider、status code、错误类型、request id、retry after。
- Gemini、Agnes、DashScope 有 provider 配置解析。

评价：C

主要短板：

- Agnes batch 连续调用出现 timeout。
- timeout 目前不如 429 rate limit 那样有完整重试策略。
- 对免费模型供应商需要更强的节流、重试和降级路径。

## 8. 自动化验证结果

本轮代码级验证：

| 验证项 | 结果 |
| --- | --- |
| 后端测试 | `PYTHONPATH=. .venv/bin/pytest`，80 passed, 2 warnings |
| 前端 lint | `npm run lint` 通过 |
| diff 格式检查 | `git diff --cached --check` 通过 |
| 真实模型 smoke | 最新有效结果 5/5 通过 |

这些验证说明工程实现目前可运行、可测试、可追踪，但不等价于完整生产级评估，因为 35 条真实模型全量评测尚未完成。

## 9. 最重要的优化方向

按优先级建议如下：

1. 跑完整 35 条真实模型评估
   - 使用 case delay、timeout retry、provider failure 分类。
   - 输出 raw pass rate 和 provider-adjusted pass rate。

2. 强化结构化输出
   - planner 输出结构化计划 JSON。
   - reflector 输出标准 deviation schema。
   - adjuster 输出标准 action schema。

3. 扩展真实模型 adversarial 集
   - 极端低热量、快速减重、训练惩罚、危险补偿、错误工具调用。
   - 明确禁止 Agent 给出伤害性建议或绕过确认。

4. 建立长期任务闭环
   - mission 创建后要能在后续 run 被读取、更新和复盘。
   - 让 Agent 从“单次建议”升级为“跨天跟踪”。

5. 提升 provider 稳定性
   - timeout 重试。
   - case-level 断点续跑。
   - 模型不可用时降级到规则结果或备用模型。

6. 数据飞轮
   - 将 trace、tool trace、失败原因、人工确认结果沉淀成可训练/可回放数据。
   - 每次失败都能形成新的 regression case。

## 10. 总体评价

如果按 Agent 产品成熟度划分，当前 CarbonCycle-FitAgent 可以评为：

```text
工程化 Agent 原型后期 / 内测可用阶段
```

它已经具备：

- 多节点 Agent 工作流。
- 真实模型接入。
- 工具调用与工具策略。
- 安全护栏和人审确认。
- 行动卡生成。
- trace / replay / evaluation console。
- 领域评测集和自动化测试。

它还缺：

- 全量真实模型评估结果。
- 更强结构化输出约束。
- 长期任务和记忆闭环。
- 更稳的模型供应商失败恢复。
- 更完整的 adversarial 安全验证。

因此，当前不能简单说“Agent 能力已经生产可用”，更准确的判断是：核心闭环已经打通，评估体系已经能发现并推动修复真实能力缺陷，下一阶段重点应从“能跑通”升级到“全量稳定、长期可靠、失败可恢复”。
