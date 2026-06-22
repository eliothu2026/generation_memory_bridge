"""Pydantic state models for the NarratorFlow."""

from typing import List, Optional

from pydantic import BaseModel, Field


class TranscriptChunk(BaseModel):
    """A single piece of incoming narration (simulated streaming input)."""

    index: int
    text: str


class TimelineEvent(BaseModel):
    """A single event reconstructed from the narrator's story."""

    order: int = Field(description="推断出的时间顺序，数字越小越早")
    period_hint: Optional[str] = Field(
        default=None, description="推断出的大致时间，如 '约1980年代初'"
    )
    description: str = Field(description="事件描述")
    cause: Optional[str] = Field(default=None, description="原因（如有）")
    effect: Optional[str] = Field(default=None, description="结果/影响（如有）")
    source_chunk_indices: List[int] = Field(
        default_factory=list, description="该事件来自哪些段落"
    )


class LogicOutlineState(BaseModel):
    """流水线A：逻辑/时间线大纲状态。"""

    events: List[TimelineEvent] = Field(default_factory=list)
    open_threads: List[str] = Field(
        default_factory=list, description="尚未澄清、需要后续内容补充的线索"
    )
    raw_outline_text: str = Field(default="", description="人类可读的大纲文本（markdown）")
    last_update_mode: Optional[str] = Field(
        default=None,
        description="本次更新所采用的模式：incremental / refine / full_rerun（仅供展示，非LLM输出字段）",
    )


class BackgroundKnowledgeState(BaseModel):
    """流水线B：时代/社会背景知识状态（纯增量）。"""

    era_estimate: Optional[str] = Field(default=None, description="对年代/地域背景的估计")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="对年代估计的置信度")
    notes: List[str] = Field(default_factory=list, description="背景知识笔记列表，只增不减")


class AnchorObjectState(BaseModel):
    """流水线C：叙事锚定物 + 图像生成提示词状态。"""

    candidate_name: Optional[str] = Field(default=None, description="当前候选锚定物名称")
    mention_count: int = Field(default=0, description="该锚定物被提及的次数")
    descriptive_attributes: List[str] = Field(
        default_factory=list, description="已知的视觉细节描述列表"
    )
    image_prompt: str = Field(default="", description="当前的英文图像生成提示词")
    prompt_detail_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="提示词详实程度评分（0-1）"
    )
    is_ready_for_generation: bool = Field(default=False, description="是否已可以触发生图")
    image_generated: bool = Field(default=False, description="是否已生成过图像")
    image_path: Optional[str] = Field(default=None, description="生成图像（或占位文件）的路径")


class NarratorFlowState(BaseModel):
    """NarratorFlow 的完整运行状态。"""

    all_chunks: List[TranscriptChunk] = Field(default_factory=list)
    current_chunk_index: int = -1
    full_transcript_text: str = ""
    background_update_count: int = 0  # 背景流水线更新次数（用于触发考据 agent 的节奏）

    logic_outline: LogicOutlineState = Field(default_factory=LogicOutlineState)
    background: BackgroundKnowledgeState = Field(default_factory=BackgroundKnowledgeState)
    anchor: AnchorObjectState = Field(default_factory=AnchorObjectState)
