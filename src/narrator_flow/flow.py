"""NarratorFlow: 口述史实时分析 Agent 的主 Flow。

整体设计：单次 kickoff()，在 @start 方法内部循环消费模拟流式输入的
每一个 chunk，并依次驱动三条流水线：

- 流水线 A（逻辑/时间线大纲）：增量更新，每5段轻量整理，每10段全量重跑
- 流水线 B（时代背景知识）：纯增量，每段都跑
- 流水线 C（叙事锚定物 + 图像提示词）：增量细化 + 详实度达标后触发全量重写与生图
"""

from pathlib import Path
from typing import Optional

from crewai.flow.flow import Flow, start

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
from narrator_flow.streaming import stream_chunks
from narrator_flow.tools.image_gen_tool import ImageGenerationTool

OUTPUT_DIR = Path("output")


class NarratorFlow(Flow[NarratorFlowState]):
    """边听边分析的口述史 Flow。"""

    def __init__(self, transcript_path: str, delay: float = 0.0, output_dir: Optional[Path] = None):
        super().__init__()
        self.transcript_path = transcript_path
        self.delay = delay
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "generated_images").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 入口：单次 kickoff，内部循环消费模拟流式 chunk
    # ------------------------------------------------------------------
    @start()
    def run_simulation(self):
        for chunk in stream_chunks(self.transcript_path, self.delay):
            self.process_chunk(chunk)
            self.print_progress(chunk)
            self.dump_outputs()
        return self.state

    # ------------------------------------------------------------------
    # 单个 chunk 的处理：依次驱动三条流水线
    # ------------------------------------------------------------------
    def process_chunk(self, chunk: TranscriptChunk) -> None:
        self._ingest(chunk)
        self._update_background(chunk)  # 流水线B：纯增量，每次都跑
        self._update_logic(chunk)  # 流水线A：按节奏分发
        self._update_anchor(chunk)  # 流水线C：增量 + 触发式全量

    def _ingest(self, chunk: TranscriptChunk) -> None:
        self.state.all_chunks.append(chunk)
        self.state.current_chunk_index = chunk.index
        sep = "\n" if self.state.full_transcript_text else ""
        self.state.full_transcript_text += f"{sep}[{chunk.index}] {chunk.text}"

    # ------------------------------------------------------------------
    # 流水线 A：逻辑 / 时间线大纲
    # ------------------------------------------------------------------
    def _update_logic(self, chunk: TranscriptChunk) -> None:
        n = chunk.index + 1  # 已处理的段落数（1-based）
        if n % 10 == 0:
            self._logic_full_rerun(chunk, mode="full_rerun")
        elif n % 5 == 0:
            self._logic_refine(chunk, mode="refine")
        else:
            self._logic_incremental(chunk, mode="incremental")

    def _logic_incremental(self, chunk: TranscriptChunk, mode: str) -> None:
        self.state.logic_outline.last_update_mode = mode
        result = TimelineCrew().incremental_crew().kickoff(
            inputs={
                "current_outline": self.state.logic_outline.model_dump_json(),
                "chunk_index": chunk.index,
                "new_chunk_text": chunk.text,
            }
        )
        self._apply_logic_result(result, mode)

    def _logic_refine(self, chunk: TranscriptChunk, mode: str) -> None:
        # 先做一次增量更新，纳入本段新信息
        self._logic_incremental(chunk, mode="incremental")
        # 再做一次轻量整理（不引入新信息）
        result = TimelineCrew().refine_crew().kickoff(
            inputs={"current_outline": self.state.logic_outline.model_dump_json()}
        )
        self._apply_logic_result(result, mode)

    def _logic_full_rerun(self, chunk: TranscriptChunk, mode: str) -> None:
        result = TimelineCrew().full_rerun_crew().kickoff(
            inputs={"full_transcript": self.state.full_transcript_text}
        )
        self._apply_logic_result(result, mode)

    def _apply_logic_result(self, result, mode: str) -> None:
        outline: LogicOutlineState = result.pydantic
        outline.last_update_mode = mode
        self.state.logic_outline = outline

    # ------------------------------------------------------------------
    # 流水线 B：时代背景知识（纯增量）
    # ------------------------------------------------------------------
    def _update_background(self, chunk: TranscriptChunk) -> None:
        result = BackgroundCrew().crew().kickoff(
            inputs={
                "current_notes": self.state.background.notes,
                "current_era_estimate": self.state.background.era_estimate or "未知",
                "confidence": self.state.background.confidence,
                "chunk_index": chunk.index,
                "new_chunk_text": chunk.text,
            }
        )
        new_state: BackgroundKnowledgeState = result.pydantic
        # 防御性保证“纯增量”：notes 只增不减
        existing = self.state.background.notes
        merged = existing + [n for n in new_state.notes if n not in existing]
        new_state.notes = merged
        self.state.background = new_state

    # ------------------------------------------------------------------
    # 流水线 C：叙事锚定物 + 图像提示词
    # ------------------------------------------------------------------
    def _update_anchor(self, chunk: TranscriptChunk) -> None:
        self._anchor_incremental(chunk)
        if self.state.anchor.prompt_detail_score >= 0.8 and not self.state.anchor.image_generated:
            self._anchor_full_regen_and_generate()

    def _anchor_incremental(self, chunk: TranscriptChunk) -> None:
        result = AnchorCrew().incremental_crew().kickoff(
            inputs={
                "candidate_name": self.state.anchor.candidate_name or "（尚未确定）",
                "mention_count": self.state.anchor.mention_count,
                "descriptive_attributes": self.state.anchor.descriptive_attributes,
                "current_prompt": self.state.anchor.image_prompt,
                "chunk_index": chunk.index,
                "new_chunk_text": chunk.text,
            }
        )
        self._apply_anchor_result(result)

    def _anchor_full_regen_and_generate(self) -> None:
        result = AnchorCrew().full_regen_crew().kickoff(
            inputs={
                "candidate_name": self.state.anchor.candidate_name or "（尚未确定）",
                "descriptive_attributes": self.state.anchor.descriptive_attributes,
                "full_transcript": self.state.full_transcript_text,
            }
        )
        self._apply_anchor_result(result)

        anchor = self.state.anchor
        if anchor.is_ready_for_generation and not anchor.image_generated:
            safe_name = (anchor.candidate_name or "anchor_object").replace(" ", "_")
            image_path = self.output_dir / "generated_images" / f"{safe_name}.txt"
            ImageGenerationTool().run(prompt=anchor.image_prompt, output_path=str(image_path))
            anchor.image_generated = True
            anchor.image_path = str(image_path)

    def _apply_anchor_result(self, result) -> None:
        new_state: AnchorObjectState = result.pydantic
        # 保留之前已生成的图像信息，避免被覆盖
        new_state.image_generated = self.state.anchor.image_generated
        new_state.image_path = self.state.anchor.image_path
        self.state.anchor = new_state

    # ------------------------------------------------------------------
    # 输出展示与持久化
    # ------------------------------------------------------------------
    def print_progress(self, chunk: TranscriptChunk) -> None:
        total = len(self.state.all_chunks)
        outline = self.state.logic_outline
        bg = self.state.background
        anchor = self.state.anchor

        print(f"\n=== Chunk {chunk.index + 1}/{total} ===")
        print(f"[逻辑大纲] 更新方式: {getattr(outline, 'last_update_mode', 'incremental')} "
              f"| 当前事件数: {len(outline.events)} | 待澄清: {len(outline.open_threads)}")
        print(f"[背景知识] 年代估计: {bg.era_estimate or '未知'} (置信度 {bg.confidence:.2f}) "
              f"| 笔记条数: {len(bg.notes)}")
        print(f"[锚点物件] 候选: \"{anchor.candidate_name or '未确定'}\" "
              f"(提及{anchor.mention_count}次) | 提示词细节分: {anchor.prompt_detail_score:.2f} "
              f"| 已生图: {anchor.image_generated}")

    def dump_outputs(self) -> None:
        (self.output_dir / "logic_outline.json").write_text(
            self.state.logic_outline.model_dump_json(indent=2, exclude={"last_update_mode"}),
            encoding="utf-8",
        )
        (self.output_dir / "background_knowledge.json").write_text(
            self.state.background.model_dump_json(indent=2), encoding="utf-8"
        )
        (self.output_dir / "anchor_object.json").write_text(
            self.state.anchor.model_dump_json(indent=2), encoding="utf-8"
        )
