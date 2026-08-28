"""FastAPI 服务的免 key 测试(会话 CRUD、WS 持久化、无 key 报错)。

真实 DeepSeek 分析 / ASR 转写无法在无 key / 无音频环境验证,这里覆盖:
配置热更新、会话增删查、WS 孙辈发言的持久化、以及老人输入缺 key 时的报错。
"""

import os

import pytest

pytest.importorskip("fastapi")  # 未安装 [web] 时跳过整个文件

from fastapi.testclient import TestClient  # noqa: E402

from narrator_flow.server.app import app  # noqa: E402


def test_health():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"ok": True}


def test_config_set_reports_configured(monkeypatch):
    """从前端热配置 key:POST 后 GET 应报 configured=True(不回传 key 明文)。"""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/config").json()["configured"] is False
        r = client.post("/api/config", json={"api_key": "sk-test", "base_url": "https://example.com"})
        assert r.status_code == 200
        body = r.json()
        assert body["configured"] is True and body["base_url"] == "https://example.com"
        assert "sk-test" not in str(body)  # 绝不回传明文 key
    os.environ.pop("DEEPSEEK_API_KEY", None)
    os.environ.pop("DEEPSEEK_BASE_URL", None)


def test_session_crud():
    """新建 → 列表可见 → 取详情 → 删除 → 列表消失。"""
    with TestClient(app) as client:
        r = client.post("/api/sessions")
        assert r.status_code == 200
        sid = r.json()["id"]
        assert r.json()["snapshot"]["messages"] == []
        try:
            assert client.get(f"/api/sessions/{sid}").json()["meta"]["id"] == sid
            assert any(s["id"] == sid for s in client.get("/api/sessions").json())
        finally:
            assert client.delete(f"/api/sessions/{sid}").json()["ok"] is True
        assert not any(s["id"] == sid for s in client.get("/api/sessions").json())


def test_ws_grandchild_persists():
    """孙辈发言应追加并持久化;重连(GET)仍能取回。"""
    with TestClient(app) as client:
        sid = client.post("/api/sessions").json()["id"]
        try:
            with client.websocket_connect(f"/ws/sessions/{sid}") as ws:
                first = ws.receive_json()
                assert first["type"] == "snapshot"
                ws.send_json({"type": "grandchild", "text": "你好爷爷"})
                snap = ws.receive_json()["snapshot"]
                assert snap["messages"][-1]["speaker"] == "grandchild"
                assert snap["messages"][-1]["text"] == "你好爷爷"
            reget = client.get(f"/api/sessions/{sid}").json()
            assert any(m["text"] == "你好爷爷" for m in reget["messages"])
        finally:
            client.delete(f"/api/sessions/{sid}")


def test_ws_elder_without_key_errors(monkeypatch):
    """老人输入需要真实分析;缺 key 时应回传错误而非静默。"""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with TestClient(app) as client:
        sid = client.post("/api/sessions").json()["id"]
        try:
            with client.websocket_connect(f"/ws/sessions/{sid}") as ws:
                ws.receive_json()  # 初始快照
                ws.send_json({"type": "elder_text", "text": "门口有棵大槐树"})
                msg = ws.receive_json()
                assert msg["type"] == "error"
                assert "API Key" in msg["message"]
        finally:
            client.delete(f"/api/sessions/{sid}")
