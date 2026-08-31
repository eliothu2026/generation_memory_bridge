# 代际记忆桥梁 · Generation Memory Bridge

> 一个"边听边理解"的 AI：在长辈口述往事时，实时把零散、跳跃的讲述整理成
> 时间线，补全时代背景，并把反复提及的"记忆锚点"还原成画面。

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-prototype-orange)

📄 **想了解产品思路**（用户、竞品、AI 风险、成功指标、关键决策）？
见 **[产品简报 docs/product-brief.md](./docs/product-brief.md)**。

> ### 🚀 30 秒先睹为快(无需安装)
> 在跑完整项目之前,想先感受一下使用流程?**直接用浏览器打开仓库根目录的
> [`静态demo_快速体验.html`](./静态demo_快速体验.html)** 即可——纯静态、**0 依赖**(数据内联,无需 npm / 后端 / 网络),
> 与真实前端**同款设计与交互**:逐段点「老人继续讲」,看右侧时间线实时生长、老人气泡下自动
> 挂出「AI 背景补充」与「追问建议」,还能扮演孙辈发言。觉得对味,再按下方「快速开始」上手完整版。

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
| **逻辑梳理** | 讲述跳来跳去、没有时间线 | 把零散口述重建成结构化的**时间线 / 因果大纲**，并标记"待澄清线索" |
| **背景还原** | 细节背后的时代/社会语境缺失 | 从只言片语推断**年代与社会背景**，持续生成背景知识笔记（并由考据 agent 核实） |
| **记忆可视化** | 珍贵的记忆只是文字，看不见 | 识别反复提及的**标志性物件**，逐步完善描述，最终生成一张图把它"画出来" |
| **建议追问** | 年轻人常因"不知道怎么接"而冷场 | 在长辈说完一段后，替年轻人想 1–2 个具体追问，增强互动、补全细节；无值得问的则不打扰 |

> 这几件事是**同时进行**的——讲述者不必停顿，AI 在后台持续整理、修订、补全。
> 其中"建议追问"服务于**对话当下**、不写入档案：本产品的核心价值是**那场祖孙对话的
> 体验**，结构化的记忆档案只是副产品（这与"以成书为交付"的同类产品根本不同）。

---

## 测试效果

以一段模拟的"农村长辈回忆 1970–80 年代"的口述（18 段）为例，跑完后 AI 的产出：

- **时间线**：整理出 15 个事件、8 条待澄清线索，覆盖知青下乡、记工分、包产到户、
  购置拖拉机等多个时期，并在讲述中多次自我修订。
- **背景还原**：年代估计收敛为"20 世纪 70 年代末至 80 年代末中国农村（家庭联产
  承包责任制推行初期至中期）"，累积 8 条背景笔记，并经考据 agent 核实标注。
- **记忆锚点**：识别出讲述者反复提到的"**大槐树**"（提及 10 次），逐步攒出 14 条
  视觉细节（树皮裂纹、树下石桌、喜鹊窝、四季变化……），细节足够后自动触发生图。

<!-- 演示 GIF / 截图放这里（见「路线图」P1）。建议录一段 Streamlit 界面逐段播放
     "大槐树"故事、右侧三栏实时填充的过程，约 20–30 秒。 -->
>  **演示动图待补**： Streamlit 中可见 调试界面逐段播放、三栏实时更新的过程
> （见下方「在线调试界面」）。这是本项目最直观的展示。

---

## 快速开始

环境要求：Python 3.10–3.12（建议用 pyenv 安装 3.10.x）。

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

## 🖥️ Web 演示前端（Gemini 风格 · 会话优先）

面向**产品演示**的正式前端（React + Vite + TypeScript + Tailwind），区别于下方偏工程的 Streamlit 调试界面。
布局:左侧**真实会话列表**（新建 / 切换 / 删除，持久化于后端 SQLite）、中间祖孙双人对话（老人转写在左、
孙辈发言在右）、右侧可收起的实时时间线；**史实补充与交互提醒逐段挂在对应的老人气泡下**
（明确标注「AI 背景补充，非老人原话」）。

