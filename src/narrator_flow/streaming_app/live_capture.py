"""实时通话模式的捕获层（sounddevice 本机麦 + webrtcvad 切句 + faster-whisper）。

为什么是 sounddevice：它的 pip 包**自带编译好的 PortAudio**，纯 `pip install` 即可，
无需 Homebrew/系统库（PyAudio 需要系统 portaudio，在无 Homebrew 的机器上装不上）。
sounddevice 直接以 16kHz 单声道 int16 取流，正好同时喂给 webrtcvad 与 faster-whisper，
连重采样都省了。

线程模型：
- 采集线程：以 16kHz 读本机麦 → 喂 VADSegmenter，整句完成就放入转写队列；
- 转写线程：从队列取整句 → faster-whisper 转文字 → 追加到线程安全的句子列表。
采集与转写分离，转写慢也不会丢音频。

依赖（可选组 [live]）：sounddevice / webrtcvad / faster-whisper，均纯 pip、无系统依赖。
本模块对它们惰性导入。
"""

from __future__ import annotations

import queue
import threading
from typing import List, Optional, Tuple

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
        self._frame_bytes = int(SAMPLE_RATE * FRAME_MS / 1000) * 2
        self._silence_limit = max(1, silence_ms // FRAME_MS)
        self._min_frames = max(1, min_utterance_ms // FRAME_MS)
        self._buf = b""
        self._utt = bytearray()
        self._utt_frames = 0
        self._in_speech = False
        self._silence = 0

    def add(self, pcm16: bytes) -> List[bytes]:
        out: List[bytes] = []
        self._buf += pcm16
        while len(self._buf) >= self._frame_bytes:
            frame = self._buf[:self._frame_bytes]
            self._buf = self._buf[self._frame_bytes:]
            try:
                speech = self._vad.is_speech(frame, SAMPLE_RATE)
            except Exception:  # noqa: BLE001
                continue
            if speech:
                self._in_speech = True
                self._silence = 0
                self._utt += frame
                self._utt_frames += 1
            elif self._in_speech:
                self._silence += 1
                self._utt += frame
                self._utt_frames += 1
                if self._silence >= self._silence_limit:
                    if self._utt_frames - self._silence >= self._min_frames:
                        out.append(bytes(self._utt))
                    self._reset_utt()
        return out

    def flush(self) -> Optional[bytes]:
        u = bytes(self._utt) if self._utt_frames - self._silence >= self._min_frames else None
        self._reset_utt()
        return u

    def _reset_utt(self) -> None:
        self._utt = bytearray()
        self._utt_frames = 0
        self._in_speech = False
        self._silence = 0


def transcribe_pcm16(pcm16: bytes, model_size: str = "tiny", language: str = "zh") -> str:
    """把一句 PCM 转成文字（复用 asr 的本地 faster-whisper 模型）。"""
    samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
    if samples.size == 0:
        return ""
    model = asr._load_model(model_size)
    segments, _info = model.transcribe(
        samples, language=language, vad_filter=False,
        initial_prompt=asr.DOMAIN_PROMPT,
    )
    return "".join(s.text for s in segments).strip()


class LiveRecorder:
    """sounddevice 本机麦 → VAD 切句 → faster-whisper 逐句转写。start/stop/snapshot。"""

    def __init__(self, model: str = "tiny", language: str = "zh") -> None:
        self._model = model
        self._language = language
        self._seg = VADSegmenter()        # 惰性触发 webrtcvad 导入
        self._sentences: List[str] = []
        self._lock = threading.Lock()
        self._utt_q: "queue.Queue[bytes]" = queue.Queue()
        self._running = False
        self._cap_thread: Optional[threading.Thread] = None
        self._tx_thread: Optional[threading.Thread] = None
        self._error: Optional[str] = None

    def _capture_loop(self) -> None:
        try:
            import sounddevice as sd
            block = int(SAMPLE_RATE * 0.1)  # 100ms
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                blocksize=block) as stream:
                while self._running:
                    data, _ = stream.read(block)
                    for utt in self._seg.add(data.tobytes()):
                        self._utt_q.put(utt)
            tail = self._seg.flush()
            if tail:
                self._utt_q.put(tail)
        except Exception as e:  # noqa: BLE001 — 麦克风/设备问题
            self._error = f"{type(e).__name__}: {e}"
            self._running = False

    def _transcribe_loop(self) -> None:
        while self._running or not self._utt_q.empty():
            try:
                utt = self._utt_q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                text = transcribe_pcm16(utt, self._model, self._language)
            except Exception as e:  # noqa: BLE001
                self._error = f"{type(e).__name__}: {e}"
                continue
            if text:
                with self._lock:
                    self._sentences.append(text)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._cap_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._tx_thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._cap_thread.start()
        self._tx_thread.start()

    def stop(self) -> None:
        self._running = False

    def clear(self) -> None:
        with self._lock:
            self._sentences = []

    def snapshot(self) -> Tuple[List[str], str]:
        """返回 (已定稿整句列表, 实时部分文本)。本实现无实时部分，故第二项恒为空串。"""
        with self._lock:
            return list(self._sentences), ""

    @property
    def error(self) -> Optional[str]:
        return self._error
