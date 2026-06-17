# 代际记忆桥梁 · Generation Memory Bridge

> 一个"边听边理解"的 AI：在长辈口述往事时，实时把零散、跳跃的讲述整理成
> 时间线，补全时代背景，并把反复提及的"记忆锚点"还原成画面。

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-prototype-orange)

📄 **想了解产品思路**（用户、竞品、AI 风险、成功指标、关键决策）？
见 **[产品简报 docs/product-brief.md](./docs/product-brief.md)**。

---

## 为什么做这个

很多家庭里，长辈的人生记忆是最珍贵、也最容易永久流失的东西。但真实的口述往往：

- **零散、跳跃**——想到哪说到哪，时间线是乱的；
- **缺乏背景**——"那年生产队……"，可那是哪一年？什么社会环境？听的人未必懂；
- **稍纵即逝**——讲过一次，细节就散落在几小时的录音里，没人会再去逐字回听。

市面上的录音转写工具只解决了"**记录**"，没有解决"**理解**"。它给你一堆逐字稿，
但不会替你把混乱的讲述**梳理成能读、能传、能看见**的记忆。

**代际记忆桥梁**想填补的就是这一步：让 AI 像一个有耐心、懂历史、还会画画的
倾听者，在长辈讲述的**同时**，一点点把记忆整理、还原出来。

---

## 它能做什么

边听边并行完成三件事，并随讲述推进持续完善：

| 能力 | 解决的问题 | 产出 |
|---|---|---|
| 🧩 **逻辑梳理** | 讲述跳来跳去、没有时间线 | 把零散口述重建成结构化的**时间线 / 因果大纲**，并标记"待澄清线索" |
| 📚 **背景还原** | 细节背后的时代/社会语境缺失 | 从只言片语推断**年代与社会背景**，持续生成背景知识笔记（带置信度） |
| 🖼️ **记忆可视化** | 珍贵的记忆只是文字，看不见 | 识别反复提及的**标志性物件**，逐步完善描述，最终生成一张图把它"画出来" |

> 三件事是**同时进行**的——讲述者不必停顿，AI 在后台持续整理、修订、补全。

---

## 看一眼效果

以一段"农村长辈回忆 1970–80 年代"的口述（18 段）为例，跑完后 AI 的产出：

- **时间线**：整理出 15 个事件、8 条待澄清线索，覆盖知青下乡、记工分、包产到户、
  购置拖拉机等多个时期，并在讲述中多次自我修订。
- **背景还原**：年代估计收敛为"20 世纪 70 年代末至 80 年代末中国农村（家庭联产
  承包责任制推行初期至中期）"，置信度 0.98，累积 8 条背景笔记。
- **记忆锚点**：识别出讲述者反复提到的"**大槐树**"（提及 10 次），逐步攒出 14 条
  视觉细节（树皮裂纹、树下石桌、喜鹊窝、四季变化……），细节足够后自动触发生图。

<!-- 演示 GIF / 截图放这里（见「路线图」P1）。建议录一段 Streamlit 界面逐段播放
     "大槐树"故事、右侧三栏实时填充的过程，约 20–30 秒。 -->
> 📺 **演示动图待补**：推荐录制 Streamlit 调试界面逐段播放、三栏实时更新的过程
> （见下方「在线调试界面」）。这是本项目最直观的展示，也是路线图里的下一步。

---

## 快速开始

环境要求：Python ≥ 3.10（`crewai` 不支持 3.9，建议用 pyenv 安装 3.10.x）。

```bash
pip install -r requirements.txt
pip install -e .                 # 以可编辑模式安装（把 src 加入路径）
```

### 🆓 免 key 试用（无需 API key、零成本）

不想配 key、不想花钱，只想看看效果？用**回放模式**——它逐段播放预录的分析结果，
不调用任何 LLM，体验和真实运行完全一致：

```bash
python -m narrator_flow.main --demo
```

### 接入真实 AI 运行

```bash
cp .env.example .env             # 在 .env 中填入 DEEPSEEK_API_KEY
python -m narrator_flow.main             # 逐段播放示例口述并实时分析
python -m narrator_flow.main --delay 1.0 # 加延迟，更接近真实听写节奏
```

体验真正的"流式 + 背压"运行时（默认 SQLite 持久化，可断点续接；加 `--demo` 同样免 key）：

```bash
python -m narrator_flow.streaming_app.run_stream
```

### 🎙️ 真实语音输入（可选）

用本地 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) 把**录音**转成文字再分析，
全程离线、不需要额外的 API key（首次运行会自动下载语音模型）：

```bash
pip install -e ".[asr]"     # 安装 ASR 可选依赖（与核心依赖分离，按需安装）
python -m narrator_flow.streaming_app.run_stream --audio 你的录音.wav --asr-model small
```

