"""实时通话模式的捕获层（基于开源库 RealtimeSTT）。

不再手写 VAD/切句/重采样——改用成熟的 RealtimeSTT：它内部封装了"开本机麦 → 双重
VAD（webrtc + Silero）→ faster-whisper 转写 → 实时部分结果 + 最终整句"。我们只做一层
薄封装，把它接进 Streamlit。

设计：录音器在**后台线程**里循环取"下一句最终文本"，追加到线程安全的列表；实时
部分文本通过回调更新。Streamlit 端轮询 snapshot() 渲染。

RealtimeSTT 是可选依赖组 [live]，本模块对它惰性导入（未装时仅在真正启动录音器时报错）。

注意：RealtimeSTT 抓的是**运行 Python 的这台机器的麦克风**（适合本地 demo）；它在
macOS 上用 multiprocessing(spawn) 跑转写子进程，首次集成可能需要按其文档处理。
"""

from __future__ import annotations

import threading
from typing import List, Optional, Tuple


class LiveRecorder:
    """RealtimeSTT 的薄封装：start/stop + 线程安全的转写快照。"""

    def __init__(self, model: str = "tiny", language: str = "zh") -> None:
        from RealtimeSTT import AudioToTextRecorder  # 惰性导入

        self._sentences: List[str] = []   # 已定稿的整句
        self._partial: str = ""           # 当前正在说的实时部分文本
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._recorder = AudioToTextRecorder(
            model=model,
            language=language,
            spinner=False,
            enable_realtime_transcription=True,
            on_realtime_transcription_update=self._on_partial,
        )

    # ---- RealtimeSTT 回调：实时部分文本 ----
    def _on_partial(self, text: str) -> None:
        with self._lock:
            self._partial = text or ""

    # ---- 后台循环：阻塞取下一整句 ----
    def _loop(self) -> None:
        while self._running:
            try:
                text = self._recorder.text()  # 阻塞，返回下一整句
            except Exception:  # noqa: BLE001 — 关闭时可能抛异常
                break
            if text:
                with self._lock:
                    self._sentences.append(text.strip())
                    self._partial = ""

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        try:
            self._recorder.shutdown()
        except Exception:  # noqa: BLE001
            pass

    def clear(self) -> None:
        with self._lock:
            self._sentences = []
            self._partial = ""

    def snapshot(self) -> Tuple[List[str], str]:
        """返回 (已定稿整句列表, 当前实时部分文本)。"""
        with self._lock:
            return list(self._sentences), self._partial
