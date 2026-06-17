"""真实 ASR：用本地 faster-whisper 把音频转成文字片段。

它和 producer.py 的 simulated_asr 扮演**同一种角色**——往队列里塞文字片段的
producer，因此下游（队列/背压/worker/分析）完全不用改。这正是早期"producer 与
分析解耦"的架构决策带来的红利：接真实 ASR 只是换掉"耳朵"。

faster-whisper 是**可选依赖**（pyproject 的 [asr] 组）。本模块对它做**惰性导入**：
不装也能 import 本模块，只有真正调用转写时才会提示安装，避免拖累其他用法。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List

from narrator_flow.state import TranscriptChunk

from .coalescing_queue import CoalescingQueue

DEFAULT_MODEL = "small"   # tiny/base/small/medium/large；small 在中文与速度间较平衡
DEFAULT_LANGUAGE = "zh"

# 进程内缓存已加载的模型，避免每次转写都重新加载（Streamlit 多次 rerun 时尤为重要）
_MODEL_CACHE: Dict[str, object] = {}


def _load_model(model_size: str):
    if model_size in _MODEL_CACHE:
        return _MODEL_CACHE[model_size]
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:  # 惰性、友好的报错
        raise RuntimeError(
            "未安装 faster-whisper。请先安装 ASR 可选依赖：\n"
            '    pip install -e ".[asr]"'
        ) from e
    # CPU + int8 量化：无需 GPU，体积/速度对个人机器友好
    try:
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
    except Exception as e:  # noqa: BLE001 — 多为模型下载失败，给出可操作提示
        raise RuntimeError(
            f"加载语音模型 '{model_size}' 失败：{e}\n"
            "首次使用需联网下载模型。若是下载超时（国内网络常无法访问 "
            "huggingface.co），请改用镜像后重试：\n"
            "    export HF_ENDPOINT=https://hf-mirror.com"
        ) from e
    _MODEL_CACHE[model_size] = model
    return model


def transcribe_segments(
    audio_path: str | Path,
    model_size: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
) -> List[str]:
    """把音频文件转成一串文字片段（按 Whisper 的句子级切分）。"""
    model = _load_model(model_size)
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,   # 用 VAD 过滤静音，切分更干净、更接近"话轮"
    )
    return [seg.text.strip() for seg in segments if seg.text and seg.text.strip()]


def transcribe_to_chunks(
    audio_path: str | Path,
    model_size: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
) -> List[TranscriptChunk]:
    """转成 TranscriptChunk 列表，方便 GUI 像播放预录文本一样逐段播放。"""
    texts = transcribe_segments(audio_path, model_size, language)
    return [TranscriptChunk(index=i, text=t) for i, t in enumerate(texts)]


async def transcribe_file_to_queue(
    queue: CoalescingQueue,
    audio_path: str | Path,
    model_size: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
    pacing: float = 0.0,
) -> None:
    """流式入口：转写音频并把片段逐个推入队列，结束后推 stop 信号。

    转写本身是同步且偏重的，放进 asyncio.to_thread 以免阻塞事件循环；pacing 可在
    片段间加间隔，模拟真实说话节奏（用于观察背压）。
    """
    segments = await asyncio.to_thread(
        transcribe_segments, audio_path, model_size, language
    )
    for seg in segments:
        if pacing > 0:
            await asyncio.sleep(pacing)
        await queue.put(seg)
    await queue.close()
