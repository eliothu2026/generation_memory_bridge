"""FastAPI 服务:把 narrator_flow 引擎包成 HTTP + WebSocket 服务(路线图「🌐 服务化」)。

两类会话:
- **demo**(免 key):回放大槐树脚本(ReplayPipelines),`next_elder` 逐段推进——用于纯演示前后端链路。
- **real**(需 `DEEPSEEK_API_KEY`):**自由输入**——客户端发 `elder_text` 提交任意一段老人口述,
  后端用真实 DeepSeek 现场分析(时间线/背景/追问),每段约 1–2 分钟。

前端两种数据源(离线 / 后端)共用同一份快照结构:meta / messages / timeline / eraEstimate /
segmentsPlayed / totalSegments。

启动:`pip install -e ".[web]"` 后 `uvicorn narrator_flow.server.app:app --reload`(默认 8000)。
真实分析:启动前 `export DEEPSEEK_API_KEY=sk-...`,前端切「实时(后端)」即建 real 会话。
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
from dotenv import load_dotenv

from narrator_flow.state import TranscriptChunk
from narrator_flow.streaming import stream_chunks
from narrator_flow.streaming_app.session import NarratorSession

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")  # 读取项目根 .env(DEEPSEEK_API_KEY 等),与 main.py / app.py 一致
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
            raise HTTPException(
                status_code=400,
                detail="「实时」需要真实分析:请在启动后端前设置 DEEPSEEK_API_KEY。",
            )
        return NarratorSession(output_dir=out)  # 真实 DeepSeek
    return NarratorSession.demo(output_dir=out, think_delay=0.0)  # 回放,免 key


@dataclass
class ServerSession:
    """一条服务端会话:持有引擎会话 + 已渲染的对话消息。

    scripted=True:demo 会话,老人叙述来自大槐树脚本(next_elder 推进)。
    scripted=False:real 会话,老人叙述由客户端自由输入(elder_text)。
    """

    id: str
    title: str
    subtitle: str
    mode: str  # "demo" | "real"
    session: NarratorSession
    chunks: list[TranscriptChunk]
    scripted: bool = True
    cursor: int = 0
    prev_notes: int = 0  # 上一段处理后的背景笔记总数(用于算本段增量)
    messages: list[dict] = field(default_factory=list)
    _mid: int = 0

    def _next_id(self) -> str:
        self._mid += 1
        return f"m{self._mid}"

    def _ingest(self, text: str) -> None:
        """把一段老人叙述喂给引擎,并把该段的增量补充挂到消息上。"""
        chunk = TranscriptChunk(index=self.cursor, text=text)
        self.session.process_chunk(chunk)  # demo=回放 / real=真实 DeepSeek
        st = self.session.state
        notes = st.background.notes
        new_notes = notes[self.prev_notes:]
        self.prev_notes = len(notes)
        self.messages.append({
            "id": self._next_id(),
            "speaker": "elder",
            "text": text,
            "backgroundNotes": [{"text": n, "verified": False} for n in new_notes],
            "followUps": list(st.follow_up_questions),
        })
        self.cursor += 1

    def advance_elder(self) -> None:
        """脚本模式:推进老人的下一段(大槐树脚本)。"""
        if self.cursor < len(self.chunks):
            self._ingest(self.chunks[self.cursor].text)

    def submit_elder(self, text: str) -> None:
        """自由输入模式:分析用户提交的任意一段老人叙述(real 会话即真实 DeepSeek)。"""
        t = (text or "").strip()
        if t:
            self._ingest(t)

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
                     "subtitle": self.subtitle, "elder_name": DEMO_ELDER},
            "scripted": self.scripted,
            "messages": self.messages,
            "timeline": {
                "events": [e.model_dump() for e in lo.events],
                "open_threads": list(lo.open_threads),
                "last_update_mode": lo.last_update_mode,
                "raw_outline_text": lo.raw_outline_text,
            },
            "eraEstimate": st.background.era_estimate,
            "segmentsPlayed": self.cursor,
            "totalSegments": len(self.chunks),  # real 会话为 0(自由输入,无固定总数)
        }

    def summary(self) -> dict:
        return {"id": self.id, "title": self.title, "mode": self.mode,
                "segmentsPlayed": self.cursor, "totalSegments": len(self.chunks)}


# 进程内会话注册表
SESSIONS: dict[str, ServerSession] = {}


def create_session(mode: str = "demo") -> ServerSession:
    sid = uuid.uuid4().hex[:12]
    scripted = mode == "demo"
    sess = ServerSession(
        id=sid,
        title=DEMO_TITLE if scripted else "自由口述 · 实时分析",
        subtitle=DEMO_SUBTITLE if scripted else "你输入长辈的话,AI 实时整理",
        mode=mode,
        session=_make_session(mode, sid),  # real 无 key 时在此抛 400
        chunks=_load_demo_chunks() if scripted else [],
        scripted=scripted,
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
            # process_chunk 内部用 asyncio.run,不能在事件循环里直接调 → 丢到线程
            if action == "next_elder":
                await asyncio.to_thread(s.advance_elder)
            elif action == "elder_text":
                await asyncio.to_thread(s.submit_elder, msg.get("text", ""))
            elif action == "grandchild":
                s.add_grandchild(msg.get("text", ""))
            elif action == "reset":
                await asyncio.to_thread(s.reset)
            await websocket.send_json({"type": "snapshot", "snapshot": s.snapshot()})
    except WebSocketDisconnect:
        return
