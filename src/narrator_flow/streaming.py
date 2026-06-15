"""Simulated real-time streaming input for the NarratorFlow.

Reads a pre-prepared transcript JSON file and yields chunks one by one,
optionally with a delay between them, to simulate listening to a live
narration in real time.
"""

import json
import time
from pathlib import Path
from typing import Iterator

from narrator_flow.state import TranscriptChunk


def stream_chunks(path: str, delay: float = 0.0) -> Iterator[TranscriptChunk]:
    """Yield TranscriptChunk objects from a transcript JSON file.

    Args:
        path: Path to a JSON file with the shape
              {"title": str, "chunks": [{"index": int, "text": str}, ...]}
        delay: Seconds to sleep before yielding each chunk (simulated real-time).
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for raw_chunk in data["chunks"]:
        if delay > 0:
            time.sleep(delay)
        yield TranscriptChunk(**raw_chunk)
