# 口述史实时分析 Agent（CrewAI Flows Demo）

模拟"两人对话，一人主讲（叙事零散、缺乏逻辑/文化水平不高）、一人聆听"的场景。
Agent 边"听"边持续完成三件事，并随对话推进不断完善输出：

1. **逻辑梳理**：把主讲人跳跃、混乱的口述整理成结构化的时间线/因果大纲
2. **背景知识生成**：从口述细节推断时代/社会背景，持续生成、细化背景知识笔记
3. **叙事锚定物 + 生图**：识别高频提及的标志性物件，持续完善其图像生成提示词，
   待提示词足够详实后调用生图模型（接口已预留为 stub，实际模型待定）

## 输入方式

当前为"模拟流式"：`data/transcripts/sample_story.json` 中预先准备好的中文口述
文本，按段落顺序逐段送入，模拟实时听写过程。

## 三条流水线的更新策略

- **流水线 A（逻辑大纲）**：每段增量更新；每 5 段做一次轻量整理；每 10 段做一次
  全量重跑（基于完整文本重建，纠正累积偏差）
- **流水线 B（背景知识）**：纯增量，笔记只增不减
- **流水线 C（锚定物 + 提示词）**：每段增量细化；当提示词详实度评分
  `prompt_detail_score >= 0.8` 时触发一次全量重写并调用生图工具（stub）

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env   # 并填入 DEEPSEEK_API_KEY
python -m narrator_flow.main
# 或带延迟模拟实时效果：
python -m narrator_flow.main --delay 1.0
```

需要先将 `src` 加入 `PYTHONPATH`（或以可编辑模式安装）：

```bash
pip install -e .
```

环境要求：Python >= 3.10（建议用 pyenv 安装 3.10.x），因为 crewai 不支持 3.9。

## LLM 配置（当前使用 DeepSeek）

三个 Crew 的 `agents.yaml` 中均配置为 `llm: deepseek/deepseek-chat`，运行前
需在 `.env` 中设置：

```
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

> **关于 `src/narrator_flow/llm_compat.py`**：DeepSeek 的 OpenAI 兼容接口
> 不支持 OpenAI 专属的结构化输出方式
> `client.beta.chat.completions.parse(response_format=<PydanticModel>)`
> （会报错 `This response_format type is unavailable now`）。
> 因此项目里自定义了 `DeepSeekCompatibleLLM`（继承自
> `crewai.llms.providers.openai_compatible.completion.OpenAICompatibleCompletion`），
> 在存在 `output_pydantic`/`output_json` 时改用普通的
> `chat.completions.create(response_format={"type": "json_object"})`，
> 再手动用 Pydantic 模型解析返回的 JSON 文本。各 Crew 的 `@agent` 方法通过
> `llm=get_deepseek_llm()` 使用这个自定义 LLM。
>
> 若想切回 OpenAI（gpt-4o-mini 等原生支持 `beta.parse` 的模型），可以：
> 1. 把各 `agents.yaml` 的 `llm` 改回 `gpt-4o-mini`
> 2. 把各 Crew 中 `llm=get_deepseek_llm()` 的入参去掉（使用 Agent 默认行为读取 yaml 的 llm 配置）
> 3. `.env` 中设置 `OPENAI_API_KEY`

## GUI 调试面板（Streamlit）

为了方便自己测试，提供了一个 Streamlit 页面：

```bash
source .venv/bin/activate
streamlit run src/narrator_flow/app.py
```

启动后浏览器打开 http://localhost:8501，左侧侧边栏可切换两种模式：

- **预制 Demo 播放**：选择 `data/transcripts/` 下的某个示例文件，
  点击「▶ 下一段」逐段播放，或勾选「自动连续播放剩余全部段落」一次性跑完；
  右侧三栏实时展示流水线A（逻辑大纲）/ B（背景知识）/ C（锚点物件+生图提示词）的最新状态，
  并可展开查看每个状态的原始 JSON。
- **自由输入（实时模拟）**：在文本框中手动输入"主讲人刚说的一段话"，
  点击「发送」后立即触发一次三条流水线的实时分析，可以逐句输入，
  模拟真实边听边记的使用场景；"清空对话，重新开始"按钮可重置状态。

