"""实时通话模式的捕获层（阶段1：连续麦 → VAD 切句 → 逐句转写）。

职责只有"把实时音频变成一句句文字"，下游分析照旧复用 NarratorSession（阶段2 再接）。

- VADSegmenter：用 webrtcvad（纯算法、不下模型）按静音自动切句；
- frame_to_pcm16：把 WebRTC 的 av.AudioFrame 重采样为 16kHz 单声道 16-bit PCM；
- transcribe_pcm16：把一句 PCM 交给 faster-whisper 转文字（复用 asr 的模型缓存）。

依赖 streamlit-webrtc / webrtcvad 为可选组 [live]，本模块对它们惰性导入。
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from . import asr

SAMPLE_RATE = 16000
FRAME_MS = 30  # webrtcvad 仅接受 10/20/30ms


class VADSegmenter:
    """按"说话后跟随一段静音"自动切出整句。喂入 16kHz 单声道 16-bit PCM 字节。"""

    def __init__(self, silence_ms: int = 700, aggressiveness: int = 2,
                 min_utterance_ms: int = 300) -> None:
        import webrtcvad  # 惰性导入
        self._vad = webrtcvad.Vad(aggressiveness)
        self._frame_bytes = int(SAMPLE_RATE * FRAME_MS / 1000) * 2  # 16-bit → ×2
        self._silence_limit = max(1, silence_ms // FRAME_MS)
        self._min_frames = max(1, min_utterance_ms // FRAME_MS)
        self._buf = b""              # 不足一帧的余量
        self._utt = bytearray()      # 当前句的音频
        self._utt_frames = 0
        self._in_speech = False
        self._silence = 0

    def add(self, pcm16: bytes) -> List[bytes]:
        """喂入一段 PCM，返回这次新切出的整句列表（可能为空）。"""
        out: List[bytes] = []
        self._buf += pcm16
        while len(self._buf) >= self._frame_bytes:
            frame = self._buf[:self._frame_bytes]
            self._buf = self._buf[self._frame_bytes:]
            try:
                speech = self._vad.is_speech(frame, SAMPLE_RATE)
            except Exception:  # noqa: BLE001 — 帧长异常等，跳过该帧
                continue
            if speech:
                self._in_speech = True
                self._silence = 0
                self._utt += frame
                self._utt_frames += 1
            elif self._in_speech:
                self._silence += 1
                self._utt += frame  # 含尾部静音
                self._utt_frames += 1
                if self._silence >= self._silence_limit:
                    if self._utt_frames - self._silence >= self._min_frames:
                        out.append(bytes(self._utt))  # 够长才算一句，滤掉咳嗽/杂音
                    self._reset_utt()
        return out

    def flush(self) -> Optional[bytes]:
        """通话结束时取出残留的最后一句（如果有）。"""
        u = bytes(self._utt) if self._utt_frames - self._silence >= self._min_frames else None
        self._reset_utt()
        return u

    def _reset_utt(self) -> None:
        self._utt = bytearray()
        self._utt_frames = 0
        self._in_speech = False
        self._silence = 0


_resampler = None


def frame_to_pcm16(frame) -> bytes:
    """av.AudioFrame → 16kHz 单声道 16-bit PCM 字节。"""
    global _resampler
    import av
    if _resampler is None:
        _resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
    out = _resampler.resample(frame)
    frames = out if isinstance(out, list) else [out]  # av 版本差异：可能返回 list
    chunks = []
    for f in frames:
        if f is not None:
            chunks.append(f.to_ndarray().astype(np.int16).tobytes())
    return b"".join(chunks)


def transcribe_pcm16(pcm16: bytes, model_size: str = "small", language: str = "zh") -> str:
    """把一句 PCM 转成文字（复用 asr 的本地 faster-whisper 模型）。"""
    samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
    if samples.size == 0:
        return ""
    model = asr._load_model(model_size)
    segments, _info = model.transcribe(samples, language=language, vad_filter=False)
    return "".join(s.text for s in segments).strip()
