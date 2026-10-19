"""云端 ASR:支持两种协议,按 base_url 自动判别。

1) **StepFun SSE**(`POST {base}/audio/asr/sse`)——StepAudio 3 / 2.5 系列走这条:
   JSON 提交 base64 音频,SSE 返回 `transcript.text.delta` 增量与 `transcript.text.done`
   最终文本;音频容器支持 ogg / mp3 / wav / m4a / pcm,**不支持 webm**。
2) **OpenAI 兼容**(`POST {base}/audio/transcriptions`)——OpenAI / 硅基流动等:
   multipart 上传文件,返回 {"text": "..."}。

为什么前端要转 WAV:浏览器 MediaRecorder 出来的是 webm/opus(Chrome)或 m4a(Safari),
云端普遍不吃 webm,而后端不保证有 ffmpeg,所以由 frontend/src/lib/wav.ts 先转
16kHz 单声道 WAV 再发过来。这里仍按文件头嗅探真实格式,兼容直接上传 mp3/wav/ogg。
"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

import httpx

DEFAULT_CLOUD_BASE_URL = "https://api.stepfun.com/v1"
DEFAULT_CLOUD_MODEL = "stepaudio-3-asr-max"
MAX_SEGMENT_CHARS = 120
SUPPORTED_BY_STEP = (".wav", ".mp3", ".ogg", ".m4a")


def sniff_ext_bytes(head: bytes) -> str:
    """按文件头判断容器格式;识别不出返回空串(由调用方兜底)。"""
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return ".wav"
    if head[:4] == b"\x1aE\xdf\xa3":  # EBML(webm / mkv)
        return ".webm"
    if head[4:8] == b"ftyp":
        return ".m4a"
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3"
    if head[:4] == b"OggS":
        return ".ogg"
    return ""


def sniff_ext(path: str | Path) -> str:
    """按文件头判断容器格式,返回带点的扩展名;识别不出才沿用原扩展名。"""
    p = Path(path)
    with open(p, "rb") as f:
        head = f.read(16)
    return sniff_ext_bytes(head) or (p.suffix.lower() if p.suffix else ".wav")


def _protocol(base_url: str) -> str:
    """协议判别:默认按域名猜(stepfun => step SSE);也可用 ASR_PROTOCOL=step|openai 强制。"""
    forced = (os.environ.get("ASR_PROTOCOL") or "").strip().lower()
    if forced in ("step", "openai"):
        return forced
    return "step" if "stepfun" in (base_url or "").lower() else "openai"


def split_text(text: str) -> list[str]:
    """把整段转写结果按句末标点切成片段,让下游仍然是"逐段"分析。"""
    t = (text or "").strip()
    if not t:
        return []
    parts = [s for s in re.split(r"(?<=[。！？!?；;\n])", t) if s.strip()]
    segs: list[str] = []
    buf = ""
    for s in parts:
        s = s.strip()
        if not s:
            continue
        if len(buf) + len(s) <= MAX_SEGMENT_CHARS:
            buf += s
        else:
            if buf:
                segs.append(buf)
            buf = s
    if buf:
        segs.append(buf)
    return segs


def _transcribe_step_sse(path: Path, model: str, base_url: str, api_key: str, timeout: float) -> str:
    """StepFun 语音识别(HTTP + SSE):base64 提交,读 done 事件的完整文本。"""
    ext = sniff_ext(path)
    if ext not in SUPPORTED_BY_STEP:
        raise RuntimeError(
            f"Step ASR 不支持 {ext} 格式(支持 wav/mp3/ogg/m4a)。"
            "麦克风录音前端会自动转 WAV;上传文件请用 wav/mp3/m4a/ogg。"
        )
    payload = {
        "audio": {
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            "input": {
                "transcription": {"language": "zh", "model": model, "enable_itn": True},
                "format": {"type": ext.lstrip(".")},
            },
        }
    }
    url = base_url.rstrip("/") + "/audio/asr/sse"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    final = ""
    deltas: list[str] = []
    with httpx.Client(timeout=timeout) as client:
        with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code >= 400:
                body = resp.read().decode("utf-8", "ignore")[:300].replace("\n", " ")
                raise RuntimeError(f"Step ASR 返回 {resp.status_code}:{body}")
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if not chunk or chunk == "[DONE]":
                    continue
                try:
                    obj = json.loads(chunk)
                except ValueError:
                    continue
                kind = obj.get("type")
                if kind == "transcript.text.done":
                    final = obj.get("text") or final
                elif kind == "transcript.text.delta":
                    deltas.append(obj.get("delta") or "")
                elif kind == "error":
                    raise RuntimeError(f"Step ASR 错误:{obj.get('message')}")
    return final or "".join(deltas)


def _transcribe_openai(path: Path, model: str, base_url: str, api_key: str, timeout: float) -> str:
    """OpenAI 兼容 /audio/transcriptions:multipart 上传,返回 text。"""
    url = base_url.rstrip("/") + "/audio/transcriptions"
    ext = sniff_ext(path)
    with httpx.Client(timeout=timeout) as client:
        with open(path, "rb") as f:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (f"audio{ext}", f, "application/octet-stream")},
                data={"model": model, "response_format": "json"},
            )
    if resp.status_code >= 400:
        body = resp.text.strip().replace("\n", " ")[:300]
        raise RuntimeError(f"云端 ASR 返回 {resp.status_code}:{body}")
    try:
        return (resp.json() or {}).get("text", "")
    except ValueError:
        return resp.text


def transcribe_cloud(
    audio_path: str | Path,
    model: str = DEFAULT_CLOUD_MODEL,
    base_url: str = DEFAULT_CLOUD_BASE_URL,
    api_key: str = "",
    timeout: float = 120.0,
) -> list[str]:
    """调用云端 ASR 做一次转写,返回按句切好的文本片段。"""
    if not api_key:
        raise RuntimeError("未配置云端 ASR 的 API Key(设置 → 语音识别 · ASR)")
    path = Path(audio_path)
    try:
        if _protocol(base_url) == "step":
            text = _transcribe_step_sse(path, model, base_url, api_key, timeout)
        else:
            text = _transcribe_openai(path, model, base_url, api_key, timeout)
    except httpx.HTTPError as e:  # 网络层
        raise RuntimeError(f"云端 ASR 请求失败:{e}") from e
    return split_text(text)
