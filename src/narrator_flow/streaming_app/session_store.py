"""会话状态存储。

接口（async load/save）按"可序列化的远端存储"设计，worker 不关心背后是内存、
SQLite 还是 Redis/Postgres——换后端时 worker 代码无需改动。

- InMemorySessionStore：进程内存，重启即丢（测试/演示用）
- SqliteSessionStore：序列化到本地 SQLite 文件，进程崩溃/重启后可续接（默认）

这正是 README 待办①"把 state 序列化到磁盘/数据库，支持加载已有 state 继续对话"
的落点。SQLite 同步 API 用 asyncio.to_thread 包装，避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
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


class SqliteSessionStore(SessionStore):
    """SQLite 持久化实现：每个 session_id 一行，存序列化后的 state JSON。

    worker 每段 load→分析→save，因此每段都会落盘一次；进程崩溃/重启后用同一个
    session_id 再跑，load 会读回上次的 state，从中断处继续（current_chunk_index
    会接着往后递增）。SQLite 连接每次操作新建，避免跨线程共享带来的线程安全问题。
    """

    def __init__(self, db_path: str | Path = "sessions.db") -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sessions ("
                "  session_id TEXT PRIMARY KEY,"
                "  state_json TEXT NOT NULL,"
                "  updated_at TEXT NOT NULL"
                ")"
            )

    async def load(self, session_id: str) -> NarratorFlowState:
        return await asyncio.to_thread(self._load_sync, session_id)

    def _load_sync(self, session_id: str) -> NarratorFlowState:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return NarratorFlowState()
        return NarratorFlowState.model_validate_json(row[0])

    async def save(self, session_id: str, state: NarratorFlowState) -> None:
        await asyncio.to_thread(self._save_sync, session_id, state)

    def _save_sync(self, session_id: str, state: NarratorFlowState) -> None:
        payload = state.model_dump_json()
        ts = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, state_json, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "  state_json = excluded.state_json, updated_at = excluded.updated_at",
                (session_id, payload, ts),
            )
