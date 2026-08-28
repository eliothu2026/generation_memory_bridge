"""InMemorySessionStore 的纯逻辑测试（免 key、无网络）。

SQLite 实现涉及磁盘 IO，这里只测内存实现的语义（load 默认、save/load 往返、
会话隔离）；两种实现共享同一接口契约。
"""

import asyncio

from narrator_flow.state import NarratorFlowState
from narrator_flow.streaming_app.session_store import InMemorySessionStore


def test_load_unknown_returns_default_state():
    async def go():
        store = InMemorySessionStore()
        return await store.load("new-session")

    st = asyncio.run(go())
    assert isinstance(st, NarratorFlowState)
    assert st.current_chunk_index == -1


def test_save_then_load_round_trip():
    async def go():
        store = InMemorySessionStore()
        st = await store.load("s1")
        st.current_chunk_index = 7
        st.full_transcript_text = "hello"
        await store.save("s1", st)
        return await store.load("s1")

    loaded = asyncio.run(go())
    assert loaded.current_chunk_index == 7
    assert loaded.full_transcript_text == "hello"


def test_sessions_are_isolated():
    async def go():
        store = InMemorySessionStore()
        a = await store.load("a")
        a.current_chunk_index = 3
        await store.save("a", a)
        b = await store.load("b")
        return a.current_chunk_index, b.current_chunk_index

    a_idx, b_idx = asyncio.run(go())
    assert a_idx == 3
    assert b_idx == -1   # 不同会话彼此独立
