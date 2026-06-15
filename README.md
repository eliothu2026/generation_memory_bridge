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
cp .env.example .env   # 并填入 OPENAI_API_KEY
python -m narrator_flow.main
# 或带延迟模拟实时效果：
python -m narrator_flow.main --delay 1.0
```

需要先将 `src` 加入 `PYTHONPATH`（或以可编辑模式安装）：

```bash
pip install -e .
```

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

## 待办

- 接入真实生图模型（DALL-E / Stable Diffusion 等），替换 `image_gen_tool.py` 中的 stub
- 真实音频流 / ASR 输入
- FastAPI / WebSocket 服务化
