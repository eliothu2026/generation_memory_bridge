"""单段分析（Layer 2，方案3：不依赖任何 agent 框架）。

三条流水线（背景/逻辑/锚点）直接用 llm_client 调 DeepSeek + Pydantic 解析，
不再经 CrewAI。每个 LLM 调用用 asyncio.to_thread 跑在线程里，三条用 asyncio.gather
并发。Pipelines 接口不变 → 流式/GUI/CLI/免key 回放全部无需改动。

Prompt 由原 crews/*/config 的 agents.yaml(角色) + tasks.yaml(任务) 移植而来。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from narrator_flow.state import (
    AnchorObjectState,
    BackgroundKnowledgeState,
    LogicOutlineState,
    NarratorFlowState,
    TranscriptChunk,
)
from narrator_flow.tools.image_gen_tool import ImageGenerationTool

from . import llm_client

# ----------------------------------------------------------------------
# 系统提示词（移植自各 agents.yaml 的 role/goal/backstory）
# ----------------------------------------------------------------------
_BACKGROUND_SYS = (
    "你是一位社会历史学者（时代背景与社会语境研究员）。你擅长从口述史的只言片语中"
    "识别时代线索（如“粮票/知青/生产队/包产到户/拖拉机”），推断故事发生的年代、地域"
    "和社会背景，并为听众撰写、持续细化背景知识笔记。你的笔记只增不减：新信息让你修正"
    "之前判断时，在新笔记中说明“补充/修正”，而非直接覆盖。"
)
_TIMELINE_SYS = (
    "你是一位经验丰富的口述史研究员和编辑（时间线整理师）。你擅长从碎片化、反复跳跃的"
    "回忆中重建连贯的人生脉络和事件因果链。你绝不编造讲述者没提到的信息；时间不确定时"
    "用“约/大概/可能在…前后”标注；信息不足以定位的事件放入待澄清列表，而非强行排序。"
)
_ANCHOR_SYS = (
    "你是叙事锚点物件与图像提示词设计师。你擅长从冗长、跳跃的口述中捕捉反复出现、承载"
    "情感的具体物件/地点/意象，并把它的视觉细节（材质、颜色、形状、磨损、场景、光线氛围）"
    "逐步整理成详尽、具体、适合 AI 图像生成模型的英文提示词。你会持续追踪一个最主要的候选"
    "物件，统计提及次数，并客观评估提示词的详实程度。"
)


def ingest(state: NarratorFlowState, chunk: TranscriptChunk) -> None:
    """把新段并入 state。"""
    state.all_chunks.append(chunk)
    state.current_chunk_index = chunk.index
    sep = "\n" if state.full_transcript_text else ""
    state.full_transcript_text += f"{sep}[{chunk.index}] {chunk.text}"


class Pipelines(Protocol):
    async def background(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None: ...
    async def logic(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None: ...
    async def anchor(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None: ...


class LLMPipelines:
    """三条流水线的真实实现：直连 DeepSeek（无框架），跑在线程里以获得并发。"""

    FACT_CHECK_EVERY = 3

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        (self.output_dir / "generated_images").mkdir(parents=True, exist_ok=True)

    # ---- 流水线 B：背景知识（纯增量）+ 每 3 次触发考据 agent ----
    async def background(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        user = (
            f"已有的背景知识笔记列表：\n{state.background.notes}\n\n"
            f"当前对年代/地域/社会背景的估计：{state.background.era_estimate or '未知'}"
            f"（置信度 {state.background.confidence}）\n\n"
            f"新增的一段讲述内容（第 {chunk.index} 段）：\n\"{chunk.text}\"\n\n"
            "请：1) 若有可推断年代/地域/社会背景的线索，更新 era_estimate 为更具体的描述并"
            "调整 confidence(0-1)，与旧判断冲突时保留有用旧信息并注明“修正”；"
            "2) 为新发现的背景概念在 notes 末尾追加条目（简明解释一个时代背景概念），"
            "绝不删除或覆盖已有条目；3) 若本段无新增背景信息，原样返回当前 notes/"
            "era_estimate/confidence。"
        )
        new_state: BackgroundKnowledgeState = await asyncio.to_thread(
            llm_client.structured,
            [{"role": "system", "content": _BACKGROUND_SYS}, {"role": "user", "content": user}],
            BackgroundKnowledgeState,
        )
        if new_state is not None:
            existing = state.background.notes
            new_state.notes = existing + [n for n in new_state.notes if n not in existing]
            state.background = new_state

        # 每累积 FACT_CHECK_EVERY 次背景更新，串行触发一次考据核验
        state.background_update_count += 1
        if state.background_update_count % self.FACT_CHECK_EVERY == 0:
            from .fact_checker import FactChecker
            state.background = await asyncio.to_thread(FactChecker().verify, state.background)

    # ---- 流水线 A：逻辑大纲（按节奏分发） ----
    async def logic(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        n = chunk.index + 1
        if n % 10 == 0:
            await self._logic_full(state)
        elif n % 5 == 0:
            await self._logic_incremental(state, chunk, mode="incremental")
            await self._logic_refine(state)
        else:
            await self._logic_incremental(state, chunk, mode="incremental")

    async def _logic_incremental(self, state, chunk, mode: str) -> None:
        user = (
            f"以下是已有的结构化时间线大纲（JSON）：\n{state.logic_outline.model_dump_json()}\n\n"
            f"以下是新增的一段讲述内容（第 {chunk.index} 段）：\n\"{chunk.text}\"\n\n"
            "请基于新内容更新时间线大纲：1) 新内容补充/修正已有事件则更新对应条目"
            "（保留并追加 source_chunk_indices）；2) 全新事件按推断时间顺序(order)插入；"
            "3) 尽量标注因果(cause/effect)；4) 暂无法定位的放入 open_threads，之后可澄清后移除；"
            "5) 不要丢弃已有事件。最后生成简洁的 markdown 大纲文本写入 raw_outline_text。"
        )
        await self._apply_logic(state, user, mode)

    async def _logic_refine(self, state) -> None:
        user = (
            f"以下是当前时间线大纲（JSON）：\n{state.logic_outline.model_dump_json()}\n\n"
            "请做一次轻量整理（不要引入任何新信息）：1) 合并重复/高度相似事件；"
            "2) 调整 order 使顺序更连贯；3) open_threads 中能据现有 events 澄清的转为正式事件并移除；"
            "4) 重新生成 raw_outline_text。"
        )
        await self._apply_logic(state, user, "refine")

    async def _logic_full(self, state) -> None:
        user = (
            f"以下是迄今为止收到的完整讲述记录（按段落顺序拼接）：\n---\n"
            f"{state.full_transcript_text}\n---\n\n"
            "请完全基于以上全文重建时间线大纲，忽略此前中间结果以纠正累积偏差：1) 提取所有事件"
            "按推断时间顺序排列(order 从 1 起)；2) 标注因果(cause/effect)并记录每个事件来自哪些"
            "段落(source_chunk_indices)；3) 无法定位的放入 open_threads；4) 生成 raw_outline_text。"
        )
        await self._apply_logic(state, user, "full_rerun")

    async def _apply_logic(self, state, user: str, mode: str) -> None:
        outline: LogicOutlineState = await asyncio.to_thread(
            llm_client.structured,
            [{"role": "system", "content": _TIMELINE_SYS}, {"role": "user", "content": user}],
            LogicOutlineState,
        )
        if outline is not None:
            outline.last_update_mode = mode
            state.logic_outline = outline

    # ---- 流水线 C：锚定物 + 生图 ----
    async def anchor(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        user = (
            f"当前候选锚点物件：{state.anchor.candidate_name or '（尚未确定）'}"
            f"（已被提及约 {state.anchor.mention_count} 次）\n"
            f"当前已知视觉细节列表：{state.anchor.descriptive_attributes}\n"
            f"当前英文图像提示词：\"{state.anchor.image_prompt}\"\n\n"
            f"新增的一段讲述内容（第 {chunk.index} 段）：\n\"{chunk.text}\"\n\n"
            "请：1) 判断本段是否再次提及候选物件，或出现更高频/更核心的新物件（可切换 "
            "candidate_name）；2) 若提及候选物件则 mention_count 加一，提取新视觉细节追加到 "
            "descriptive_attributes（避免重复）；3) 基于累积细节更新 image_prompt（必须英文、"
            "具体可视化）；4) 给出 prompt_detail_score(0-1)，按是否覆盖[主体/材质颜色/状态磨损/"
            "场景背景/光线氛围]五维评分；5) score>=0.8 则 is_ready_for_generation=true 否则 false。"
            "image_generated/image_path 保持传入值不变。"
        )
        new_state: AnchorObjectState = await asyncio.to_thread(
            llm_client.structured,
            [{"role": "system", "content": _ANCHOR_SYS}, {"role": "user", "content": user}],
            AnchorObjectState,
        )
        if new_state is not None:
            new_state.image_generated = state.anchor.image_generated
            new_state.image_path = state.anchor.image_path
            state.anchor = new_state

        if state.anchor.prompt_detail_score >= 0.8 and not state.anchor.image_generated:
            await self._anchor_full_regen_and_generate(state)

    async def _anchor_full_regen_and_generate(self, state: NarratorFlowState) -> None:
        user = (
            f"候选锚点物件：{state.anchor.candidate_name or '（尚未确定）'}\n"
            f"已积累的视觉细节列表：{state.anchor.descriptive_attributes}\n\n"
            f"以下是迄今为止收到的完整讲述记录：\n---\n{state.full_transcript_text}\n---\n\n"
            "请基于全文重新撰写一份完整、详尽的英文图像生成提示词(image_prompt)，覆盖[主体/"
            "材质颜色/状态磨损/场景背景/光线氛围]五维，尽量纳入全文中所有相关细节；给出最终 "
            "prompt_detail_score(应 >=0.8)，is_ready_for_generation=true；mention_count 与 "
            "descriptive_attributes 可据全文重新整理。image_generated/image_path 保持传入值。"
        )
        new_state: AnchorObjectState = await asyncio.to_thread(
            llm_client.structured,
            [{"role": "system", "content": _ANCHOR_SYS}, {"role": "user", "content": user}],
            AnchorObjectState,
        )
        if new_state is not None:
            new_state.image_generated = state.anchor.image_generated
            new_state.image_path = state.anchor.image_path
            state.anchor = new_state

        anchor = state.anchor
        if anchor.is_ready_for_generation and not anchor.image_generated:
            safe_name = (anchor.candidate_name or "anchor_object").replace(" ", "_")
            image_path = self.output_dir / "generated_images" / f"{safe_name}.txt"
            await asyncio.to_thread(
                ImageGenerationTool().run, prompt=anchor.image_prompt, output_path=str(image_path)
            )
            anchor.image_generated = True
            anchor.image_path = str(image_path)


class Analyzer:
    """编排：ingest 后并发跑三条流水线。"""

    def __init__(self, pipelines: Pipelines) -> None:
        self.pipelines = pipelines

    async def analyze(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        ingest(state, chunk)
        await asyncio.gather(
            self.pipelines.background(state, chunk),
            self.pipelines.logic(state, chunk),
            self.pipelines.anchor(state, chunk),
        )
