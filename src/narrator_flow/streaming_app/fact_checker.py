"""考据 agent（方案3：手写工具循环，无框架）。

职责：对背景知识流水线累积的笔记做史实核验。流程分两步，刻意把"用工具调查"
与"输出结构化结果"分开，从而绕开"JSON 模式与工具调用单次互斥"的问题：

1. 调查：run_tool_loop —— 模型自主调用维基检索工具核实笔记中的史实（reason–act）。
2. 定稿：structured —— 把调查结论格式化为修订后的背景状态。

处置策略（按用户决策"保守标注为主"）：
- 存疑 → 标注"（⚠️待核实）"，不删
- 明确造假（高置信度）→ 删除，并记入 changelog
- 过于浅显 → 适当补充深化，不删
- 一切修正都须基于检索证据，不得凭空杜撰
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from narrator_flow.state import BackgroundKnowledgeState

from . import llm_client
from .wikipedia_tool import TOOL_IMPLS, TOOL_SPECS

logger = logging.getLogger(__name__)

_INVESTIGATE_SYSTEM = (
    "你是一位严谨、保守的历史考据员。你会用维基百科检索工具核实口述史背景笔记中的"
    "史实。原则：①只依据检索到的证据下判断，绝不凭空断言或杜撰；②证据不足时如实说"
    "“无法核实”，不要硬下结论；③区分“明确失实”（与权威资料直接冲突）与“仅存疑”"
    "（找不到佐证）。请逐条核实下面的笔记，必要时多次检索。"
)

_FINALIZE_SYSTEM = (
    "你是历史考据员，现在根据调查结论，输出修订后的背景笔记。严格遵守保守处置策略：\n"
    "- 存疑但未被证伪的：保留原文并在末尾加“（⚠️待核实）”。\n"
    "- 已被检索证据证实的：保留并在末尾加“（✅据维基核实）”。\n"
    "- 明确与权威资料冲突的失实内容：从 notes 中删除，并在 changelog 写明删除原因。\n"
    "- 过于浅显的：在原文基础上适当补充一句更具体的背景，不要删除。\n"
    "- 不要新增任何无证据支撑的“事实”。\n"
    "只输出 JSON，字段：era_estimate(string，不确定性写进措辞、不要数字置信度)、"
    "notes(字符串数组)、changelog(字符串数组，记录本次的删除/修正/标注)。"
)


class FactCheckResult(BaseModel):
    era_estimate: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    changelog: List[str] = Field(default_factory=list)


class FactChecker:
    """口述史背景知识的考据 agent。"""

    def __init__(self, model: str = llm_client.DEFAULT_MODEL, max_iters: int = 5) -> None:
        self.model = model
        self.max_iters = max_iters

    def verify(self, background: BackgroundKnowledgeState) -> BackgroundKnowledgeState:
        """核验并返回修订后的背景状态；任何失败都安全回退为原状态。"""
        if not background.notes:
            return background

        notes_block = "\n".join(f"{i+1}. {n}" for i, n in enumerate(background.notes))
        user = (
            f"当前对年代的估计：{background.era_estimate or '未知'}\n"
            f"待核实的背景笔记：\n{notes_block}"
        )

        try:
            client = llm_client.get_client()
            # 第 1 步：带工具的调查
            findings = llm_client.run_tool_loop(
                messages=[
                    {"role": "system", "content": _INVESTIGATE_SYSTEM},
                    {"role": "user", "content": user},
                ],
                tools=TOOL_SPECS,
                tool_impls=TOOL_IMPLS,
                model=self.model,
                max_iters=self.max_iters,
                client=client,
            )
            # 第 2 步：定稿为结构化结果
            result = llm_client.structured(
                messages=[
                    {"role": "system", "content": _FINALIZE_SYSTEM},
                    {"role": "user", "content":
                        f"原始笔记：\n{notes_block}\n\n调查结论：\n{findings}"},
                ],
                schema=FactCheckResult,
                model=self.model,
                client=client,
            )
        except Exception as e:  # noqa: BLE001 — 考据失败绝不能拖垮主流程
            logger.warning("考据 agent 失败，保留原背景: %s", e)
            return background

        if result is None or not result.notes:
            logger.warning("考据 agent 未返回有效结果，保留原背景")
            return background

        if result.changelog:
            logger.info("考据变更: %s", "；".join(result.changelog))

        return BackgroundKnowledgeState(
            era_estimate=result.era_estimate or background.era_estimate,
            notes=result.notes,
        )
