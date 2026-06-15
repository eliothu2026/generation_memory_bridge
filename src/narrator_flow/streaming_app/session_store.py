"""会话状态存储。

当前是内存占位实现，但接口（async load/save）刻意按"可序列化的远端存储"
设计，后续换成 Redis / Postgres 时 worker 代码无需改动——这正是 README 待办
里"把 state 序列化到磁盘/数据库，支持加载已有 state 继续对话"的落点。
"""

from __future__ import annotations

import asyncio
from typing import Dict

from narrator_flow.state import NarratorFlowState


class SessionStore:
    """会话存储接口。"""

    async def load(self, session_id: str) -> NarratorFlowState:  # pragma: no cover
        raise NotImplementedError

    async def save(self, session_id: str, state: NarratorFlowState) -> None:  # pragma: no cover
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    """进程内存实现：每个 session_id 一份 NarratorFlowState。

    注意：load 返回的是存储里的活对象，worker 直接原地修改即可；save 在内存
    实现下是幂等占位。换成 Redis/PG 时，load 改为反序列化、save 改为序列化写回，
    worker 调用方式不变。
    """

    def __init__(self) -> None:
        self._states: Dict[str, NarratorFlowState] = {}
        self._lock = asyncio.Lock()

    async def load(self, session_id: str) -> NarratorFlowState:
        async with self._lock:
            return self._states.setdefault(session_id, NarratorFlowState())

    async def save(self, session_id: str, state: NarratorFlowState) -> None:
        async with self._lock:
            self._states[session_id] = state
