"""FastAPI 服务:把 narrator_flow 引擎包成 HTTP + WebSocket 服务(路线图「🌐 服务化」)。

三条数据源,都**复用现有引擎**,不重造:
- **demo**(免 key):回放大槐树脚本(ReplayPipelines),`next_elder` 逐段推进。
- **real**(需 key):自由输入——`elder_text` 提交任意口述,真实 DeepSeek 现场分析。
- **audio**(需 [asr] + key):上传录音 → faster-whisper 转写 → **背压合并队列 + worker** → 分析。
  即把 `run_stream.py` 那条「producer → CoalescingQueue → SessionWorker → Analyzer」主干接到 WebSocket 上;
  worker 每合并出一段就推快照(带 coalescedFrom = 该段由几个 ASR 片段合并而来)。

前端两/三种数据源共用同一快照结构:meta / messages / timeline / eraEstimate / segmentsPlayed / totalSegments。

启动:`pip install -e ".[web]"` 后 `uvicorn narrator_flow.server.app:app --reload`(默认 8000)。
真实分析 / 音频:先 `export DEEPSEEK_API_KEY=sk-...`(或写进根 .env);音频还需 `pip install -e ".[asr]"`。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from narrator_flow.state import NarratorFlowState, TranscriptChunk
from narrator_flow.streaming import stream_chunks
from narrator_flow.streaming_app.analyzer import Analyzer, LLMPipelines
from narrator_flow.streaming_app.coalescing_queue import CoalescingQueue
from narrator_flow.streaming_app.session import NarratorSession
from narrator_flow.streaming_app.session_store import InMemorySessionStore
from narrator_flow.streaming_app.worker import SessionWorker

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")  # 读取项目根 .env(DEEPSEEK_API_KEY 等),与 main.py / app.py 一致

DEMO_TRANSCRIPT = REPO_ROOT / "data" / "transcripts" / "sample_story.json"
DEMO_TITLE = "大槐树的故事"
DEMO_SUBTITLE = "农村长辈回忆 1970–80 年代"
DEMO_ELDER = "老张"
DEFAULT_ASR_MODEL = "small"
SERVER_OUTPUT = Path(os.environ.get("NARRATOR_SERVER_OUTPUT", "output_server"))


def _require_key() -> None:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise HTTPException(status_code=400, detail="需要真实分析:请在启动后端前设置 DEEPSEEK_API_KEY。")


def _elder_message(mid: str, text: str, state: NarratorFlowState, prev_notes: int,
                   coalesced_from: Optional[int] = None) -> tuple[dict, int]:
    """由当前 state 构造一条老人消息(挂上本段新增背景笔记 + 交互提醒),返回(消息, 新的笔记总数)。"""
    notes = state.background.notes
    msg = {
        "id": mid,
        "speaker": "elder",
        "text": text,
        "backgroundNotes": [{"text": n, "verified": False} for n in notes[prev_notes:]],
        "followUps": list(state.follow_up_questions),
    }
    if coalesced_from is not None:
        msg["coalescedFrom"] = coalesced_from  # 该段由几个 ASR 片段合并(背压可观测)
    return msg, len(notes)


def _timeline(state: NarratorFlowState) -> dict:
    lo = state.logic_outline
    return {
        "events": [e.model_dump() for e in lo.events],
        "open_threads": list(lo.open_threads),
        "last_update_mode": lo.last_update_mode,
        "raw_outline_text": lo.raw_outline_text,
    }


def _make_session(mode: str, sid: str) -> NarratorSession:
    out = SERVER_OUTPUT / sid
    if mode == "real":
        _require_key()
        return NarratorSession(output_dir=out)  # 真实 DeepSeek
    return NarratorSession.demo(output_dir=out, think_delay=0.0)  # 回放,免 key


# ======================================================================
# 交互式会话(demo 脚本 / real 自由文本输入)
# ======================================================================
@dataclass
class ServerSession:
    id: str
    title: str
    subtitle: str
    mode: str  # "demo" | "real"
    session: NarratorSession
    chunks: list[TranscriptChunk]
    scripted: bool = True
    cursor: int = 0
    prev_notes: int = 0
    messages: list[dict] = field(default_factory=list)
    _mid: int = 0

    def _next_id(self) -> str:
        self._mid += 1
        return f"m{self._mid}"

    def _ingest(self, text: str) -> None:
        chunk = TranscriptChunk(index=self.cursor, text=text)
        self.session.process_chunk(chunk)  # demo=回放 / real=真实 DeepSeek
        msg, self.prev_notes = _elder_message(self._next_id(), text, self.session.state, self.prev_notes)
        self.messages.append(msg)
        self.cursor += 1

    def advance_elder(self) -> None:
        if self.cursor < len(self.chunks):
            self._ingest(self.chunks[self.cursor].text)

    def submit_elder(self, text: str) -> None:
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
        return {
            "meta": {"id": self.id, "title": self.title, "subtitle": self.subtitle, "elder_name": DEMO_ELDER},
            "scripted": self.scripted,
            "messages": self.messages,
            "timeline": _timeline(st),
            "eraEstimate": st.background.era_estimate,
            "segmentsPlayed": self.cursor,
            "totalSegments": len(self.chunks),
        }

    def summary(self) -> dict:
        return {"id": self.id, "title": self.title, "mode": self.mode,
                "segmentsPlayed": self.cursor, "totalSegments": len(self.chunks)}


# ======================================================================
# 音频会话(上传 → ASR → 背压合并队列 → 分析),复用 run_stream 的编排
# ======================================================================
@dataclass
class AudioSession:
    id: str
    audio_path: str
    model_size: str
    store: InMemorySessionStore
    analyzer: Analyzer
    state: NarratorFlowState = field(default_factory=NarratorFlowState)
    messages: list[dict] = field(default_factory=list)
    prev_notes: int = 0
    started: bool = False
    _mid: int = 0

    def _next_id(self) -> str:
        self._mid += 1
        return f"m{self._mid}"

    def snapshot(self) -> dict:
        return {
            "meta": {"id": self.id, "title": "录音口述 · 实时分析",
                     "subtitle": "ASR 转写 → 背压合并 → 真实分析", "elder_name": "长辈"},
            "scripted": False,
            "messages": self.messages,
            "timeline": _timeline(self.state),
            "eraEstimate": self.state.background.era_estimate,
            "segmentsPlayed": len(self.messages),
            "totalSegments": 0,  # 自由音频,无固定总数
        }


@dataclass
class MicSession:
    """实时麦克风会话:浏览器分段推音频 → ASR → 背压合并队列 → 分析。"""

    id: str
    store: InMemorySessionStore
    analyzer: Analyzer
    state: NarratorFlowState = field(default_factory=NarratorFlowState)
    messages: list[dict] = field(default_factory=list)
    prev_notes: int = 0
    seg: int = 0
    started: bool = False
    _mid: int = 0

    def _next_id(self) -> str:
        self._mid += 1
        return f"m{self._mid}"

    def snapshot(self) -> dict:
        return {
            "meta": {"id": self.id, "title": "实时麦克风 · 边听边理解",
                     "subtitle": "麦克风 → ASR → 背压合并 → 真实分析", "elder_name": "长辈"},
            "scripted": False,
            "messages": self.messages,
            "timeline": _timeline(self.state),
            "eraEstimate": self.state.background.era_estimate,
            "segmentsPlayed": len(self.messages),
            "totalSegments": 0,
        }


SESSIONS: dict[str, ServerSession] = {}
AUDIO_SESSIONS: dict[str, AudioSession] = {}
MIC_SESSIONS: dict[str, MicSession] = {}


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


def _load_demo_chunks() -> list[TranscriptChunk]:
    return list(stream_chunks(str(DEMO_TRANSCRIPT)))


app = FastAPI(title="Generation Memory Bridge API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


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


@app.post("/api/audio")
async def upload_audio(file: UploadFile = File(...), model_size: str = Form(DEFAULT_ASR_MODEL)) -> dict:
    """上传录音,创建音频会话(转写免 key,但后续分析需 key,故此处即校验)。"""
    _require_key()
    sid = uuid.uuid4().hex[:12]
    SERVER_OUTPUT.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "audio").suffix or ".wav"
    tmp = SERVER_OUTPUT / f"{sid}{suffix}"
    tmp.write_bytes(await file.read())
    a = AudioSession(
        id=sid, audio_path=str(tmp), model_size=model_size,
        store=InMemorySessionStore(), analyzer=Analyzer(LLMPipelines(SERVER_OUTPUT / sid)),
    )
    AUDIO_SESSIONS[sid] = a
    return {"id": sid, "snapshot": a.snapshot()}


@app.websocket("/ws/sessions/{sid}")
async def ws_session(websocket: WebSocket, sid: str) -> None:
    await websocket.accept()
    s = SESSIONS.get(sid)
    if not s:
        await websocket.send_json({"type": "error", "message": "session not found"})
        await websocket.close()
        return
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


@app.websocket("/ws/audio/{sid}")
async def ws_audio(websocket: WebSocket, sid: str) -> None:
    """连上即跑管线:transcribe_file_to_queue(生产者) + SessionWorker(消费者,合并背压)。"""
    await websocket.accept()
    a = AUDIO_SESSIONS.get(sid)
    if not a:
        await websocket.send_json({"type": "error", "message": "audio session not found"})
        await websocket.close()
        return
    await websocket.send_json({"type": "snapshot", "snapshot": a.snapshot()})
    if a.started:  # 幂等:重复连接不重复跑
        return
    a.started = True

    from narrator_flow.streaming_app.asr import transcribe_file_to_queue  # 惰性,避免无 [asr] 影响其他路由

    queue = CoalescingQueue()

    async def on_update(state: NarratorFlowState, chunk: TranscriptChunk, batch) -> None:
        a.state = state
        msg, a.prev_notes = _elder_message(
            a._next_id(), chunk.text, state, a.prev_notes, coalesced_from=batch.raw_count,
        )
        a.messages.append(msg)
        await websocket.send_json({"type": "snapshot", "snapshot": a.snapshot()})

    worker = SessionWorker(a.id, a.store, a.analyzer, queue, on_update)
    producer = transcribe_file_to_queue(queue, a.audio_path, model_size=a.model_size, pacing=0.05)
    try:
        await websocket.send_json({"type": "status", "message": "正在转写音频…(首次会下载语音模型)"})
        # 生产者(ASR→队列)与消费者(合并→分析)同时跑,背压在此显现
        await asyncio.gather(producer, worker.run())
        await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        return
    except Exception as e:  # noqa: BLE001 — faster-whisper 未装 / 模型下载失败 / 分析异常,回传前端
        await websocket.send_json({"type": "error", "message": str(e)})


@app.post("/api/mic")
def create_mic() -> dict:
    """开一个实时麦克风会话(转写免 key,但后续分析需 key,故此处即校验)。"""
    _require_key()
    sid = uuid.uuid4().hex[:12]
    SERVER_OUTPUT.mkdir(parents=True, exist_ok=True)
    m = MicSession(id=sid, store=InMemorySessionStore(),
                   analyzer=Analyzer(LLMPipelines(SERVER_OUTPUT / sid)))
    MIC_SESSIONS[sid] = m
    return {"id": sid, "snapshot": m.snapshot()}


@app.websocket("/ws/mic/{sid}")
async def ws_mic(websocket: WebSocket, sid: str) -> None:
    """浏览器分段推来音频(二进制帧),逐段转写 → 喂背压队列;worker 并发合并分析 → 推快照。

    worker 任务与收流循环并发运行,两者都可能向同一 WS 发送,故用 send_lock 串行化发送。
    """
    await websocket.accept()
    m = MIC_SESSIONS.get(sid)
    if not m:
        await websocket.send_json({"type": "error", "message": "mic session not found"})
        await websocket.close()
        return
    if m.started:
        await websocket.send_json({"type": "snapshot", "snapshot": m.snapshot()})
        return
    m.started = True

    from narrator_flow.streaming_app.asr import transcribe_segments  # 惰性

    queue = CoalescingQueue()
    send_lock = asyncio.Lock()

    async def send(payload: dict) -> None:
        async with send_lock:
            await websocket.send_json(payload)

    async def on_update(state: NarratorFlowState, chunk: TranscriptChunk, batch) -> None:
        m.state = state
        msg, m.prev_notes = _elder_message(
            m._next_id(), chunk.text, state, m.prev_notes, coalesced_from=batch.raw_count,
        )
        m.messages.append(msg)
        await send({"type": "snapshot", "snapshot": m.snapshot()})

    worker = SessionWorker(m.id, m.store, m.analyzer, queue, on_update)
    worker_task = asyncio.create_task(worker.run())
    await send({"type": "snapshot", "snapshot": m.snapshot()})
    try:
        while True:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                break
            blob = data.get("bytes")
            if blob:
                m.seg += 1
                tmp = SERVER_OUTPUT / f"{m.id}-{m.seg}.webm"
                await asyncio.to_thread(tmp.write_bytes, blob)
                try:
                    texts = await asyncio.to_thread(transcribe_segments, str(tmp))
                except Exception as e:  # noqa: BLE001 — 缺 [asr] / 解码失败,回传但不断流
                    await send({"type": "error", "message": str(e)})
                    continue
                for t in texts:
                    await queue.put(t)
            else:
                text = data.get("text")
                if text:
                    with contextlib.suppress(ValueError, TypeError):
                        if json.loads(text).get("type") == "stop":
                            break
    except WebSocketDisconnect:
        pass
    finally:
        await queue.close()
        with contextlib.suppress(Exception):
            await worker_task
    with contextlib.suppress(Exception):
        await send({"type": "done"})
