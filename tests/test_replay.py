"""免 key 回放流水线的端到端测试（全程不调用任何 LLM）。

用仓库自带的预录快照跑完全部 18 段，断言三条流水线累积出结果、并真的落地一个
(stub) 生图文件。这同时守护了 fixture 文件的完整性。
"""

import asyncio
from pathlib import Path

from narrator_flow.state import NarratorFlowState, TranscriptChunk
from narrator_flow.streaming_app.replay import ReplayPipelines

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "demo_replay" / "sample_story.replay.json"


def _run_full_replay(output_dir) -> NarratorFlowState:
    rp = ReplayPipelines(fixture_path=FIXTURE, output_dir=output_dir, think_delay=0.0)
    state = NarratorFlowState()

    async def go():
        for i in sorted(rp.snapshots):
            chunk = TranscriptChunk(index=i, text=f"chunk-{i}")
            await rp.logic(state, chunk)
            await rp.background(state, chunk)
            await rp.anchor(state, chunk)
            await rp.follow_up(state, chunk)

    asyncio.run(go())
    return state


def test_replay_accumulates_and_generates_image(tmp_path):
    state = _run_full_replay(tmp_path)

    # 逻辑与背景两条流水线都累积出了内容
    assert len(state.logic_outline.events) > 0
    assert len(state.background.notes) > 0

    # 记忆锚点最终触发了 (stub) 生图，并真的落地了文件
    assert state.anchor.image_generated is True
    assert state.anchor.image_path is not None
    img = Path(state.anchor.image_path)
    assert img.exists()
    assert "STUB IMAGE" in img.read_text(encoding="utf-8")


def test_fixture_has_expected_snapshot_count(tmp_path):
    rp = ReplayPipelines(fixture_path=FIXTURE, output_dir=tmp_path, think_delay=0.0)
    # 预录 18 段（索引 0..17）；若日后调整 fixture，此断言会提示同步更新
    assert sorted(rp.snapshots) == list(range(18))
