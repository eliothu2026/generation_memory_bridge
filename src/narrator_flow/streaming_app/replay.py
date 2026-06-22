"""免 key 演示用的回放流水线。

ReplayPipelines 实现了与 CrewPipelines 相同的 Pipelines 接口（background/logic/
anchor），但**不调用任何 LLM**：它读取预录快照（scripts/gen_demo_replay.py 生成），
按 chunk 索引把对应的状态切片"放"进 state。这样没有 API key、不花钱也能完整体验
三条流水线逐段填充、并最终触发生图的产品交互。

生图仍走真实的 ImageGenerationTool（当前是写占位文件的 stub），因此演示里"已生图"
这一步也是真的会落地一个文件，而非伪造。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from narrator_flow.state import (
    AnchorObjectState,
    BackgroundKnowledgeState,
    LogicOutlineState,
    NarratorFlowState,
    TranscriptChunk,
)
from narrator_flow.tools.image_gen_tool import ImageGenerationTool

DEFAULT_FIXTURE = "data/demo_replay/sample_story.replay.json"


class ReplayPipelines:
    """按预录快照逐段回放，不依赖任何 LLM 或 API key。

    Args:
        fixture_path: 快照 JSON 路径（{chunk_index: {slice: 对象}}，稀疏 + 累积）。
        output_dir: 生图输出目录。
        think_delay: 每条流水线回放前的人为延迟（秒），用于在 GUI 里营造"正在思考"
                     的观感；设 0 则瞬时返回。
    """

    def __init__(self, fixture_path: str | Path = DEFAULT_FIXTURE,
                 output_dir: str | Path = "output_demo", think_delay: float = 0.0) -> None:
        raw = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        self.snapshots: Dict[int, Dict[str, Any]] = {int(k): v for k, v in raw.items()}
        self.output_dir = Path(output_dir)
        (self.output_dir / "generated_images").mkdir(parents=True, exist_ok=True)
        self.think_delay = think_delay

    async def _tick(self) -> None:
        if self.think_delay > 0:
            await asyncio.sleep(self.think_delay)

    async def background(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        await self._tick()
        snap = self.snapshots.get(chunk.index)
        if snap and "background" in snap:
            state.background = BackgroundKnowledgeState.model_validate(snap["background"])

    async def logic(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        await self._tick()
        snap = self.snapshots.get(chunk.index)
        if snap and "logic_outline" in snap:
            state.logic_outline = LogicOutlineState.model_validate(snap["logic_outline"])

    async def follow_up(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        await self._tick()
        snap = self.snapshots.get(chunk.index)
        # 临时性：每段覆盖为快照里的预录建议（没有则清空）
        state.follow_up_questions = list(snap.get("follow_up", [])) if snap else []

    async def anchor(self, state: NarratorFlowState, chunk: TranscriptChunk) -> None:
        await self._tick()
        snap = self.snapshots.get(chunk.index)
        if not (snap and "anchor" in snap):
            return
        new = AnchorObjectState.model_validate(snap["anchor"])

        # 已经生成过图就保留，不重复生成
        if state.anchor.image_generated:
            new.image_generated = True
            new.image_path = state.anchor.image_path
        elif new.prompt_detail_score >= 0.8 and new.is_ready_for_generation:
            safe_name = (new.candidate_name or "anchor_object").replace(" ", "_")
            image_path = self.output_dir / "generated_images" / f"{safe_name}.txt"
            await asyncio.to_thread(
                ImageGenerationTool().run,
                prompt=new.image_prompt,
                output_path=str(image_path),
            )
            new.image_generated = True
            new.image_path = str(image_path)

        state.anchor = new
