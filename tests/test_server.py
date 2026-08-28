"""FastAPI 服务的免 key 测试(demo 模式走 ReplayPipelines,不需要 key/网络)。

real 模式的真实 DeepSeek 分析无法在无 key 环境验证,这里只覆盖:
demo 会话的建立/列表/WS 推进、自由输入(elder_text)的路由,以及 real 无 key 时的 400 防呆。
"""

import pytest

pytest.importorskip("fastapi")  # 未安装 [web] 时跳过整个文件

from fastapi.testclient import TestClient  # noqa: E402

from narrator_flow.server.app import SESSIONS, app  # noqa: E402


def test_health():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"ok": True}


def test_create_demo_session_returns_initial_snapshot():
    with TestClient(app) as client:
        r = client.post("/api/sessions", json={"mode": "demo"})
        assert r.status_code == 200
        body = r.json()
        sid = body["id"]
        assert sid in SESSIONS
        snap = body["snapshot"]
        assert snap["totalSegments"] == 18  # 大槐树脚本 18 段
        assert snap["segmentsPlayed"] == 0
        assert snap["messages"] == []
        assert snap["meta"]["title"]


def test_list_sessions_includes_created():
    with TestClient(app) as client:
        sid = client.post("/api/sessions", json={"mode": "demo"}).json()["id"]
        listing = client.get("/api/sessions").json()
        assert any(s["id"] == sid for s in listing)


def test_real_session_without_key_returns_400(monkeypatch):
    """real 会话需要 DEEPSEEK_API_KEY;缺 key 时应 400 防呆,而不是崩。"""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with TestClient(app) as client:
        r = client.post("/api/sessions", json={"mode": "real"})
        assert r.status_code == 400


def test_audio_upload_without_key_returns_400(monkeypatch):
    """音频分析同样需要 key;缺 key 时上传应 400(转写免 key,但后续分析需要)。"""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with TestClient(app) as client:
        r = client.post("/api/audio", files={"file": ("t.wav", b"RIFFxxxx", "audio/wav")})
        assert r.status_code == 400


def test_ws_advance_scripted_and_grandchild():
    with TestClient(app) as client:
        sid = client.post("/api/sessions", json={"mode": "demo"}).json()["id"]
        with client.websocket_connect(f"/ws/sessions/{sid}") as ws:
            first = ws.receive_json()  # 连接即推的初始快照
            assert first["type"] == "snapshot"
            assert first["snapshot"]["segmentsPlayed"] == 0

            ws.send_json({"type": "next_elder"})  # 脚本推进第一段
            snap = ws.receive_json()["snapshot"]
            assert snap["segmentsPlayed"] == 1
            assert len(snap["messages"]) == 1
            msg = snap["messages"][0]
            assert msg["speaker"] == "elder"
            assert msg["text"]
            assert len(msg["followUps"]) >= 1  # 第 0 段自带交互提醒
            assert len(snap["timeline"]["events"]) >= 1

            ws.send_json({"type": "grandchild", "text": "这树现在还在吗？"})
            snap2 = ws.receive_json()["snapshot"]
            assert snap2["messages"][-1]["speaker"] == "grandchild"
            assert snap2["messages"][-1]["text"] == "这树现在还在吗？"


def test_ws_elder_text_appends_elder_message():
    """自由输入(elder_text)应把该段作为老人消息追加(此处 demo 会话验证路由)。"""
    with TestClient(app) as client:
        sid = client.post("/api/sessions", json={"mode": "demo"}).json()["id"]
        with client.websocket_connect(f"/ws/sessions/{sid}") as ws:
            ws.receive_json()  # 初始快照
            ws.send_json({"type": "elder_text", "text": "测试口述"})
            snap = ws.receive_json()["snapshot"]
            assert snap["segmentsPlayed"] == 1
            assert snap["messages"][-1]["speaker"] == "elder"
            assert snap["messages"][-1]["text"] == "测试口述"