> 🇨🇳 **国内网络下载模型超时？** faster-whisper 默认从 huggingface.co 下载模型，
> 国内常连不上。设置镜像后重试即可（只需一次，模型会缓存到本地）：
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> ```

> 没有现成录音？macOS 可一行生成测试音频：
> `say -v Tingting "我们家门口有棵大槐树，特别粗" -o test.aiff`，再 `--audio test.aiff`。

> 注意：语音识别（faster-whisper，本地、免 key）与后续分析（DeepSeek，需 key）是
> 两件事——音频转文字这步不花钱，但把文字喂进三条流水线分析仍需配置 key。
> 在 Streamlit 的「🎙️ 音频上传」模式里，可以先看到 ASR 转写全文，再逐段触发分析。

---

## 在线调试界面（Streamlit）

最直观的体验方式——一个能实时看到三件事如何被填充的网页：

```bash
streamlit run src/narrator_flow/app.py   # 浏览器打开 http://localhost:8501
```

三种模式：

- **预制 Demo 播放**：选一个示例口述，点「▶ 下一段」逐段播放（或自动连播），
  右侧三栏实时展示时间线 / 背景 / 记忆锚点的最新状态，可展开看原始 JSON。
  侧边栏默认勾选 **🆓 免 key 演示**——无需 key、瞬时回放预录结果；取消勾选则调用
  真实 DeepSeek。
- **自由输入**：在文本框里逐句输入"长辈刚说的一段话"，点「发送」立即触发分析，
  模拟真实的边听边记场景（此模式需要真实 key）。
- **🎙️ 音频上传（真实 ASR）**：上传一段录音，用本地 faster-whisper 转成文字，
  先展示转写全文，再逐段送入三条流水线分析（需 `pip install -e ".[asr]"` 与真实 key）。

> ⏱️ 注意：真实模式下每处理一段会触发 3 次 LLM 调用，单段通常需 1–2 分钟；
> 免 key 演示模式则是瞬时回放。

---

## 设计 & 架构

这个项目最初是 CrewAI Flows 的练习，但在朝"真正能用的流式产品"演进时，做了几个
关键的产品/工程取舍——它们也是理解这套代码的主线：

**1. 三条流水线，三种更新节奏。** 不是每件事都用同样的频率重算：

- 逻辑大纲：每段增量更新；每 5 段轻量整理；每 10 段基于全文全量重跑（纠正累积偏差）
- 背景知识：纯增量，笔记只增不减
- 记忆锚点：每段细化提示词；详实度达标后触发一次全量重写并生图

**2. 从"一次性分析"转向"流式运行时"。** 真实场景是无界的语音输入，而单段分析要
1–2 分钟，与亚秒级的上游存在 **100 倍以上的吞吐错配**。为此引入了一个核心机制——
**合并队列（背压）**：上游说得再快，也只是让待分析的文本"合并得更长"，而不会排起
一条每段都要等 1–2 分钟的长队。

> 实测：上游 40 个亚秒级片段，经合并最终只触发 4 段分析（分别合并自 1/14/14/11 段）。

**3. 砍掉用不上的抽象。** 流式场景下，CrewAI 的 `Flow`（一次 kickoff 跑完一张
有向图）反而别扭——既背了它的概念成本，又用不上它的编排能力。于是**保留擅长干活的
`Crew`、去掉 `Flow` 这层壳**，用一个 async 事件循环统一"输入 / 并发 / 服务"。

**4. 状态可持久化、可续接。** 会话状态序列化到本地 SQLite，进程崩溃/重启后用同一个
会话 ID 即可从中断处继续。接口按"可换 Redis/Postgres"设计，为未来多机扩展留好了缝。

```
producer(模拟ASR) ──▶ 合并队列(背压) ──▶ 单会话 worker ──▶ 会话存储(SQLite)
                                              │
                                       并发跑三条流水线
                                  └─ asyncio.gather(逻辑, 背景, 锚点)