> 💡 只想快速感受交互?不必装下面这些——直接打开根目录 [`静态demo_快速体验.html`](./静态demo_快速体验.html)(0 依赖静态版)。

**离线示例(默认、0 后端、免 key):** 侧栏置顶的「大槐树的故事」是本地回放,逐段点「老人继续讲 ▶」
即可看到右侧时间线与气泡下补充**实时填充**、点追问建议一键填入、扮演孙辈发言。

```bash
python scripts/gen_demo_script.py            # (可选)重生成 demo 数据,仓库已内置一份
cd frontend && npm install && npm run dev    # 浏览器打开 http://127.0.0.1:5173
```

> 🇨🇳 国内 `npm install` 卡住?加镜像(只需一次):`npm install --registry=https://registry.npmmirror.com`

**实时会话(接真实分析、持久化):** 点侧栏「新建会话」开一条真实会话,连 FastAPI + WebSocket、用真实
DeepSeek 分析,结果存 SQLite(刷新页面 / 重启后端仍在)。一条会话里可随时切**输入方式**:💬 文字(以老人 / 孙辈
身份)、🎙️ 录音上传、🎤 实时麦克风——音频经 faster-whisper 转写后走**背压合并队列 + worker** 分析。

```bash
export DEEPSEEK_API_KEY=sk-...               # 或在界面右上角 ⚙️ 热配置(后端可不带 key 冷启动)
pip install -e ".[web,asr]"                  # web=服务化;asr=音频转写(faster-whisper)
uvicorn narrator_flow.server.app:app         # 默认 http://127.0.0.1:8000,前端经 Vite 代理连它
```

> ⚙️ **热配置**:右上角「配置」可直接填 / 改模型 API Key 与 Base URL(仅存后端进程内存、不落盘),保存后
> 自动重连——因此后端可**不带 key 冷启动**,界面里配好即用。
> 🎤 麦克风(getUserMedia)需"安全上下文":请用 `http://127.0.0.1:5173` 或 `localhost` 打开,勿用局域网 IP。

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
- **📞 实时通话（实验·阶段1）**：抓**本机麦克风**（`sounddevice`，wheel 自带 PortAudio、
  纯 pip 无需 Homebrew）→ VAD 自动切句 → faster-whisper 逐句转写为实时字幕，体验
  "保持通话"式输入（需 `pip install -e ".[live]"`）。**链路已端到端验证**（麦→VAD→
  转写→字幕）；**识别精度仍依赖麦克风质量/环境噪声/模型大小，属已知待打磨项**——
  原型阶段验证的是架构可行性，而非生产级 ASR 精度。分析接入（阶段2）与说话人分离见路线图。

> ⏱️ 注意：真实模式下每处理一段会触发 3 次 LLM 调用，单段通常需 1–2 分钟；
> 免 key 演示模式则是瞬时回放。

---

## 设计 & 架构

这个项目最初是 CrewAI Flows 的练习，但在朝"真正能用的流式产品"演进时，做了几个
关键的产品/工程取舍——它们也是理解这套代码的主线（其中一条主线就是：在反复评估后
**逐步、彻底地移除了 CrewAI 框架**）：

**1. 三条流水线，三种更新节奏。** 不是每件事都用同样的频率重算：

- 逻辑大纲：每段增量更新；每 5 段轻量整理；每 10 段基于全文全量重跑（纠正累积偏差）
- 背景知识：纯增量，笔记只增不减
- 记忆锚点：每段细化提示词；详实度达标后触发一次全量重写并生图

