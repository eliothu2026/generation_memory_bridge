"""Web 会话持久化(SQLite)。

与引擎的 session_store.py **解耦、互不影响**:那个存纯 NarratorFlowState(用于流式续接);
这个面向 Web 多会话管理,存前端要展示与恢复的一切——标题、对话消息、以及分析状态。

一条 web 会话:
- id / title / created_at / updated_at
- messages_json:前端对话消息数组(老人/孙辈气泡,含背景补充/追问/合并数)
- state_json:该会话的 NarratorFlowState(便于继续分析时基于既有积累)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WebSessionStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS web_sessions ("
                "  id TEXT PRIMARY KEY,"
                "  title TEXT NOT NULL,"
                "  created_at TEXT NOT NULL,"
                "  updated_at TEXT NOT NULL,"
                "  messages_json TEXT NOT NULL DEFAULT '[]',"
                "  state_json TEXT"
                ")"
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def list(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, created_at, updated_at, messages_json "
                "FROM web_sessions ORDER BY updated_at DESC"
            ).fetchall()
        out: list[dict] = []
        for r in rows:
            try:
                count = len(json.loads(r[4] or "[]"))
            except (ValueError, TypeError):
                count = 0
            out.append({"id": r[0], "title": r[1], "created_at": r[2],
                        "updated_at": r[3], "message_count": count})
        return out

    def get(self, sid: str) -> Optional[dict]:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT id, title, created_at, updated_at, messages_json, state_json "
                "FROM web_sessions WHERE id = ?", (sid,)
            ).fetchone()
        if not r:
            return None
        return {"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3],
                "messages": json.loads(r[4] or "[]"), "state_json": r[5]}

    def create(self, sid: str, title: str) -> None:
        t = _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO web_sessions (id, title, created_at, updated_at, messages_json, state_json) "
                "VALUES (?, ?, ?, ?, '[]', NULL)",
                (sid, title, t, t),
            )

    def save(self, sid: str, title: str, messages: list, state_json: Optional[str]) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE web_sessions SET title = ?, updated_at = ?, messages_json = ?, state_json = ? "
                "WHERE id = ?",
                (title, _now(), json.dumps(messages, ensure_ascii=False), state_json, sid),
            )

    def delete(self, sid: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM web_sessions WHERE id = ?", (sid,))
