[English](README.md)

# 工业 AI 运营平台

这是一个面向 **工业事件处理 + 工作流集成 + AI 增强** 的小型参考项目。

它不是单纯的 LLM Demo，而是基于企业软件和工业系统中常见的工程模式进行抽象：事件接入、确定性业务规则、任务/流程集成、数据新鲜度、审计追踪、重试与故障诊断。AI 只是系统中的一层增强能力，而不是核心业务规则和状态流转的控制者。

> 这是一个基于可复用工程模式构建的作品集项目，不包含任何原公司/客户源码，也不包含私有业务数据。

## 项目解决什么问题

```text
工业事件 / 外部系统 Webhook
              |
              v
        幂等事件接入
              |
              v
        数据新鲜度校验
              |
              v
       确定性规则引擎
              |
      +-------+--------+
      |                |
      v                v
 持久化 / 观测      AI 增强处理
                    JSON Schema 校验
                    重试 / Provider 回退
                         |
                         v
                  任务中心 / 工作流
                         |
                         v
                     审计 / Trace
```

## 已实现能力

- FastAPI 事件接入与查询接口
- Python async 异步流水线编排
- 重复事件 / Webhook 幂等处理
- 确定性规则引擎，用于严重等级判断与流程路由
- 使用 Pydantic / JSON Schema 对 LLM 结构化输出进行强校验
- timeout、retry、指数退避和模型 Provider fallback
- 外部任务中心抽象及回调幂等处理
- 根据事件时间动态计算数据新鲜度，而不是保存容易过期的派生值
- 阶段级 Trace / Audit 事件
- PostgreSQL 生产级 Schema 示例
- 使用 `FOR UPDATE SKIP LOCKED` 处理多 Worker 并发抢占
- 不依赖真实 LLM API Key 的确定性自动化测试

## 为什么业务规则和 AI 必须分开

工业系统和企业系统中的阈值、审批、路由和状态流转，通常需要满足三个条件：

1. **结果可重复**
2. **逻辑可解释**
3. **行为可审计**

因此这个项目不会让 LLM 决定固定阈值、严重等级和工作流状态。

LLM 主要负责处理非结构化信息，例如：

- 事件摘要
- 潜在原因分析
- 操作员检查建议
- 非结构化文本提取

而真正影响业务流程的判断，例如：

- 是否达到告警阈值
- 是否需要创建任务
- 任务应该走哪个流程
- 状态是否允许流转

都由确定性代码控制。

这样做还有一个重要收益：后续即使从 Gemini 切换到 OpenAI、阿里云百炼或其他模型，也不会改变系统核心业务行为。

## 关键工程问题

### 1. 重复事件与幂等

工业现场、Webhook、消息队列和第三方系统都可能产生重复请求。

系统首先基于 `event_id` 建立幂等边界：

```text
同一个 event_id 第一次进入
        |
        v
      正常处理

同一个 event_id 再次进入
        |
        v
返回已有状态 / 结果
```

生产环境中可以进一步使用 PostgreSQL Unique Constraint、Redis 或消息队列的 At-least-once 投递机制配合实现。

### 2. 确定性规则引擎

例如设备温度、振动、能源偏差等指标，严重等级判断不应该交给 LLM。

```text
metric/value
     |
     v
deterministic rules
     |
     +--> info
     +--> warning
     +--> high
     +--> critical
```

规则结果决定：

- 是否需要 AI 增强
- 是否需要创建任务
- 后续工作流如何路由

### 3. LLM Structured Output

LLM 输出统一按“不可信外部输入”处理。

```text
LLM response
     |
     v
JSON Schema / Pydantic
     |
   valid?
   /   \
 yes   no
 |      |
 v      v
accept retry / fallback
```

只有完成 Schema 校验的数据才能进入后续流程。

### 4. Retry 与 Provider Fallback

单一模型 Provider 不应该成为整个业务链路的单点故障。

当前实现包含：

- timeout
- retry
- exponential backoff
- provider fallback

后续可以进一步抽象为独立 LLM Gateway，支持 Gemini / OpenAI / 阿里云百炼等多 Provider 路由。

### 5. 数据新鲜度

系统不直接保存“当前是否过期”这类会随时间失真的字段，而是保存原始时间：

```text
event_time
received_at
```

处理或查询时动态计算：

```text
now - event_time > TTL
```

这样可以避免 stale data。

### 6. 任务中心与外部流程

高风险事件可以进入任务中心：

```text
event
  |
  v
rule engine
  |
 high / critical
  |
  v
create task
  |
  v
external workflow
  |
  v
callback
```

回调本身使用独立的 `callback_id`，避免第三方重复通知导致状态重复更新。

### 7. 可观测性与审计

每次事件处理都有独立 `trace_id`。

主要处理阶段包括：

```text
ingest
rules
ai
workflow
pipeline
```

每个阶段记录：

- trace_id
- entity_id
- stage
- status
- timestamp
- detail

生产环境可以进一步接入 Langfuse、OpenTelemetry、ELK / Loki、Prometheus / Grafana 等体系。

## 快速运行

```bash
cd portfolio/industrial-ai-ops-platform

python -m venv .venv
source .venv/bin/activate

pip install -e '.[dev]'

pytest -q
```

启动 API：

```bash
pip install uvicorn

uvicorn industrial_ai_ops.api:app \
  --app-dir src \
  --reload
```

主要接口：

- `POST /events`：接收工业事件
- `GET /events/{event_id}`：查询事件处理结果
- `POST /tasks/callback`：接收任务中心回调
- `GET /healthz`：健康检查

## 当前覆盖的故障场景

| 故障场景 | 当前处理方案 |
|---|---|
| Webhook / 事件重复发送 | 原子化幂等 Claim |
| 遥测数据过期 | 基于 event timestamp 动态计算 freshness |
| LLM 导致固定业务规则漂移 | 独立 deterministic rule engine |
| 模型返回非法 JSON | Schema 校验通过后才能进入业务流程 |
| 模型 / Provider 临时故障 | timeout + retry + fallback |
| 工作流重复回调 | callback idempotency key |
| 线上问题难以定位 | trace_id + 阶段级 audit event |
| 多 Worker 同时抢任务 | PostgreSQL `FOR UPDATE SKIP LOCKED` |

## 后续扩展方向

这个项目目前是核心骨架，后续可以继续发展为完整的企业级 AI 运营系统：

- Redis / PostgreSQL Job Repository
- Outbox Pattern，保证数据库事务与外部通知一致性
- Dead Letter Queue
- 失败任务 Replay / 人工重放
- Langfuse / OpenTelemetry 全链路追踪
- 不同工厂 / 租户的规则配置中心
- Prompt 配置中心
- 多模型 LLM Gateway
- Vue 3 运维控制台
- Trace 查询与故障回放
- K8s / ArgoCD 部署

架构设计说明见 [docs/architecture.md](docs/architecture.md)。

PostgreSQL Schema 示例见 [docs/schema.sql](docs/schema.sql)。