**2. 从"一次性分析"转向"流式运行时"。** 真实场景是无界的语音输入，而单段分析要
1–2 分钟，与亚秒级的上游存在 **100 倍以上的吞吐错配**。为此引入了一个核心机制——
**合并队列（背压）**：上游说得再快，也只是让待分析的文本"合并得更长"，而不会排起
一条每段都要等 1–2 分钟的长队。

> 实测：上游 40 个亚秒级片段，经合并最终只触发 4 段分析（分别合并自 1/14/14/11 段）。

**3. 砍掉用不上的抽象——最终彻底移除 CrewAI。** 先是流式场景下 CrewAI 的 `Flow`
（一次 kickoff 跑完一张有向图）不适合无界流，去掉它、用 async 事件循环统一"输入/
并发/服务"。继续评估后发现：这套"三条独立变换 + 一个核验者"的拓扑里，CrewAI 是
主流框架中概念最不匹配、体量最重（30 依赖、~1GB）的那个，三条变换其实退化成了
"填模板→调一次 LLM→解析 Pydantic"，用不上多 agent/工具调用能力。于是三条变换
也改为**直连 DeepSeek + Pydantic**，整个项目**不再依赖任何 agent 框架**。

**4. 状态可持久化、可续接。** 会话状态序列化到本地 SQLite，进程崩溃/重启后用同一个
会话 ID 即可从中断处继续。接口按"可换 Redis/Postgres"设计，为未来多机扩展留好了缝。

**5. 引入"考据 agent"对抗幻觉（生成者 / 批判者分工）。** 背景知识由 LLM 推断，
天然有编造史实的风险。为此加了一个独立的**考据 agent**：背景流水线每累积 3 次输出，
它就介入一次，**自主调用维基百科检索工具**核实笔记中的史实，按保守策略处置——存疑只
标注「待核实」、明确造假才删、过浅则补充。它是一个**手写的 reason–act 工具循环**（不
依赖任何 agent 框架）：先用工具调查、再输出结构化结论，两步分开，刚好避开"JSON 模式与
工具调用在单次调用里互斥"的坑。

> 为什么不复用 CrewAI 写这个 agent？因为评估下来，这个"三条独立变换 + 一个核验者"的
> 拓扑里，CrewAI 是主流框架中概念最不匹配、体量最重（30 依赖、~1GB）的那个。唯一真正
> 需要"agent 能力"的就是这一个工具循环，而它手写也就百来行——所以选择不为它背一个重
> 框架。（方案已收尾：三条变换也已迁出，整个项目不再依赖 CrewAI。）

```
producer(模拟ASR) ──▶ 合并队列(背压) ──▶ 单会话 worker ──▶ 会话存储(SQLite)
                                              │
                                       并发跑四条流水线
                          └─ asyncio.gather(逻辑, 背景, 锚点, 建议追问)
                                              │ 背景每 3 次
                                              ▼
                                   考据 agent（维基检索·手写工具循环）
```

---

## 记忆 / 状态系统

"边听边理解"要求系统记住整场对话、并让每段分析都站在之前的积累之上。本项目的记忆是
**两层**的：

**第 1 层 · 工作记忆 `NarratorFlowState`（`state.py`）**
对话进行中的"短期记忆"，累积全部上下文：原文（`full_transcript_text`）、时间线
（`logic_outline`）、背景笔记（`background`，**纯增量、只增不减**，仅考据 agent 有权修订/
删改）、记忆锚点（`anchor`）、最新建议追问（`follow_up_questions`，临时不累积）。
**机制**：每来新一段，四条流水线拿到的是「当前完整 state + 新一段」→ 产出「更新后的
state」。所以"记忆"就体现在——**每段分析都基于之前所有积累**（笔记越攒越全、时间线越拼
越完整、考据 agent 还会回头修订）。

**第 2 层 · 持久记忆 `SqliteSessionStore`（`session_store.py`）**
把工作记忆序列化进本地 SQLite，每段处理后落盘；进程崩溃/重启后用同一 `session-id`
即可**从中断处续接**。接口（`load`/`save`）按"可换 Redis/Postgres"设计。