```

---

## 路线图

原型已经把"流式 + 背压 + 并发 + 断点续接"的主干跑通。接下来按"开源易用 +
作品展示"的目标推进：

- ✅ **免 key 试用模式**（已完成）：`--demo` / GUI 勾选框用预录结果回放，不配 key、
  不花钱即可完整体验三条流水线填充与生图
- **📺 录制演示动图**：Streamlit 界面逐段播放、三栏实时填充（最直观的展示）
- **🧠 防止上下文膨胀**：把"周期性全量重跑/摘要合并"抽成后台任务，并引入摘要/向量
  检索，避免讲述越长、prompt 越大、越慢越贵
- ✅ **接入真实 ASR**（已完成）：本地 faster-whisper，支持音频文件（`--audio`）与
  Streamlit 音频上传；离线、免 key。下一步可扩展为实时麦克风流
- **🎨 接入真实生图模型**（DALL·E / Stable Diffusion 等），替换当前的 stub
- **🌐 服务化**：FastAPI + WebSocket，让长辈能从手机/网页远程连入（async 骨架已就绪）

---

## 技术细节

<details>
<summary><b>项目结构</b></summary>

```
src/narrator_flow/
├── main.py          # CLI 入口（逐段播放 demo，底层用 NarratorSession）
├── app.py           # Streamlit 调试界面（底层用 NarratorSession）
├── state.py         # Pydantic 状态模型
├── streaming.py     # 模拟流式输入（逐段读取 transcript）
├── tools/
│   └── image_gen_tool.py   # 生图工具 stub（待接入真实模型）
├── crews/
│   ├── timeline_crew/      # 逻辑大纲
│   ├── background_crew/    # 背景知识
│   └── anchor_crew/        # 记忆锚点 + 提示词
└── streaming_app/          # 流式运行时（async 事件循环 + 背压，不依赖 CrewAI Flow）
    ├── analyzer.py         # 单段分析：gather 并发三条流水线（唯一一份流水线逻辑）
    ├── session.py          # NarratorSession：同步逐段分析封装（CLI/GUI 用）
    ├── replay.py           # 免 key 演示：回放预录结果，不调用 LLM
    ├── coalescing_queue.py # 合并队列（背压核心）
    ├── session_store.py    # 会话存储：内存 / SQLite（可断点续接）
    ├── worker.py           # 单会话消费循环
    ├── producer.py         # 模拟 ASR 流式输入（文本，免依赖）
    ├── asr.py              # 真实 ASR：本地 faster-whisper（音频→文字片段）
    └── run_stream.py       # 流式运行时 CLI 入口
```

CLI、GUI、流式服务三个入口**共用同一份** `analyzer.py` 的分析逻辑：交互式场景
（CLI/GUI）经 `NarratorSession` 同步调用，真实流式经 `worker` + 合并队列异步调用。
</details>

<details>
<summary><b>LLM 配置（DeepSeek / OpenAI 兼容）</b></summary>

三个 Crew 默认使用 `deepseek/deepseek-chat`，运行前在 `.env` 设置
`DEEPSEEK_API_KEY=sk-xxxx`。

`src/narrator_flow/llm_compat.py` 解决了一个兼容性问题：DeepSeek 的 OpenAI 兼容接口
不支持 OpenAI 专属的结构化输出 `client.beta.chat.completions.parse(...)`（会报
`This response_format type is unavailable now`）。因此自定义了 `DeepSeekCompatibleLLM`，
在需要结构化输出时改用普通的 `chat.completions.create(response_format={"type":
"json_object"})`，再用 Pydantic 手动解析。

切回 OpenAI（如 `gpt-4o-mini`）：把各 `agents.yaml` 的 `llm` 改回 `gpt-4o-mini`，
去掉各 Crew 中 `llm=get_deepseek_llm()` 入参，并在 `.env` 设置 `OPENAI_API_KEY`。
</details>

<details>
<summary><b>流式运行时与背压</b></summary>

- **合并队列** `coalescing_queue.py`：有界队列，worker 忙时堆积的片段在下次取用时
  合并成一段，把"分析次数"与"上游速率"解耦——这是应对吞吐错配的核心。
- **会话存储** `session_store.py`：`SqliteSessionStore`（默认）每段处理后落盘，崩溃/
  重启后用同一 `--session-id` 续接；`InMemorySessionStore` 退出即丢。
- **并发**：`analyzer.py` 用 `asyncio.gather` 同时跑三条流水线，每个 Crew 调用经
  `asyncio.to_thread` 跑在线程里（网络 IO 释放 GIL，获得真实并发）。

运行参数：

```bash
python -m narrator_flow.streaming_app.run_stream                # 默认 SQLite，可续接
python -m narrator_flow.streaming_app.run_stream --segment-delay 0.02  # 加剧背压
python -m narrator_flow.streaming_app.run_stream --store memory # 不落盘
```
</details>

<details>
<summary><b>输出文件</b></summary>

控制台逐段打印进展，同时将最新状态写入（`output*/` 均已加入 `.gitignore`）：

- `logic_outline.json` — 时间线大纲
- `background_knowledge.json` — 背景知识笔记
- `anchor_object.json` — 记忆锚点 + 图像提示词状态
- `generated_images/<物件名>.txt` — 生图结果（当前为 stub 占位）
</details>

---

## License

[MIT](./LICENSE) © 2026 eliothu2026
