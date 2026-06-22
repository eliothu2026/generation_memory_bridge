"""维基百科检索工具（考据 agent 用，免 key）。

直连 MediaWiki API（zh.wikipedia.org），无需任何 API key。提供两个动作：
- wiki_search(query): 搜索条目，返回标题 + 摘要片段
- wiki_extract(title): 取某条目的导言纯文本

注意：维基百科在中国大陆被屏蔽——裸网会 ConnectTimeout（与 Hugging Face 同类）。
端点可通过环境变量 WIKIPEDIA_API_ENDPOINT 指向镜像/代理，或在能访问维基的网络
（海外 / VPN）下使用。

以 OpenAI function-calling 格式导出 TOOL_SPECS + TOOL_IMPLS，供 llm_client 的
工具循环驱动。
"""

from __future__ import annotations

import os

import httpx

DEFAULT_ENDPOINT = "https://zh.wikipedia.org/w/api.php"
_UA = "narrator-flow/0.1 (oral-history fact-check; https://github.com/eliothu2026/generation_memory_bridge)"
_TIMEOUT = 15.0


def _endpoint() -> str:
    return os.environ.get("WIKIPEDIA_API_ENDPOINT", DEFAULT_ENDPOINT)


def _get(params: dict) -> dict:
    params = {**params, "format": "json"}
    resp = httpx.get(_endpoint(), params=params, headers={"User-Agent": _UA}, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def wiki_search(query: str, limit: int = 3) -> str:
    """搜索维基条目，返回 '标题 + 摘要' 的可读文本。"""
    try:
        data = _get({"action": "query", "list": "search",
                     "srsearch": query, "srlimit": limit})
    except Exception as e:  # noqa: BLE001 — 把网络错误变成可读结果，让 agent 自行处置
        return f"[维基搜索失败：{type(e).__name__}。可能是网络无法访问维基百科。]"
    hits = data.get("query", {}).get("search", [])
    if not hits:
        return f"[未找到与“{query}”相关的维基条目]"
    lines = []
    for h in hits:
        # snippet 含 HTML 标签，去掉
        snippet = (h.get("snippet", "")
                   .replace('<span class="searchmatch">', "").replace("</span>", ""))
        lines.append(f"《{h['title']}》：{snippet}…")
    return "\n".join(lines)


def wiki_extract(title: str, max_chars: int = 1200) -> str:
    """取某条目的导言纯文本（用于核实细节）。"""
    try:
        data = _get({"action": "query", "prop": "extracts", "titles": title,
                     "exintro": 1, "explaintext": 1, "redirects": 1})
    except Exception as e:  # noqa: BLE001
        return f"[维基取条目失败：{type(e).__name__}]"
    pages = data.get("query", {}).get("pages", {})
    for _pid, page in pages.items():
        extract = page.get("extract", "")
        if extract:
            return extract[:max_chars]
    return f"[条目“{title}”无可用正文]"


# ---- 供 LLM 工具循环使用的声明与实现映射 ----
TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "wiki_search",
            "description": "在中文维基百科搜索条目，用于核实历史/社会背景事实。返回相关条目标题与摘要。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要查证的关键词或主题，如“人民公社”"},
                    "limit": {"type": "integer", "description": "返回条目数，默认 3"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wiki_extract",
            "description": "获取某个维基条目的导言正文，用于核实具体细节（如年代、定义）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "维基条目的准确标题"},
                },
                "required": ["title"],
            },
        },
    },
]

TOOL_IMPLS = {
    "wiki_search": wiki_search,
    "wiki_extract": wiki_extract,
}