```
新一段口述 ──▶ 工作记忆 NarratorFlowState ◀──累积/修订── 四条流水线 + 考据 agent
                      │ 每段落盘
                      ▼
              持久记忆 SqliteSessionStore(SQLite) ──▶ 崩溃/重启可续接
```

**诚实的局限（当前为"全量保留"）**：记忆目前是朴素的"把一切都留着"——`full_transcript_text`
全量保留、笔记只增不减。它**还没有**LLM 圈意义上的高级记忆（无向量库、无摘要压缩、无按需
检索）。因此对话越长，喂给模型的 prompt 越大、越慢越贵。这是已知缺口，对应路线图的
**「防止上下文膨胀」**：把周期性整理抽成后台任务，并引入摘要 / 向量检索，只把相关片段
喂进 prompt，而非每次塞全量。

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
  Streamlit / Web 音频上传;离线、免 key。已进一步扩展为 Web 端实时麦克风流
- ✅ **建议追问（第 4 条流水线）**（已完成 v1）：长辈说完一段后替年轻人想 1–2 个具体
  追问，增强互动、补全细节；自我克制（无值得问的则返回空，不打扰）。当前仅"细节追问型"，
  情感共情型与"音频情绪感知"留待后续
- ✅ **实时语音输入 · Web 端已落地**：Web 会话内 🎙️ 录音上传 / 🎤 实时麦克风 → faster-whisper
  转写 → 背压合并队列 → 真实分析(阶段1 切句 + 阶段2 分析接入已通);阶段3 说话人分离见下条
- **🎙️ 说话人分离（speaker diarization）**：当前 ASR（Whisper）只产出**一条不分人的
  文字流**，分不清"长辈叙述"与"年轻人提问"——这在双人对话+追问场景下会污染分析。
  需引入 whisperx/pyannote（受 HF 访问限制），或在产品上把两人输入分通道处理
- ✅ **考据 agent 对抗幻觉**（已完成）：独立核验 agent，每 3 次背景更新介入，自主调用
  维基检索核实史实、保守标注/删改（手写工具循环，不依赖框架）
- ✅ **彻底移除 CrewAI**（已完成）：三条变换改为直连 DeepSeek + Pydantic，删除
  `crews/` 与 `llm_compat.py`，依赖从 `crewai[tools]`（30 依赖、~1GB）瘦身为
  `openai + httpx`。整个项目不再依赖任何 agent 框架
- **🎨 接入真实生图模型**（DALL·E / Stable Diffusion 等），替换当前的 stub
- ✅ **服务化 + Web 前端**（已完成）：FastAPI + WebSocket 后端 + 会话优先的 React 前端
  （多会话持久化于 SQLite、⚙️ 模型 key 热配置、会话内切换 文字 / 录音 / 麦克风 输入）;
  另含 0 依赖静态演示 `静态demo_快速体验.html`(双击即开)

<!-- 以下由「静态 demo」先行验证、正式前端(frontend/)尚未跟进,列为下次开发备忘 -->
- **🧭 首次使用引导（onboarding）**：静态 demo 已示范"左 → 中 → 右"分区聚光引导（左＝管理会话 +
  配置 LLM Key、中＝点击底部按钮开启"陪伴聆听"、右＝实时时间线），以「我知道了」逐步推进；
  正式前端（`frontend/`）**尚未实现**。
