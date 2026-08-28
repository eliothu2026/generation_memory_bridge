"""合并队列（背压核心）的行为测试。免 key、无网络。

队列在 async 上下文里工作；为避免额外依赖（pytest-asyncio），这里用 asyncio.run
驱动一个协程，并把队列创建在协程内部（绑定到运行中的事件循环）。
"""

import asyncio

from narrator_flow.streaming_app.coalescing_queue import CoalescingQueue


def test_single_segment():
    async def go():
        q = CoalescingQueue()
        await q.put("你好")
        return await q.get_coalesced()

    batch = asyncio.run(go())
    assert batch.text == "你好"
    assert batch.raw_count == 1
    assert batch.stop is False


def test_multiple_segments_coalesce_into_one():
    """堆积的多个片段在一次取用时合并为一段——这正是背压的核心行为。"""

    async def go():
        q = CoalescingQueue()
        for s in ("a", "b", "c"):
            await q.put(s)
        return await q.get_coalesced()

    batch = asyncio.run(go())
    assert batch.text == "a b c"
    assert batch.raw_count == 3
    assert batch.stop is False


def test_blank_segments_counted_but_stripped_from_text():
    async def go():
        q = CoalescingQueue()
        for s in ("a", "   ", "b"):
            await q.put(s)
        return await q.get_coalesced()

    batch = asyncio.run(go())
    assert batch.text == "a b"      # 空白片段不进入合并文本
    assert batch.raw_count == 3     # 但仍计入原始片段数（背压可观测性）


def test_close_only_signals_stop():
    async def go():
        q = CoalescingQueue()
        await q.close()             # 只推入结束信号（poison pill）
        return await q.get_coalesced()

    batch = asyncio.run(go())
    assert batch.stop is True
    assert batch.text == ""
    assert batch.raw_count == 0


def test_segment_then_close_coalesced_with_stop():
    """片段后紧跟结束信号：同一批既带内容又带 stop 标志。"""

    async def go():
        q = CoalescingQueue()
        await q.put("末段")
        await q.close()
        return await q.get_coalesced()

    batch = asyncio.run(go())
    assert batch.text == "末段"
    assert batch.raw_count == 1
    assert batch.stop is True


def test_pending_reflects_backlog():
    async def go():
        q = CoalescingQueue()
        await q.put("a")
        await q.put("b")
        return q.pending()

    assert asyncio.run(go()) == 2
