"""FastAPI 服务:多会话(持久化)+ 统一输入 + 背压分析(路线图「🌐 服务化」)。

- **会话持久化**:WebSessionStore(SQLite)存 id/title/messages/state;后端重启仍在,可续接。
- **会话与输入解耦**:一条会话的 WS 同时接受文字动作与二进制音频帧(录音上传 / 实时麦克风);
  所有"老人"输入(文字 or 转写文本)统一进 CoalescingQueue → SessionWorker(背压)→ 分析。
- **离线大槐树演示**是前端本地回放,不在此持久化会话之列。
- **热配置**:GET/POST /api/config 把 DeepSeek key/base_url 写进运行进程环境(仅内存、不落盘)。

启动:`pip install -e ".[web,asr]"` 后 `uvicorn narrator_flow.server.app:app --reload`(默认 8000)。
真实分析/音频需 DEEPSEEK_API_KEY(可在前端 ⚙️ 热配置,后端可不带 key 冷启动)。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from narrator_flow.state import NarratorFlowState, TranscriptChunk
from narrator_flow.streaming_app.analyzer import Analyzer, LLMPipelines
from narrator_flow.streaming_app.coalescing_queue import CoalescingQueue
from narrator_flow.streaming_app.session_store import InMemorySessionStore
from narrator_flow.streaming_app.worker import SessionWorker

from .store import WebSessionStore

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")  # 读取项目根 .env(DEEPSEEK_API_KEY 等)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_TITLE = "新对话"
ELDER_NAME = "长辈"
SERVER_OUTPUT = Path(os.environ.get("NARRATOR_SERVER_OUTPUT", "output_server"))
WEB_STORE = WebSessionStore(SERVER_OUTPUT / "web_sessions.db")


def _has_key() -> bool:
    return bool(os.environ.get("DEEPSEEK_API_KEY"))


def _timeline(state: NarratorFlowState) -> dict:
    lo = state.logic_outline
    return {
        "events": [e.model_dump() for e in lo.events],
        "open_threads": list(lo.open_threads),
        "last_update_mode": lo.last_update_mode,
        "raw_outline_text": lo.raw_outline_text,
    }


def _state_from(rec: dict) -> NarratorFlowState:
    if rec.get("state_json"):
        return NarratorFlowState.model_validate_json(rec["state_json"])
    return NarratorFlowState()


def _snapshot(sid: str, title: str, messages: list, state: NarratorFlowState) -> dict:
    return {
        "meta": {"id": sid, "title": title, "elder_name": ELDER_NAME},
        "messages": messages,
        "timeline": _timeline(state),
        "eraEstimate": state.background.era_estimate,
        "segmentsPlayed": sum(1 for m in messages if m.get("speaker") == "elder"),
        "totalSegments": 0,
    }


def _derive_title(messages: list, current: str) -> str:
    """标题若仍是默认值,取首条老人发言前 18 字作为会话名。"""
    if current and current != DEFAULT_TITLE:
        return current
    for m in messages:
        if m.get("speaker") == "elder" and m.get("text"):
            t = m["text"].strip()
            return t[:18] + ("…" if len(t) > 18 else "")
    return current


app = FastAPI(title="Generation Memory Bridge API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- 配置(热更新)
class ConfigReq(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/config")
def get_config() -> dict:
    return {"configured": _has_key(), "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)}


@app.post("/api/config")
def set_config(req: ConfigReq) -> dict:
    """从前端热配置 key/base_url —— 写进运行进程环境变量(仅内存、不落盘,绝不回传明文)。"""
    if req.api_key is not None:
        key = req.api_key.strip()
        if key:
            os.environ["DEEPSEEK_API_KEY"] = key
        else:
            os.environ.pop("DEEPSEEK_API_KEY", None)
    if req.base_url is not None and req.base_url.strip():
        os.environ["DEEPSEEK_BASE_URL"] = req.base_url.strip()
    return {"configured": _has_key(), "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)}


# ---------------------------------------------------------------- 会话 CRUD
@app.get("/api/sessions")
def list_sessions() -> list[dict]:
    return WEB_STORE.list()


@app.post("/api/sessions")
def create_session() -> dict:
    sid = uuid.uuid4().hex[:12]
    WEB_STORE.create(sid, DEFAULT_TITLE)
    return {"id": sid, "snapshot": _snapshot(sid, DEFAULT_TITLE, [], NarratorFlowState())}


@app.get("/api/sessions/{sid}")
def get_session(sid: str) -> dict:
    rec = WEB_STORE.get(sid)
    if not rec:
        raise HTTPException(status_code=404, detail="session not found")
    return _snapshot(sid, rec["title"], rec["messages"], _state_from(rec))


@app.delete("/api/sessions/{sid}")
def delete_session(sid: str) -> dict:
    WEB_STORE.delete(sid)
    return {"ok": True}


# ---------------------------------------------------------------- 统一会话 WS
@app.websocket("/ws/sessions/{sid}")
async def ws_session(websocket: WebSocket, sid: str) -> None:
    """一条会话的实时通道:文字动作 + 二进制音频帧;老人输入统一进背压队列 → 分析 → 持久化 → 推快照。"""
    await websocket.accept()
    rec = await asyncio.to_thread(WEB_STORE.get, sid)
    if not rec:
        await websocket.send_json({"type": "error", "message": "session not found"})
        await websocket.close()
        return

    title = rec["title"]
    messages: list[dict] = list(rec["messages"])
    latest_state = _state_from(rec)
    prev_notes = len(latest_state.background.notes)
    mid = max((int(m["id"][1:]) for m in messages
               if isinstance(m.get("id"), str) and m["id"][1:].isdigit()), default=0)

    # 引擎侧:用内存 store 装载已有 state,供 worker 续接分析
    engine_store = InMemorySessionStore()
    await engine_store.save(sid, latest_state)
    analyzer = Analyzer(LLMPipelines(SERVER_OUTPUT / sid))
    queue = CoalescingQueue()
    send_lock = asyncio.Lock()

    def next_id() -> str:
        nonlocal mid
        mid += 1
        return f"m{mid}"

    async def send(payload: dict) -> None:
        async with send_lock:
            await websocket.send_json(payload)

    def persist() -> None:
        nonlocal title
        title = _derive_title(messages, title)
        WEB_STORE.save(sid, title, messages, latest_state.model_dump_json())

    async def push() -> None:
        await send({"type": "snapshot", "snapshot": _snapshot(sid, title, messages, latest_state)})

    async def on_update(state: NarratorFlowState, chunk: TranscriptChunk, batch) -> None:
        nonlocal prev_notes, latest_state
        latest_state = state
        notes = state.background.notes
        messages.append({
            "id": next_id(), "speaker": "elder", "text": chunk.text,
            "backgroundNotes": [{"text": n, "verified": False} for n in notes[prev_notes:]],
            "followUps": list(state.follow_up_questions),
            "coalescedFrom": batch.raw_count,
        })
        prev_notes = len(notes)
        await asyncio.to_thread(persist)
        await push()

    worker = SessionWorker(sid, engine_store, analyzer, queue, on_update)
    worker_task = asyncio.create_task(worker.run())
    await push()  # 初始快照(恢复历史)

    async def feed_elder(text: str) -> bool:
        t = (text or "").strip()
        if not t:
            return True
        if not _has_key():
            await send({"type": "error", "message": "请先配置 API Key(右上角 ⚙️)才能分析"})
            return False
        await queue.put(t)
        return True

    try:
        while True:
            data = await websocket.receive()
            if data.get("type") == "websocket.disconnect":
                break
            blob = data.get("bytes")
            if blob:
                # 音频帧(录音上传 / 麦克风分段):转写后逐段进队列
                if not _has_key():
                    await send({"type": "error", "message": "请先配置 API Key(右上角 ⚙️)才能分析"})
                    continue
                from narrator_flow.streaming_app.asr import transcribe_segments  # 惰性
                seg_path = SERVER_OUTPUT / f"{sid}-{next_id()}.webm"
                await asyncio.to_thread(seg_path.write_bytes, blob)
                try:
                    texts = await asyncio.to_thread(transcribe_segments, str(seg_path))
                except Exception as e:  # noqa: BLE001 — 缺 [asr]/解码失败,回传但不断流
                    await send({"type": "error", "message": str(e)})
                    continue
                for t in texts:
                    await queue.put(t)
            else:
                raw = data.get("text")
                if not raw:
                    continue
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                action = msg.get("type")
                if action == "elder_text":
                    await feed_elder(msg.get("text", ""))
                elif action == "grandchild":
                    t = (msg.get("text") or "").strip()
                    if t:
                        messages.append({"id": next_id(), "speaker": "grandchild", "text": t})
                        await asyncio.to_thread(persist)
                        await push()
    except WebSocketDisconnect:
        pass
    finally:
        await queue.close()
        with contextlib.suppress(Exception):
            await worker_task
