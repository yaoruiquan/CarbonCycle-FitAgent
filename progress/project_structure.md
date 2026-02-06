# CarbonCycle-FitAgent 项目目录结构详解

## 📁 项目根目录概览

```
CarbonCycle-FitAgent/
├── app/                    # 🔧 后端核心代码 (FastAPI + LangGraph Agent)
├── frontend/               # 🎨 前端代码 (Next.js + React)
├── data/                   # 💾 数据存储 (SQLite + 向量库 + 知识库)
├── tests/                  # 🧪 测试套件
├── progress/               # 📝 项目进展记录
├── .env                    # 环境变量配置
├── run_api.py              # 后端启动入口
├── requirements.txt        # Python 依赖
├── Dockerfile              # 容器化配置
└── docker-compose.yml      # 多服务编排
```

---

## 🔧 `app/` - 后端核心 (Python/FastAPI)

这是整个系统的大脑，包含 API 接口、Agent 逻辑、数据库操作等。

### 📂 `app/main.py`
- **作用**: FastAPI 应用入口
- **功能**: 
  - 创建 FastAPI 实例
  - 配置 CORS 中间件
  - 注册所有 API 路由 (`/api/*`)
  - 管理应用生命周期 (启动/关闭时的资源初始化与清理)

---

### 📂 `app/api/` - RESTful API 层
对外暴露的所有 HTTP 接口。

| 文件 | 路由前缀 | 功能 |
|------|----------|------|
| `user.py` | `/api/users` | 用户 CRUD (创建、查询、更新、删除) |
| `plan.py` | `/api/plans` | 碳循环计划管理 (生成、查询、更新) |
| `log.py` | `/api/logs` | 饮食日志记录与查询 |
| `agent.py` | `/api/agent` | Agent 触发与对话接口 |
| `health.py` | `/api/health` | 健康检查端点 |
| `report.py` | `/api/reports` | 周报生成 |
| `auth.py` | `/api/auth` | 认证相关 (预留) |
| `storage.py` | - | 内存/数据库存储抽象层 |

**关键关系**:
- `api/*.py` → 调用 `services/*.py` 处理业务逻辑
- `api/*.py` → 通过 `storage.py` 获取数据持久层

---

### 📂 `app/agent/` - LangGraph 智能体
这是系统的"智能大脑"，基于 LangGraph 实现 **Planner → Actor → Reflector → Adjuster** 工作流。

| 文件 | 作用 |
|------|------|
| `graph.py` | 定义状态图 (StateGraph)，编排节点顺序和条件分支 |
| `state.py` | 定义 `AgentState` TypedDict，作为节点间传递的状态容器 |
| `router.py` | 条件路由函数 (`should_adjust`, `should_continue_to_reflect`) |
| `nodes/` | 各节点实现 |

#### `app/agent/nodes/` - 节点实现
| 文件 | 节点名 | 职责 |
|------|--------|------|
| `planner.py` | Planner | 分析用户状态，生成初步建议 |
| `actor.py` | Actor | 执行具体动作 (如更新计划) |
| `reflector.py` | Reflector | 反思执行结果，评估是否需要调整 |
| `adjuster.py` | Adjuster | 根据反思结果微调计划 |

**工作流示意**:
```
用户触发 → Planner → Actor → [条件] → Reflector → [条件] → Adjuster → END
                                ↓                         ↓
                               END                       END
```

---

### 📂 `app/models/` - 数据模型 (Pydantic)
定义所有业务实体的数据结构。

| 文件 | 模型 |
|------|------|
| `user.py` | `UserProfile`, `UserCreate`, `UserUpdate` |
| `plan.py` | `DayPlan`, `CarbonCyclePlan`, `PlanCreate`, `PlanUpdate` |
| `log.py` | `DietLog`, `LogCreate`, `MacroNutrients` |
| `report.py` | `WeeklyReport`, `ReportSummary` |

**关键关系**:
- `models/*.py` ← 被 `api/*.py` 用于请求/响应验证
- `models/*.py` ← 被 `db/models.py` 映射为 ORM 实体

---

### 📂 `app/services/` - 业务服务层
封装核心业务逻辑，被 API 和 Agent 调用。

| 文件 | 职责 |
|------|------|
| `carbon_strategy.py` | 碳循环策略计算 (TDEE, 宏量分配, 日类型安排) |
| `execution_analysis.py` | 执行情况分析 (对比计划 vs 实际摄入) |
| `adjustment_engine.py` | 计划调整引擎 (根据执行偏差生成调整建议) |
| `plan_enrichment.py` | 计划丰富 (为每日计划添加具体训练/饮食建议) |
| `report_service.py` | 周报生成服务 |
| `knowledge_service.py` | 知识库检索服务 (RAG) |

**关键关系**:
- `services/*.py` ← 被 `agent/nodes/*.py` 调用
- `services/*.py` → 调用 `llm/client.py` 进行大模型推理

---

### 📂 `app/llm/` - 大语言模型集成
| 文件 | 作用 |
|------|------|
| `client.py` | LLM 客户端封装 (支持 Qwen/OpenAI API) |
| `tools.py` | LangGraph Tool 定义 (如 `get_user_plan`, `update_plan`) |

---

### 📂 `app/db/` - 数据库层
| 文件 | 作用 |
|------|------|
| `models.py` | SQLAlchemy ORM 模型 (User, Plan, Log 表定义) |
| `db_storage.py` | 数据库存储实现 (实现 `StorageInterface`) |
| `repositories/` | Repository 模式实现 |