- **📤 记忆的「分享 / 导出」——让回忆成为 AI-native 的上下文**：demo 已放出入口（会话卡右端的分享按钮）。
  最朴素的形态是把一场对话整理出的时间线 / 背景 / 记忆锚点导出为 Markdown 记忆档案，喂给其他 AI / agent
  当上下文；要把它做得更 **AI-native**，可沿这些方向演进（均待实现）：
  - **结构化记忆包（不止 .md）**：同时产出机器可读结构（时间线事件、实体 人/地/物、待澄清线索、锚点），
    每条事实附**出处**（来自哪段口述）与**考据核验状态**（✅已核实 / ⚠️待核实 / 推测），下游 agent 据此
    区分事实与推断，避免幻觉沿着上下文扩散。
  - **可查询的记忆（而非静态文件）**：把记忆暴露成 **MCP / 上下文服务**，其他 agent 按需检索（「外公关于
    大槐树说过什么？」），天然适配 RAG / 工具调用，而不必一次性塞入整份文本。
  - **面向受众的自适应生成**：同一份记忆由 AI 按目标重渲染——给家人的温情叙事 / 纪念册、给族谱工具的
    事实时间线、给孩子的绘本版、给 agent 的问答上下文，而非一份固定导出。
  - **跨会话合并成记忆图谱**：对同一位长辈的多场对话做实体归一 / 去重，汇成一张不断生长的记忆图谱
    （人—地—物—事件及其关系），供 graph-RAG 遍历。
  - **一键接力到下游**：把上下文按目标格式直接送进 Claude / ChatGPT / Notion / 族谱类应用（深链或剪贴板），
    实现「换个工具继续追问」。
  - **持久的「记忆伙伴」**：由记忆包生成可被其他应用消费的长辈 persona / 记忆卡，让「数字记忆伙伴」
    能以了解其生平的口吻回答与陪伴。
- **⏳ 分析过程的实时反馈（流式「识别 / 理解中」占位）**：demo 在每段之间显示「正在识别和理解…」+ 动态
  loading，模拟"边听边理解"的处理过程。真实分析每段需 1–2 分钟，正式前端可借鉴这种**逐段处理态占位**，
  提升"正在为你整理"的感知响应（呈现 / 体验增强）。
- **🎙️ "陪伴聆听"一等入口（呈现增强）**：demo 把底部做成"点一下开始陪伴 / 正在聆听"的单一开关
  （含聆听态动效、模拟讲述的播放 / 暂停）。正式前端**已支持**实时麦克风，但放在"文字 / 上传 / 麦克风"三选一里；
  可考虑把它提升为更醒目的常驻"陪伴模式"（能力已在，差在呈现）。
- **🎨 前端视觉对齐（设计项，非功能缺口）**：把静态 demo 打磨过的观感（Forest 配色、单拱 logo、
  对话区为底 + 左右悬浮卡片、去分界线、内联 SVG 图标 + `prefers-reduced-motion`）回流到正式前端，
  保持两端一致。

---

## 技术细节

<details>
<summary><b>项目结构</b></summary>

```
generation_memory_bridge/
├── src/narrator_flow/
│   ├── main.py · app.py · state.py · streaming.py     # CLI / Streamlit / 状态模型 / 模拟流
│   ├── tools/image_gen_tool.py                         # 生图 stub(待接入真实模型)
│   ├── streaming_app/                                  # 流式运行时(async + 背压,无 agent 框架)
│   │   ├── analyzer.py         # 四条流水线并发(直连 DeepSeek + Pydantic)
│   │   ├── session.py          # NarratorSession(CLI/GUI 同步封装)
│   │   ├── replay.py           # 免 key 回放(不调 LLM)
│   │   ├── coalescing_queue.py · worker.py · producer.py  # 合并队列(背压)/ 消费 / 模拟 ASR
│   │   ├── asr.py              # 真实 ASR:faster-whisper(音频→文字)
│   │   ├── llm_client.py · wikipedia_tool.py · fact_checker.py  # LLM 客户端 / 维基 / 考据 agent
│   │   ├── session_store.py    # 会话状态存储(内存 / SQLite)
│   │   └── run_stream.py       # 流式运行时 CLI
│   └── server/                                         # 🌐 服务化:FastAPI + WebSocket
│       ├── app.py              # 多会话 REST + 统一会话 WS(文字/音频 → 背压 → 分析)
│       └── store.py            # WebSessionStore:会话持久化(SQLite)
├── frontend/                                           # 会话优先 Web 前端(React + Vite + TS + Tailwind)
├── scripts/
│   ├── gen_demo_script.py      # 合成离线 demo 数据(transcript + replay → demo_script.json)
│   └── gen_static_demo.py      # 生成 0 依赖静态演示 → 静态demo_快速体验.html
├── tests/                      # 免 key 单元测试(pytest);.github/workflows/ CI
├── 静态demo_快速体验.html       # 0 依赖静态演示(双击即开)
└── data/  ·  docs/  ·  .env.example  ·  README.md
```

