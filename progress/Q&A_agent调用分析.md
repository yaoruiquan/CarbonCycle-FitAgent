# Agent 调用情况分析

## 问题

> 4个节点连到一起算是1个agent，但是我的功能实现都是利用这一个agent嘛？比如生成计划、记录饮食、分析偏差、写报告、调整策略，这些都是同一个agent完成的嘛？
> 这些功能有没有完整的调用agent能力？

---

## 答案

### Agent 架构

是的，系统只有 **1 个 Agent**，由 4 个节点组成：

```
Planner → Actor → Reflector → Adjuster
   ↓         ↓         ↓           ↓
 计划日程   记录执行   分析偏差   调整策略
```

### 各功能 Agent 调用情况（已更新 2026-02-05）

| 功能 | API 端点 | 是否调用 Agent | 实际使用的服务 |
|------|----------|---------------|---------------|
| ✅ **生成计划** | `POST /api/plans/` | ✅ 是 | `run_agent(trigger=create_plan)` → Planner 节点 |
| ✅ **生成周报** | `POST /api/reports/weekly` | ✅ 是 | `run_agent()` - 完整 4 节点流程 |
| ✅ **触发 Agent** | `POST /api/agent/trigger` | ✅ 是 | `run_agent()` - 完整 4 节点流程 |
| ❌ **重新生成某天** | `POST /api/plans/{id}/days/{date}/regenerate` | ❌ 否 | `PlanEnrichmentService` - 直接调用 LLM |
| ❌ **记录饮食** | `POST /api/logs/` | ❌ 否 | `DatabaseStorage` - 仅数据库操作 |
| ❌ **查看日志统计** | `GET /api/logs/user/{id}/stats` | ❌ 否 | 数据库聚合 |

> [!NOTE]
> **2026-02-05 更新**：计划生成已集成 Agent（方案 B），现在调用 Planner 节点获取 RAG 知识 + AI 建议。

#### ✅ 调用 Agent 的功能

1. **周报生成** (`app/api/report.py`)
   - 调用 `run_agent()` 执行完整的 4 节点流程
   - Planner 分析本周目标
   - Actor 汇总执行数据
   - Reflector 分析偏差趋势，生成 LLM 总结
   - Adjuster 给出调整建议

2. **Agent 触发器** (`app/api/agent.py`)
   - 提供通用的 Agent 触发入口
   - 可从前端/定时任务调用

#### ❌ 未调用 Agent 的功能

1. **生成计划** (`app/api/plan.py`)
   - 使用 `CarbonStrategyService.generate_plan()`
   - 基于 TDEE、目标、体重等参数计算
   - 不涉及 LLM 或 Agent

2. **计划丰富/重新生成某天** (`regenerate_day`)
   - 使用 `PlanEnrichmentService._enrich_day()`
   - 直接调用 LLM 生成训练和饮食描述
   - 绕过 Agent，单独调用 LLM

3. **记录饮食** (`app/api/log.py`)
   - 纯数据库 CRUD 操作
   - 无 LLM 或 Agent 参与

---

## 建议改进

如果希望让更多功能使用 Agent，可以考虑：

### 方案 A：扩展现有 Agent 触发场景

```python
# 在记录饮食后自动触发 Agent 分析
@router.post("/")
async def create_log(log_data: LogCreate, db: ...):
    log = await storage.add_log(log)
    
    # 异步触发 Agent 分析今日偏差
    background_tasks.add_task(
        run_agent,
        user_id=log.user_id,
        trigger="daily_log_recorded",
        ...
    )
    return log
```

### 方案 B：让计划生成调用 Agent

```python
# 在 create_plan 中调用 Agent 的 Planner 节点
result = await run_agent(
    user_id=user_id,
    trigger="create_plan",
    ...
)
# 从 result["planner_output"] 提取计划
```

### 方案 C：保持现状

当前架构是合理的：
- **Agent** 负责复杂的多步骤推理（周报、偏差分析）
- **Service** 负责确定性计算（TDEE、碳循环分配）
- **Database** 负责数据存取（日志、计划CRUD）

这种分层设计是常见的最佳实践。

---

## 结论

| 类别 | 数量 | 说明 |
|------|------|------|
| 调用 Agent | 2 个 | 周报生成、Agent 触发器 |
| 调用 LLM（非 Agent） | 1 个 | 计划丰富服务 |
| 纯规则/数据库 | 6 个 | 计划CRUD、日志CRUD、用户管理等 |

**当前 Agent 主要用于周报反思和复盘**，其他功能使用更轻量的服务或直接数据库操作。
