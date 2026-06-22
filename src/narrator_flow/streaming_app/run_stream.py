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

from .analyzer import Analyzer, LLMPipelines
from .coalescing_queue import CoalescedBatch, CoalescingQueue
from .producer import simulated_asr
from .session_store import InMemorySessionStore, SqliteSessionStore
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

    if args.store == "sqlite":
        store = SqliteSessionStore(db_path=args.db_path)
        print(f"[存储] SQLite: {args.db_path}（会话 {args.session_id} 可断点续接）")
    else:
        store = InMemorySessionStore()
        print("[存储] 内存（进程退出即丢失）")

    queue = CoalescingQueue(maxsize=args.queue_maxsize)
    if args.demo:
        from .replay import ReplayPipelines
        print("[免 key 演示] 回放预录结果，不调用 DeepSeek。")
        pipelines = ReplayPipelines(output_dir=Path(args.output_dir), think_delay=0.2)
    else:
        pipelines = LLMPipelines(output_dir=Path(args.output_dir))
    analyzer = Analyzer(pipelines)
    worker = SessionWorker(
        session_id=args.session_id,
        store=store,
        analyzer=analyzer,
        queue=queue,
        on_update=_make_printer(queue),
    )

    # 选择输入 producer：给了 --audio 用真实 ASR，否则用模拟文本流
    if args.audio:
        from .asr import transcribe_file_to_queue
        print(f"[ASR] 真实语音识别：{args.audio}（模型 {args.asr_model}）")
        producer = transcribe_file_to_queue(
            queue, args.audio, model_size=args.asr_model,
            language=args.asr_language, pacing=args.segment_delay,
        )
    else:
        producer = simulated_asr(queue, args.transcript, segment_delay=args.segment_delay)

    # producer 与 worker 同时跑：上游喂片段，worker 合并消费
    await asyncio.gather(producer, worker.run())

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
    parser.add_argument("--store", choices=["sqlite", "memory"], default="sqlite",
                        help="会话存储后端：sqlite=可断点续接(默认)，memory=退出即丢")
    parser.add_argument("--db-path", default="output_stream/sessions.db",
                        help="SQLite 数据库文件路径（--store sqlite 时生效）")
    parser.add_argument("--demo", action="store_true",
                        help="免 key 演示：回放预录结果，不调用任何 LLM")
    parser.add_argument("--audio", default=None,
                        help="音频文件路径；给定后用真实 ASR（faster-whisper）替代模拟文本输入")
    parser.add_argument("--asr-model", default="small",
                        help="faster-whisper 模型大小：tiny/base/small/medium/large")
    parser.add_argument("--asr-language", default="zh", help="识别语言，默认中文 zh")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    run()
