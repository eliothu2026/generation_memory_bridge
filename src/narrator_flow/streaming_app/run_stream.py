"""CLI 入口：把流式骨架接成一条主干并跑起来。

    producer(模拟ASR) ──▶ CoalescingQueue ──▶ SessionWorker ──▶ SessionStore
                                                  │
                                            Analyzer.analyze
                                            └─ gather(bg, logic, anchor)

用法：
    python -m narrator_flow.streaming_app.run_stream                 # 真实 DeepSeek 流水线
    python -m narrator_flow.streaming_app.run_stream --segment-delay 0.02
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from narrator_flow.state import NarratorFlowState, TranscriptChunk

from .analyzer import Analyzer, CrewPipelines
from .coalescing_queue import CoalescedBatch, CoalescingQueue
from .producer import simulated_asr
from .session_store import InMemorySessionStore
from .worker import SessionWorker


def _make_printer(queue: CoalescingQueue):
    def on_update(state: NarratorFlowState, chunk: TranscriptChunk, batch: CoalescedBatch) -> None:
        o, b, a = state.logic_outline, state.background, state.anchor
        print(f"\n=== 处理第 {chunk.index + 1} 段（由 {batch.raw_count} 个ASR片段合并，"
              f"队列仍堆积 {queue.pending()}）===")
        print(f"  本段文本: {chunk.text[:60]}{'…' if len(chunk.text) > 60 else ''}")
        print(f"  [逻辑] 方式={o.last_update_mode} 事件={len(o.events)} 待澄清={len(o.open_threads)}")
        print(f"  [背景] 年代={b.era_estimate or '未知'}({b.confidence:.2f}) 笔记={len(b.notes)}")
        print(f"  [锚点] {a.candidate_name or '未确定'} 提及{a.mention_count} "
              f"细节分{a.prompt_detail_score:.2f} 已生图={a.image_generated}")
    return on_update


async def main_async(args: argparse.Namespace) -> None:
    load_dotenv()

    store = InMemorySessionStore()
    queue = CoalescingQueue(maxsize=args.queue_maxsize)
    pipelines = CrewPipelines(output_dir=Path(args.output_dir))
    analyzer = Analyzer(pipelines)
    worker = SessionWorker(
        session_id=args.session_id,
        store=store,
        analyzer=analyzer,
        queue=queue,
        on_update=_make_printer(queue),
    )

    # producer 与 worker 同时跑：上游快速喂片段，worker 慢速合并消费
    await asyncio.gather(
        simulated_asr(queue, args.transcript, segment_delay=args.segment_delay),
        worker.run(),
    )

    print("\n=== 完成 ===")
    print(f"会话 {args.session_id} 的最终状态在 store 中；输出快照见 {args.output_dir}/")


def run() -> None:
    parser = argparse.ArgumentParser(description="口述史实时分析 — 流式骨架")
    parser.add_argument("--transcript", default="data/transcripts/sample_story.json")
    parser.add_argument("--session-id", default="default")
    parser.add_argument("--output-dir", default="output_stream")
    parser.add_argument("--segment-delay", type=float, default=0.05,
                        help="模拟 ASR 片段之间的间隔（秒），调小可加剧背压")
    parser.add_argument("--queue-maxsize", type=int, default=1000)
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    run()
