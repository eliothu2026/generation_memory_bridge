"""状态模型的纯逻辑测试（免 key、无网络）。

覆盖：默认值、JSON 往返（SqliteSessionStore 的持久化依赖它）、字段约束，
以及一条回归测试——确保"背景"不再输出数字置信度（见 docs/product-brief.md 风险 2）。
"""

import pytest
from pydantic import ValidationError

from narrator_flow.state import (
    AnchorObjectState,
    BackgroundKnowledgeState,
    LogicOutlineState,
    NarratorFlowState,
    TimelineEvent,
)


def test_default_state_is_empty():
    st = NarratorFlowState()
    assert st.current_chunk_index == -1
    assert st.background_update_count == 0
    assert st.all_chunks == []
    assert st.full_transcript_text == ""
    assert st.logic_outline.events == []
    assert st.background.notes == []
    assert st.anchor.image_generated is False
    assert st.follow_up_questions == []


def test_state_json_round_trip():
    """model_dump_json → model_validate_json 应无损——这是 SQLite 断点续接的基础。"""
    st = NarratorFlowState(
        full_transcript_text="门口有棵大槐树",
        current_chunk_index=3,
        background_update_count=2,
        logic_outline=LogicOutlineState(
            events=[TimelineEvent(order=1, description="下乡", source_chunk_indices=[0, 1])],
            open_threads=["哪一年下乡？"],
        ),
        background=BackgroundKnowledgeState(era_estimate="约1980年代初", notes=["n1", "n2"]),
        anchor=AnchorObjectState(
            candidate_name="大槐树",
            mention_count=5,
            descriptive_attributes=["树皮裂纹"],
            image_prompt="an old locust tree",
            prompt_detail_score=0.85,
            is_ready_for_generation=True,
        ),
        follow_up_questions=["那棵树现在还在吗？"],
    )
    restored = NarratorFlowState.model_validate_json(st.model_dump_json())
    assert restored == st


def test_prompt_detail_score_is_bounded():
    """prompt_detail_score 约束在 [0, 1]，越界应校验失败。"""
    with pytest.raises(ValidationError):
        AnchorObjectState(prompt_detail_score=1.5)
    with pytest.raises(ValidationError):
        AnchorObjectState(prompt_detail_score=-0.1)


def test_background_has_no_numeric_confidence():
    """回归：曾输出"置信度 0.98"，现改为用措辞表达不确定性。

    背景模型不应再出现任何数字置信度字段（见 docs/product-brief.md 风险 2）。
    """
    fields = set(BackgroundKnowledgeState.model_fields)
    assert fields == {"era_estimate", "notes"}
    assert not any("conf" in f.lower() or "置信" in f for f in fields)
