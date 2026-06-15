"""单会话 worker：消费合并队列，驱动分析，落库。

一个 session 对应一个 worker 协程。真实产品里"多会话并发"就是起多个
SessionWorker（各自一个 queue + 共享 store/限流的 LLM 客户端池），这里先把
单会话主干跑通。
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Optional

from narrator_flow.state import NarratorFlowState, TranscriptChunk

from .analyzer import Analyzer
from .coalescing_queue import CoalescedBatch, CoalescingQueue
from .session_store import SessionStore

logger = logging.getLogger(__name__)

# 处理完一段后的回调：拿到最新 state、刚处理的 chunk、以及合并批次信息
OnUpdate = Callable[[NarratorFlowState, TranscriptChunk, CoalescedBatch], Optional[Awaitable[None]]]


class SessionWorker:
    def __init__(
        self,
        session_id: str,
        store: SessionStore,
        analyzer: Analyzer,
        queue: CoalescingQueue,
        on_update: Optional[OnUpdate] = None,
    ) -> None:
        self.session_id = session_id
        self.store = store
        self.analyzer = analyzer
        self.queue = queue
        self.on_update = on_update

    async def run(self) -> None:
        while True:
            batch = await self.queue.get_coalesced()

            # 即使收到 stop，也要把本批已合并的文本处理完再退出（不丢数据）
            if batch.text:
                await self._process(batch)

            if batch.stop:
                logger.info("[%s] 收到结束信号，worker 退出", self.session_id)
                return

    async def _process(self, batch: CoalescedBatch) -> None:
        state = await self.store.load(self.session_id)
        chunk = TranscriptChunk(index=state.current_chunk_index + 1, text=batch.text)
        try:
            await self.analyzer.analyze(state, chunk)
        except Exception:  # noqa: BLE001 — 单段失败不该拖垮整个会话
            logger.exception("[%s] chunk %d 分析失败，跳过本段", self.session_id, chunk.index)
            return
        await self.store.save(self.session_id, state)

        if self.on_update is not None:
            res = self.on_update(state, chunk, batch)
            if res is not None:
                await res