CLI、Streamlit、流式 CLI、Web 服务多个入口**共用同一份** `analyzer.py` 的分析逻辑：交互式场景
（CLI / GUI）经 `NarratorSession` 同步调用，真实流式与 Web 会话经 `worker` + 合并队列异步调用。
</details>

<details>
<summary><b>LLM 配置（DeepSeek，直连，无框架）</b></summary>

默认使用 `deepseek-chat`，运行前在 `.env` 设置 `DEEPSEEK_API_KEY=sk-xxxx`
（可选 `DEEPSEEK_BASE_URL`，默认 `https://api.deepseek.com`）。

`streaming_app/llm_client.py` 是框架无关的薄封装（直接用 `openai` SDK 调 DeepSeek 的
OpenAI 兼容接口）：

- `structured(messages, schema)`：自动把 Pydantic 模型的 JSON Schema 注入 prompt，
  用 JSON 模式输出、再解析校验——替代了原先 CrewAI 的 `output_pydantic`（以及为绕过
  DeepSeek 不支持 `beta.parse` 而写的兼容层，现已随 CrewAI 一并移除）。
- `run_tool_loop(messages, tools, tool_impls)`：agentic 的工具调用循环（考据 agent 用）。

切到 OpenAI：把 base_url/模型换成 OpenAI 的、并设 `OPENAI_API_KEY` 即可。
</details>

<details>
<summary><b>考据 agent（史实核验，对抗幻觉）</b></summary>

- 触发：背景流水线每累积 **3 次**更新，`fact_checker.py` 的 `FactChecker` 介入一次。
- 机制：`llm_client.run_tool_loop` 驱动一个手写的 reason–act 循环，模型自主调用
  `wikipedia_tool.py` 的维基检索工具核实史实；再用 `llm_client.structured` 输出
  修订后的结构化结果。**不依赖任何 agent 框架。**
- 处置（保守）：存疑→标注「⚠️待核实」；明确造假→删除并记 changelog；过浅→补充深化。
- 安全：缺 key 或网络不可达时**安全回退**为原背景，绝不拖垮主流程。

> 🇨🇳 **维基百科在中国大陆被屏蔽**（与 Hugging Face 同类）。裸网会 ConnectTimeout。
> 请在能访问维基的网络（VPN/海外）下使用，或用环境变量指向镜像：
> ```bash
> export WIKIPEDIA_API_ENDPOINT=https://<你的维基镜像>/w/api.php
> ```
> 仅 demo / 文本分析不需要它；考据 agent 只在真实运行（有 key）时按节奏触发。
</details>

<details>
<summary><b>流式运行时与背压</b></summary>

- **合并队列** `coalescing_queue.py`：有界队列，worker 忙时堆积的片段在下次取用时
  合并成一段，把"分析次数"与"上游速率"解耦——这是应对吞吐错配的核心。
- **会话存储** `session_store.py`：`SqliteSessionStore`（默认）每段处理后落盘，崩溃/
  重启后用同一 `--session-id` 续接；`InMemorySessionStore` 退出即丢。
- **并发**：`analyzer.py` 用 `asyncio.gather` 同时跑三条流水线，每个 LLM 调用经
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
