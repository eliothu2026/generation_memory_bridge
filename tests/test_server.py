"""FastAPI 服务的免 key 测试(demo 模式走 ReplayPipelines,不需要 key/网络)。"""

import pytest

pytest.importorskip("fastapi")  # 未安装 [web] 时跳过整个文件

from fastapi.testclient import TestClient  # noqa: E402

from narrator_flow.server.app import SESSIONS, app  # noqa: E402


def test_health():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"ok": True}


def test_create_session_returns_initial_snapshot():
    with TestClient(app) as client:
        r = client.post("/api/sessions", json={"mode": "demo"})
        assert r.status_code == 200
        body = r.json()
        sid = body["id"]
        assert sid in SESSIONS
        snap = body["snapshot"]
        assert snap["totalSegments"] == 18
        assert snap["segmentsPlayed"] == 0
        assert snap["messages"] == []
        assert snap["meta"]["title"]


def test_list_sessions_includes_created():
    with TestClient(app) as client:
        sid = client.post("/api/sessions", json={"mode": "demo"}).json()["id"]
        listing = client.get("/api/sessions").json()
        assert any(s["id"] == sid for s in listing)


def test_ws_advance_and_grandchild():
    with TestClient(app) as client:
        sid = client.post("/api/sessions", json={"mode": "demo"}).json()["id"]
        with client.websocket_connect(f"/ws/sessions/{sid}") as ws:
            first = ws.receive_json()  # 连接即推的初始快照
            assert first["type"] == "snapshot"
            assert first["snapshot"]["segmentsPlayed"] == 0

            # 推进老人第一段:真跑回放引擎
            ws.send_json({"type": "next_elder"})
            snap = ws.receive_json()["snapshot"]
            assert snap["segmentsPlayed"] == 1
            assert len(snap["messages"]) == 1
            msg = snap["messages"][0]
            assert msg["speaker"] == "elder"
            assert msg["text"]  # 老人第一段文本非空
            assert len(msg["followUps"]) >= 1  # 第 0 段自带交互提醒
            assert len(snap["timeline"]["events"]) >= 1  # 第 0 段已有时间线事件

            # 孙辈自由发言
            ws.send_json({"type": "grandchild", "text": "这树现在还在吗？"})
            snap2 = ws.receive_json()["snapshot"]
            last = snap2["messages"][-1]
            assert last["speaker"] == "grandchild"
            assert last["text"] == "这树现在还在吗？"
