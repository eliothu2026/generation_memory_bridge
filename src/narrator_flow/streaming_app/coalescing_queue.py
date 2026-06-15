"""有界队列 + 合并策略 —— 背压的核心。

问题：真实 ASR 是亚秒级持续吐字，而单段分析要 1-2 分钟（3 次 LLM 调用），
两者吞吐相差 100 倍以上。绝不能对每个 ASR 片段都跑一遍流水线。

策略：worker 忙的时候到达的片段在队列里堆积；当 worker 空闲来取时，把当前
**已堆积的所有片段一次性排空并合并成一段**再交给分析。这样每个 worker-free
时刻只产出一段待分析文本，把"分析次数"与"上游速率"彻底解耦——上游再快，
也只是让单段合并得更长，而不是排起一条每个等 1-2 分钟的长队。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass
class CoalescedBatch:
    """一次取用得到的合并结果。"""

    text: str
    raw_count: int  # 本段由多少个原始 ASR 片段合并而来（背压可观测性）
    stop: bool = False  # 是否收到了结束信号


class CoalescingQueue:
    """有界 async 队列，取用时合并所有待处理片段。

    put(None) 作为结束信号（poison pill）。
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: asyncio.Queue[Optional[str]] = asyncio.Queue(maxsize=maxsize)

    async def put(self, segment: Optional[str]) -> None:
        await self._queue.put(segment)

    async def close(self) -> None:
        """推入结束信号。"""
        await self._queue.put(None)

    async def get_coalesced(self) -> CoalescedBatch:
        """阻塞直到至少有一个片段，然后排空当前所有片段合并成一段返回。"""
        first = await self._queue.get()
        if first is None:
            return CoalescedBatch(text="", raw_count=0, stop=True)

        segments = [first]
        stop = False
        # 非阻塞排空当前已到达的其余片段
        while True:
            try:
                item = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if item is None:
                stop = True
                break
            segments.append(item)

        text = " ".join(s.strip() for s in segments if s and s.strip())
        return CoalescedBatch(text=text, raw_count=len(segments), stop=stop)

    def pending(self) -> int:
        """当前堆积的片段数（用于观测背压）。"""
        return self._queue.qsize()