#### `app/db/repositories/`
| 文件 | 职责 |
|------|------|
| `user_repo.py` | 用户数据 CRUD |
| `plan_repo.py` | 计划数据 CRUD |
| `log_repo.py` | 日志数据 CRUD |

---

### 📂 `app/memory/` - 记忆模块
| 文件 | 作用 |
|------|------|
| `agent_memory.py` | Agent 运行时记忆 (对话历史, 上下文) |
| `user_memory.py` | 用户长期记忆 (偏好, 历史模式) |

---

### 📂 `app/rag/` - RAG 检索增强
| 文件 | 作用 |
|------|------|
| `retriever.py` | 文档检索器 (结合向量检索 + BM25) |
| `vectorstore.py` | Qdrant 向量存储封装 |
| `embedding.py` | 文本向量化 (使用 DashScope 或本地模型) |

---

### 📂 `app/prompts/` - 提示词模板
| 文件 | 用途 |
|------|------|
| `planner.txt` | Planner 节点的系统提示词 |
| `reflect.txt` | Reflector 节点的系统提示词 |
| `adjust.txt` | Adjuster 节点的系统提示词 |
| `report.txt` | 周报生成提示词 |

---

### 📂 `app/core/` - 基础设施
| 文件 | 作用 |
|------|------|
| `config.py` | 配置管理 (从 `.env` 读取) |
| `database.py` | 数据库连接池管理 |
| `logging.py` | 日志配置 |
| `scheduler.py` | 定时任务 (如每日计划生成) |
| `security.py` | 安全相关 (密码哈希等) |

---

## 🎨 `frontend/` - 前端 (Next.js)

```
frontend/
├── src/
│   ├── app/                # Next.js App Router 页面
│   │   ├── page.tsx        # Dashboard 仪表盘
│   │   ├── strategy/       # 策略页
│   │   ├── planner/        # 复盘页
│   │   ├── chat/           # AI 对话页
│   │   ├── onboarding/     # 引导页
│   │   ├── layout.tsx      # 全局布局 (导航栏)
│   │   └── globals.css     # 全局样式
│   ├── components/         # React 组件
│   │   ├── DayDetailModal.tsx  # 每日详情弹窗
│   │   ├── ui/             # shadcn/ui 基础组件
│   │   └── providers/      # Context Providers
│   └── lib/                # 工具库
│       ├── api.ts          # API 客户端 (fetch 封装)
│       ├── types.ts        # TypeScript 类型定义
│       ├── storage.ts      # localStorage 工具
│       └── context/        # React Context
├── public/                 # 静态资源
├── tailwind.config.ts      # Tailwind CSS 配置
└── package.json            # 依赖配置
```

**前后端连接**:
- `frontend/src/lib/api.ts` → `http://localhost:8000/api/*`

---

## 💾 `data/` - 数据存储

| 路径 | 作用 |
|------|------|
| `carboncycle.db` | SQLite 数据库主文件 |
| `knowledge/` | RAG 知识库 (Markdown 文档) |
| `qdrant/` | Qdrant 向量数据库存储 |
| `sample_logs.json` | 示例饮食日志 |
| `seed_users.json` | 种子用户数据 |

---

## 🧪 `tests/` - 测试套件

| 文件 | 覆盖范围 |
|------|----------|
| `test_api.py` | API 接口测试 |
| `test_agent_e2e.py` | Agent 端到端流程测试 |
| `test_services.py` | 服务层单元测试 |
| `test_strategy.py` | 碳循环策略算法测试 |
| `test_persistence.py` | 数据库持久化测试 |
| `init_db.py` | 数据库初始化脚本 |
| `init_knowledge_base.py` | 知识库初始化脚本 |

---

## 🔗 模块间关系总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │Dashboard│  │Strategy │  │ Planner │  │  Chat   │             │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘             │
└───────┼────────────┼────────────┼────────────┼──────────────────┘
        │            │            │            │
        └────────────┴────────────┴────────────┘
                           │
                     HTTP (REST API)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     app/api/                              │   │
│  │  user.py | plan.py | log.py | agent.py | health.py       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                      │
│              ┌────────────┴────────────┐                        │
│              ▼                         ▼                        │
│  ┌───────────────────┐      ┌───────────────────┐              │
│  │   app/services/   │      │    app/agent/     │              │
│  │ carbon_strategy   │      │   LangGraph FSM   │              │
│  │ execution_analysis│◄────►│ Planner→Actor→   │              │
│  │ adjustment_engine │      │ Reflector→Adjuster│              │
│  └─────────┬─────────┘      └─────────┬─────────┘              │
│            │                          │                         │
│            ▼                          ▼                         │
│  ┌───────────────────┐      ┌───────────────────┐              │
│  │     app/db/       │      │     app/llm/      │              │
│  │   SQLAlchemy ORM  │      │    Qwen API       │              │
│  └─────────┬─────────┘      └───────────────────┘              │
│            │                                                     │
└────────────┼─────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        data/                                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                 │
│  │ SQLite DB  │  │   Qdrant   │  │ Knowledge  │                 │
│  │(users,plans│  │ (vectors)  │  │ (markdown) │                 │
│  │  logs)     │  │            │  │            │                 │
│  └────────────┘  └────────────┘  └────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 启动流程

1. **后端**: `python run_api.py`
   - 初始化数据库 (`init_db`)
   - 启动 FastAPI 服务 (`:8000`)
   
2. **前端**: `cd frontend && npm run dev`
   - 启动 Next.js 开发服务器 (`:3000`)

3. **完整体验**:
   - 访问 `http://localhost:3000/onboarding` 创建用户
   - 系统自动生成碳循环计划
   - 在 Dashboard 查看和编辑每日计划
