"""NarratorSession：单会话状态的同步增量分析封装。

为什么需要它：流式骨架（worker + queue）是 async 的，适合真实流式服务；但
Streamlit GUI / CLI demo 是"用户点一下、处理一段"的交互式场景，不需要队列和
背压。它们只需要"把分析逻辑套在一个 state 上"。

NarratorSession 就是这个适配层：底层复用 streaming_app 里**唯一一份**流水线逻辑
（Analyzer + CrewPipelines），但对外暴露同步的 process_chunk，方便非 async 调用。
这样旧 flow.py 可以彻底删除，流水线逻辑不再有第二份拷贝。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from narrator_flow.state import NarratorFlowState, TranscriptChunk

from .analyzer import Analyzer, CrewPipelines, Pipelines


class NarratorSession:
    """持有一份 NarratorFlowState，对外提供同步的逐段分析与输出落盘。"""

    def __init__(self, output_dir: str | Path = "output",
                 pipelines: Pipelines | None = None) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state = NarratorFlowState()
        # 默认走真实 LLM（CrewPipelines）；传入 pipelines 可换成回放等其他实现
        self.analyzer = Analyzer(pipelines or CrewPipelines(self.output_dir))

    @classmethod
    def demo(cls, output_dir: str | Path = "output_demo",
             fixture_path: str | Path | None = None,
             think_delay: float = 0.0) -> "NarratorSession":
        """免 key 演示模式：用预录回放，不调用任何 LLM。"""
        from .replay import DEFAULT_FIXTURE, ReplayPipelines
        out = Path(output_dir)
        pipelines = ReplayPipelines(
            fixture_path=fixture_path or DEFAULT_FIXTURE,
            output_dir=out,
            think_delay=think_delay,
        )
        return cls(output_dir=out, pipelines=pipelines)

    def process_chunk(self, chunk: TranscriptChunk) -> None:
        """同步处理一段：内部跑一次 async 的三流水线并发分析。"""
        asyncio.run(self.analyzer.analyze(self.state, chunk))

    # ------------------------------------------------------------------
    # 输出展示与持久化（从旧 flow.py 迁移过来）
    # ------------------------------------------------------------------
    def format_progress(self, chunk: TranscriptChunk, total: Optional[int] = None) -> str:
        o, b, a = self.state.logic_outline, self.state.background, self.state.anchor
        total = total if total is not None else len(self.state.all_chunks)
        return (
            f"\n=== Chunk {chunk.index + 1}/{total} ===\n"
            f"[逻辑大纲] 更新方式: {o.last_update_mode or 'incremental'} "
            f"| 当前事件数: {len(o.events)} | 待澄清: {len(o.open_threads)}\n"
            f"[背景知识] 年代估计: {b.era_estimate or '未知'} (置信度 {b.confidence:.2f}) "
            f"| 笔记条数: {len(b.notes)}\n"
            f"[锚点物件] 候选: \"{a.candidate_name or '未确定'}\" (提及{a.mention_count}次) "
            f"| 提示词细节分: {a.prompt_detail_score:.2f} | 已生图: {a.image_generated}"
        )

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
