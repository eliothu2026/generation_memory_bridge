"""FastAPI 服务:把 narrator_flow 引擎包成 HTTP + WebSocket 服务(路线图「🌐 服务化」)。

- **免 key**:demo 会话用 `NarratorSession.demo()`(ReplayPipelines)——真跑引擎、逐段回放,不调 LLM。
- **有 key**:`mode="real"` 用真实 DeepSeek(逐段 1–2 分钟,需 `DEEPSEEK_API_KEY`)。
- REST 建/查会话;WebSocket 逐段推进老人叙述并回推快照。

前端两种数据源(离线 / 后端)共用同一份快照结构,因此后端返回的 snapshot 字段与前端
`SessionSnapshot` 一一对应(meta / messages / timeline / eraEstimate / segmentsPlayed / totalSegments)。

启动:`pip install -e ".[web]"` 后 `uvicorn narrator_flow.server.app:app --reload`(默认 8000 端口)。
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from narrator_flow.state import TranscriptChunk
from narrator_flow.streaming import stream_chunks
from narrator_flow.streaming_app.session import NarratorSession

REPO_ROOT = Path(__file__).resolve().parents[3]
DEMO_TRANSCRIPT = REPO_ROOT / "data" / "transcripts" / "sample_story.json"
DEMO_TITLE = "大槐树的故事"
DEMO_SUBTITLE = "农村长辈回忆 1970–80 年代"
DEMO_ELDER = "老张"
SERVER_OUTPUT = Path(os.environ.get("NARRATOR_SERVER_OUTPUT", "output_server"))


def _load_demo_chunks() -> list[TranscriptChunk]:
    return list(stream_chunks(str(DEMO_TRANSCRIPT)))


def _make_session(mode: str, sid: str) -> NarratorSession:
    out = SERVER_OUTPUT / sid
    if mode == "real":
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise HTTPException(status_code=400, detail="real 模式需要设置 DEEPSEEK_API_KEY")
        return NarratorSession(output_dir=out)
    return NarratorSession.demo(output_dir=out, think_delay=0.0)


@dataclass
class ServerSession:
    """一条服务端会话:持有引擎会话 + 脚本化的老人分段 + 已渲染的对话消息。"""

    id: str
    title: str
    mode: str  # "demo" | "real"
    session: NarratorSession
    chunks: list[TranscriptChunk]
    cursor: int = 0
    prev_notes: int = 0  # 上一段处理后的背景笔记总数(用于算本段增量)
    messages: list[dict] = field(default_factory=list)
    _mid: int = 0

    def _next_id(self) -> str:
        self._mid += 1
        return f"m{self._mid}"

    def advance_elder(self) -> None:
        """推进老人的下一段叙述——真跑引擎,并把该段的增量补充挂到消息上。"""
        if self.cursor >= len(self.chunks):
            return
        chunk = self.chunks[self.cursor]
        self.session.process_chunk(chunk)  # demo=回放 / real=DeepSeek
        st = self.session.state
        notes = st.background.notes
        new_notes = notes[self.prev_notes:]
        self.prev_notes = len(notes)
        self.messages.append({
            "id": self._next_id(),
            "speaker": "elder",
            "text": chunk.text,
            "backgroundNotes": [{"text": n, "verified": False} for n in new_notes],
            "followUps": list(st.follow_up_questions),
        })
        self.cursor += 1

    def add_grandchild(self, text: str) -> None:
        t = (text or "").strip()
        if t:
            self.messages.append({"id": self._next_id(), "speaker": "grandchild", "text": t})

    def reset(self) -> None:
        self.session = _make_session(self.mode, self.id)
        self.cursor = 0
        self.prev_notes = 0
        self.messages = []

    def snapshot(self) -> dict:
        st = self.session.state
        lo = st.logic_outline
        return {
            "meta": {"id": self.id, "title": self.title,
                     "subtitle": DEMO_SUBTITLE, "elder_name": DEMO_ELDER},
            "messages": self.messages,
            "timeline": {
                "events": [e.model_dump() for e in lo.events],
                "open_threads": list(lo.open_threads),
                "last_update_mode": lo.last_update_mode,
                "raw_outline_text": lo.raw_outline_text,
            },
            "eraEstimate": st.background.era_estimate,
            "segmentsPlayed": self.cursor,
            "totalSegments": len(self.chunks),
        }

    def summary(self) -> dict:
        return {"id": self.id, "title": self.title, "mode": self.mode,
                "segmentsPlayed": self.cursor, "totalSegments": len(self.chunks)}


# 进程内会话注册表(demo 用;真实持久化可换 SqliteSessionStore.list_sessions)
SESSIONS: dict[str, ServerSession] = {}


def create_session(mode: str = "demo") -> ServerSession:
    sid = uuid.uuid4().hex[:12]
    sess = ServerSession(
        id=sid, title=DEMO_TITLE, mode=mode,
        session=_make_session(mode, sid), chunks=_load_demo_chunks(),
    )
    SESSIONS[sid] = sess
    return sess


app = FastAPI(title="Generation Memory Bridge API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class CreateReq(BaseModel):
    mode: str = "demo"


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/sessions")
def list_sessions() -> list[dict]:
    return [s.summary() for s in SESSIONS.values()]


@app.post("/api/sessions")
def create(req: Optional[CreateReq] = None) -> dict:
    s = create_session(req.mode if req else "demo")
    return {"id": s.id, "snapshot": s.snapshot()}


@app.get("/api/sessions/{sid}")
def get_session(sid: str) -> dict:
    s = SESSIONS.get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    return s.snapshot()


@app.websocket("/ws/sessions/{sid}")
async def ws_session(websocket: WebSocket, sid: str) -> None:
    await websocket.accept()
    s = SESSIONS.get(sid)
    if not s:
        await websocket.send_json({"type": "error", "message": "session not found"})
        await websocket.close()
        return
    # 连接即推初始快照
    await websocket.send_json({"type": "snapshot", "snapshot": s.snapshot()})
    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("type")
            if action == "next_elder":
                # process_chunk 内部用 asyncio.run,不能在事件循环里直接调 → 丢到线程
                await asyncio.to_thread(s.advance_elder)
            elif action == "grandchild":
                s.add_grandchild(msg.get("text", ""))
            elif action == "reset":
                await asyncio.to_thread(s.reset)
            await websocket.send_json({"type": "snapshot", "snapshot": s.snapshot()})
    except WebSocketDisconnect:
        return
