"""单段分析（Layer 2）。

把原 NarratorFlow 里的三条流水线逻辑搬过来，但：
- 操作"传入的 state"而不是 self.state（无状态、可复用、可多会话）
- 用 asyncio.gather 并发跑三条流水线（替代 flow.py 里的 ThreadPoolExecutor）
- 每个 CrewAI kickoff 用 asyncio.to_thread 丢进线程（同步 LLM 客户端 + 真实并发）

Pipelines 设计成可替换：CrewPipelines 是真实实现；测试/烟测可注入只 sleep 的
桩，用来验证流式骨架本身（队列/背压/worker/并发）而不烧 LLM 调用。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

from narrator_flow.crews.anchor_crew.anchor_crew import AnchorCrew
from narrator_flow.crews.background_crew.background_crew import BackgroundCrew
from narrator_flow.crews.timeline_crew.timeline_crew import TimelineCrew
from narrator_flow.state import (
    AnchorObjectState,
    BackgroundKnowledgeState,
    LogicOutlineState,
    NarratorFlowState,
    TranscriptChunk,
)
from narrator_flow.tools.image_gen_tool import ImageGenerationTool


def ingest(state: NarratorFlowState, chunk: TranscriptChunk) -> None:
    """把新段并入 state（与原 flow.py 的 _ingest 等价）。"""
    state.all_chunks.append(chunk)
    state.current_chunk_index = chunk.index
    sep = "\n" if state.full_transcript_text else ""
    state.full_transcript_text += f"{sep}[{chunk.index}] {chunk.text}"


class Pipelines(Protocol):
    """三条流水线的接口。每个方法原地修改 state 的对应切片。"""

    async def background(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None: ...
    async def logic(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None: ...
    async def anchor(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None: ...


class CrewPipelines:
    """真实实现：背后是三个 CrewAI Crew，跑在线程里以获得真实并发。"""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        (self.output_dir / "generated_images").mkdir(parents=True, exist_ok=True)

    # ---- 流水线 B：背景知识（纯增量）+ 每 3 次触发考据 agent ----
    FACT_CHECK_EVERY = 3

    async def background(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        result = await asyncio.to_thread(
            lambda: BackgroundCrew().crew().kickoff(
                inputs={
                    "current_notes": state.background.notes,
                    "current_era_estimate": state.background.era_estimate or "未知",
                    "confidence": state.background.confidence,
                    "chunk_index": chunk.index,
                    "new_chunk_text": chunk.text,
                }
            )
        )
        new_state: BackgroundKnowledgeState = result.pydantic
        existing = state.background.notes
        new_state.notes = existing + [n for n in new_state.notes if n not in existing]
        state.background = new_state

        # 每累积 FACT_CHECK_EVERY 次背景更新，串行触发一次考据核验
        state.background_update_count += 1
        if state.background_update_count % self.FACT_CHECK_EVERY == 0:
            from .fact_checker import FactChecker
            state.background = await asyncio.to_thread(
                FactChecker().verify, state.background
            )

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
        result = await asyncio.to_thread(
            lambda: TimelineCrew().incremental_crew().kickoff(
                inputs={
                    "current_outline": state.logic_outline.model_dump_json(),
                    "chunk_index": chunk.index,
                    "new_chunk_text": chunk.text,
                }
            )
        )
        self._apply_logic(state, result, mode)

    async def _logic_refine(self, state) -> None:
        result = await asyncio.to_thread(
            lambda: TimelineCrew().refine_crew().kickoff(
                inputs={"current_outline": state.logic_outline.model_dump_json()}
            )
        )
        self._apply_logic(state, result, "refine")

    async def _logic_full(self, state) -> None:
        result = await asyncio.to_thread(
            lambda: TimelineCrew().full_rerun_crew().kickoff(
                inputs={"full_transcript": state.full_transcript_text}
            )
        )
        self._apply_logic(state, result, "full_rerun")

    @staticmethod
    def _apply_logic(state, result, mode: str) -> None:
        outline: LogicOutlineState = result.pydantic
        outline.last_update_mode = mode
        state.logic_outline = outline

    # ---- 流水线 C：锚定物 + 生图 ----
    async def anchor(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        result = await asyncio.to_thread(
            lambda: AnchorCrew().incremental_crew().kickoff(
                inputs={
                    "candidate_name": state.anchor.candidate_name or "（尚未确定）",
                    "mention_count": state.anchor.mention_count,
                    "descriptive_attributes": state.anchor.descriptive_attributes,
                    "current_prompt": state.anchor.image_prompt,
                    "chunk_index": chunk.index,
                    "new_chunk_text": chunk.text,
                }
            )
        )
        self._apply_anchor(state, result)

        if state.anchor.prompt_detail_score >= 0.8 and not state.anchor.image_generated:
            result = await asyncio.to_thread(
                lambda: AnchorCrew().full_regen_crew().kickoff(
                    inputs={
                        "candidate_name": state.anchor.candidate_name or "（尚未确定）",
                        "descriptive_attributes": state.anchor.descriptive_attributes,
                        "full_transcript": state.full_transcript_text,
                    }
                )
            )
            self._apply_anchor(state, result)
            anchor = state.anchor
            if anchor.is_ready_for_generation and not anchor.image_generated:
                safe_name = (anchor.candidate_name or "anchor_object").replace(" ", "_")
                image_path = self.output_dir / "generated_images" / f"{safe_name}.txt"
                await asyncio.to_thread(
                    ImageGenerationTool().run,
                    prompt=anchor.image_prompt,
                    output_path=str(image_path),
                )
                anchor.image_generated = True
                anchor.image_path = str(image_path)

    @staticmethod
    def _apply_anchor(state, result) -> None:
        new_state: AnchorObjectState = result.pydantic
        new_state.image_generated = state.anchor.image_generated
        new_state.image_path = state.anchor.image_path
        state.anchor = new_state


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
