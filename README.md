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

## 输出

控制台逐段打印三条流水线的进展，同时将最新状态写入：

- `output/logic_outline.json` — 逻辑/时间线大纲
- `output/background_knowledge.json` — 背景知识笔记
- `output/anchor_object.json` — 锚定物 + 图像提示词状态
- `output/generated_images/<物件名>.txt` — 生图结果（当前为 stub 占位文件）

## 项目结构

```
src/narrator_flow/
├── main.py          # CLI 入口
├── flow.py          # NarratorFlow 主类（编排三条流水线）
├── state.py         # Pydantic 状态模型
├── streaming.py      # 模拟流式输入
├── tools/
│   └── image_gen_tool.py   # 生图工具 stub（待接入真实模型）
└── crews/
    ├── timeline_crew/      # 流水线A：逻辑大纲
    ├── background_crew/    # 流水线B：背景知识
    └── anchor_crew/        # 流水线C：锚定物+提示词
```

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

## 待办

- 接入真实生图模型（DALL-E / Stable Diffusion 等），替换 `image_gen_tool.py` 中的 stub
- 真实音频流 / ASR 输入
- FastAPI / WebSocket 服务化