两种模式分别使用独立的 `NarratorSession` 实例和输出目录
（`output_gui/demo/`、`output_gui/free/`，均已加入 `.gitignore`），
互不影响，也不会覆盖 CLI demo 产生的 `output/`。

> 注意：每处理一段都会触发3次 DeepSeek 调用（背景/逻辑/锚点），
> 单段耗时通常在1-2分钟，期间页面会显示 spinner 提示。

## 输出

控制台逐段打印三条流水线的进展，同时将最新状态写入：

- `output/logic_outline.json` — 逻辑/时间线大纲
- `output/background_knowledge.json` — 背景知识笔记
- `output/anchor_object.json` — 锚定物 + 图像提示词状态
- `output/generated_images/<物件名>.txt` — 生图结果（当前为 stub 占位文件）

## 项目结构

```
src/narrator_flow/
├── main.py          # CLI 入口（逐段播放 demo，底层用 NarratorSession）
├── app.py           # Streamlit 调试界面（底层用 NarratorSession）
├── state.py         # Pydantic 状态模型
├── streaming.py      # 模拟流式输入（逐段读取 transcript）
├── tools/
│   └── image_gen_tool.py   # 生图工具 stub（待接入真实模型）
├── crews/
│   ├── timeline_crew/      # 流水线A：逻辑大纲
│   ├── background_crew/    # 流水线B：背景知识
│   └── anchor_crew/        # 流水线C：锚定物+提示词
└── streaming_app/          # 流式运行时骨架（async 事件循环 + 背压，不依赖 CrewAI Flow）
    ├── analyzer.py         # 单段分析：gather 并发三条流水线（唯一一份流水线逻辑）
    ├── session.py          # NarratorSession：同步逐段分析封装（GUI/CLI 用）
    ├── coalescing_queue.py # 合并队列（背压核心）
    ├── session_store.py    # 会话状态存储（内存占位）
    ├── worker.py           # 单会话消费循环
    ├── producer.py         # 模拟 ASR 流式输入
    └── run_stream.py       # 流式骨架 CLI 入口
```

> 注：原先编排三条流水线的 `flow.py`（CrewAI `Flow` 子类）已移除。它的流水线逻辑
> 与 `streaming_app/analyzer.py` 重复，且 `Flow` 的"一次 kickoff 跑完一张 DAG"模型
> 不适合无界流式场景。现在 CLI、GUI、流式服务三个入口**共用同一份** `analyzer.py`
> 的分析逻辑：交互式场景（CLI/GUI）经 `NarratorSession` 同步调用，真实流式经
> `worker` + `coalescing_queue` 异步调用。

## 运行示例（18段示例文本，DeepSeek）

跑完 `data/transcripts/sample_story.json` 的全部18段后，三条流水线的最终结果示例：

- **流水线A（逻辑大纲）**：整理出 15 个时间线事件，8 条待澄清线索
  （`open_threads`），覆盖知青下乡、包产到户、拖拉机购置等多个时期，
  并按"每5段轻量整理、每10段全量重跑"的节奏多次更新。
- **流水线B（背景知识）**：年代估计收敛为
  "20世纪70年代末至80年代末中国农村（家庭联产承包责任制推行初期至中期）"，
  置信度 0.98，累积 8 条背景笔记（拖拉机、记工分、知青下乡、粮票、人民公社、
  辘轳水井、包产到户、农机情感价值），笔记数量随对话单调递增、从不删减。
- **流水线C（锚定物 + 生图）**："大槐树"被提及 10 次，描述属性累积到 14 条
  （树皮裂纹、石桌、喜鹊窝、四季变化等），`prompt_detail_score` 达到 0.9
  （>= 0.8 阈值），触发全量提示词重写并调用 stub 生图工具，生成
  `output/generated_images/大槐树.txt`。

> 注：`output/` 目录已加入 `.gitignore`，不会提交到仓库；运行一次 demo 后即可
> 在本地查看 `output/*.json` 与 `output/generated_images/` 的完整内容。

## 流式运行时骨架（streaming_app）

