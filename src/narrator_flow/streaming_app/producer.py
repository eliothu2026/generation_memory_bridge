"""模拟 ASR 流式输入。

真实产品里这里接的是 ASR 引擎的 partial/final 结果。骨架阶段我们从预录
transcript 读段落，并按中文句末标点切成更小的"亚秒级片段"，以亚秒间隔推入
队列——刻意制造"上游快、下游慢"的吞吐错配，好让合并队列的背压行为显现出来。
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import List

from .coalescing_queue import CoalescingQueue

_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])")


def _split_into_segments(text: str) -> List[str]:
    """把一段话按句末标点切成更小的片段，模拟 ASR 的连续 partial 输出。"""
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p and p.strip()]
    return parts or [text.strip()]


async def simulated_asr(
    queue: CoalescingQueue,
    transcript_path: str,
    segment_delay: float = 0.05,
    split: bool = True,
) -> None:
    """读取 transcript，逐个亚秒级片段推入队列，结束时推入 stop 信号。"""
    data = json.loads(Path(transcript_path).read_text(encoding="utf-8"))
    for raw in data["chunks"]:
        segments = _split_into_segments(raw["text"]) if split else [raw["text"]]
        for seg in segments:
            if segment_delay > 0:
                await asyncio.sleep(segment_delay)
            await queue.put(seg)
    await queue.close()
