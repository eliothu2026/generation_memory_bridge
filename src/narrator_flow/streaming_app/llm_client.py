"""框架无关的 LLM 客户端（方案3：不依赖 CrewAI）。

直接用 openai SDK 调 DeepSeek 的 OpenAI 兼容接口，提供两类能力：

- run_tool_loop(): agentic 的"调工具→读结果→再决定"循环（给考据 agent 用）。
  这一步**不要求结构化输出**，让模型自由发起工具调用——从而绕开"JSON 模式与
  工具调用在单次调用里互斥"的问题（见对话里的分析）。
- structured(): JSON 模式 + Pydantic 解析（给需要结构化结果的最终步骤用）。

环境变量：
- DEEPSEEK_API_KEY（必填）
- DEEPSEEK_BASE_URL（可选，默认 https://api.deepseek.com）
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def get_client():
    try:
        from openai import OpenAI
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("缺少 openai SDK，请 pip install openai") from e
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY，无法调用真实 LLM。")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=api_key, base_url=base_url)


def run_tool_loop(
    messages: list[dict],
    tools: list[dict],
    tool_impls: dict[str, Callable[..., str]],
    model: str = DEFAULT_MODEL,
    max_iters: int = 5,
    temperature: float = 0.2,
    client: Any = None,
) -> str:
    """运行 reason–act 工具循环，返回模型最终的文本输出。

    Args:
        messages: 初始对话（含 system / user）。
        tools: OpenAI function-calling 格式的工具声明。
        tool_impls: 工具名 -> 可调用实现（接收解析后的参数，返回字符串结果）。
        max_iters: 最多允许多少轮工具调用，防止无限循环。
    """
    client = client or get_client()
    messages = list(messages)

    for _ in range(max_iters):
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=tools,
            tool_choice="auto", temperature=temperature,
        )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)

        if not tool_calls:
            return msg.content or ""

        # 把助手这轮（含工具调用）记入对话
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })
        # 逐个执行工具，把结果回灌
        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            impl = tool_impls.get(name)
            try:
                result = impl(**args) if impl else f"[未知工具: {name}]"
            except Exception as e:  # noqa: BLE001 — 工具失败不应中断循环
                result = f"[工具 {name} 执行失败: {e}]"
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": str(result)[:4000],
            })

    # 用尽轮数仍未给出最终答案：再要一次纯文本收尾
    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def structured(
    messages: list[dict],
    schema: type[BaseModel],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    client: Any = None,
) -> Optional[BaseModel]:
    """JSON 模式 + Pydantic 解析，返回结构化对象（失败返回 None）。

    自动把目标模型的 JSON Schema 注入对话，替代 CrewAI 的 output_pydantic 约束：
    让模型按 schema 输出 JSON，再用 Pydantic 解析校验。
    """
    client = client or get_client()
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    messages = list(messages) + [{
        "role": "system",
        "content": ("只输出一个 JSON 对象，严格符合下面的 JSON Schema；"
                    "不要输出任何多余文字，也不要用 markdown 代码块包裹：\n" + schema_json),
    }]
    resp = client.chat.completions.create(
        model=model, messages=messages,
        response_format={"type": "json_object"}, temperature=temperature,
    )
    content = resp.choices[0].message.content or ""
    try:
        return schema.model_validate_json(content)
    except Exception:  # noqa: BLE001
        try:
            return schema.model_validate(json.loads(content))
        except Exception as e:  # noqa: BLE001
            logger.warning("结构化解析失败: %s", e)
            return None