> 要做成**真正能在流式场景里走的产品**，CrewAI `Flow` 的"一次 kickoff 跑完一张
> DAG"模型并不合适：真实输入是无界的 ASR 流，且单段分析要 1-2 分钟，与亚秒级
> 的上游存在 100 倍以上的吞吐错配。为此用 `src/narrator_flow/streaming_app/` 取代了
> 原先基于 `Flow` 的编排，用一个 async 事件循环统一"输入 / 并发 / 服务"三个模型，
> **保留 CrewAI 的 Crew、去掉 Flow 这层编排壳**。`analyzer.py` 是唯一一份流水线逻辑，
> CLI / GUI 经 `NarratorSession` 同步复用，真实流式经 `worker` + 队列异步复用。

主干数据流：

```
producer(模拟ASR) ──▶ CoalescingQueue ──▶ SessionWorker ──▶ SessionStore
                       (合并/背压)            │
                                        Analyzer.analyze
                                        └─ asyncio.gather(背景, 逻辑, 锚点)
```

模块划分：

| 文件 | 作用 |
|---|---|
| `coalescing_queue.py` | **背压核心**：有界队列，worker 忙时堆积的片段在下次取用时合并成一段，把"分析次数"与"上游速率"解耦 |
| `session_store.py` | 会话状态存储（当前为内存占位，`load`/`save` 接口按可换 Redis/PG 设计） |
| `analyzer.py` | 单段分析：`ingest` + `asyncio.gather` 并发三条流水线，每个 Crew 用 `asyncio.to_thread` 跑在线程里 |
| `worker.py` | 单会话消费循环，单段失败不拖垮整个会话 |
| `producer.py` | 模拟 ASR：读预录 transcript，按句末标点切成亚秒级片段推入队列 |
| `run_stream.py` | CLI 入口，把以上接成一条主干 |

运行：

```bash
source .venv/bin/activate
python -m narrator_flow.streaming_app.run_stream                 # 真实 DeepSeek 流水线
python -m narrator_flow.streaming_app.run_stream --segment-delay 0.02   # 调小间隔以加剧背压
```

背压效果（离线烟测，用桩流水线）：上游 40 个亚秒级片段，最终只触发 4 段分析
（分别合并自 1/14/14/11 个片段）——上游再快，只是让单段合并得更长，而不会排起
一条每个等 1-2 分钟的长队。

## 待办

`streaming_app` 已经把"流式 + 背压 + 并发"的主干跑通，剩下几处仍是占位/凑合，
按优先级：

- **会话存储落地**：把 `InMemorySessionStore` 换成 Redis/Postgres（`load`=反序列化、
  `save`=序列化），实现断点续接，避免进程崩溃丢状态（接口已留好，worker 不用改）
- **修订/合并改后台任务**：把"每5段轻整理、每10段全量重跑"从 worker 主循环抽成
  独立后台任务，并引入摘要/向量检索，避免 `full_transcript_text` 随对话无限变长
- **多会话并发**：会话注册表管理多个 `SessionWorker` + 带限流的共享 LLM 客户端池
- **FastAPI / WebSocket 服务化**：producer 换成 WS 收流、`on_update` 换成 WS 推回
  （骨架已是 async 事件循环，可直接套上）
- **真实音频流 / ASR 输入**：把 `producer.py` 的模拟 ASR 换成真实 ASR 引擎
- **接入真实生图模型**（DALL-E / Stable Diffusion 等），替换 `image_gen_tool.py` 中的 stub

### 记忆/状态管理（当前为纯内存、单次会话）

当前 `NarratorFlowState` 只存在于内存中的单个 flow 实例里，重启进程/刷新
Streamlit 页面即丢失；`output/`、`output_gui/` 下的 JSON 只是运行结束后的
快照，不会被重新加载续接。后续可以考虑：

- 把 `NarratorFlowState` 定期序列化到磁盘/数据库，支持"加载已有state继续对话"
- 给 `background.notes`、`logic_outline.events` 加摘要/合并机制，避免随对话
  增长导致 prompt 无限变长
- 用向量库存储历史细节，按需检索相关片段，而不是每次把全量状态/全文塞进 prompt
- 支持多用户/多会话并发（当前为单实例单状态）
