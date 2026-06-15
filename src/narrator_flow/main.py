"""CLI 入口：运行口述史实时分析 Agent demo（逐段播放预录 transcript）。

注：这是"交互式逐段分析"的简单入口，底层复用 streaming_app 的分析逻辑
（NarratorSession）。要体验真正的"流式 + 背压"主干，见
``python -m narrator_flow.streaming_app.run_stream``。
"""

import argparse

from dotenv import load_dotenv

from narrator_flow.streaming import stream_chunks
from narrator_flow.streaming_app.session import NarratorSession


def run() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="口述史实时分析 Agent demo")
    parser.add_argument(
        "--transcript",
        default="data/transcripts/sample_story.json",
        help="模拟流式输入的口述文本 JSON 文件路径",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="每段之间的模拟延迟（秒），用于演示实时听写效果",
    )
    args = parser.parse_args()

    session = NarratorSession(output_dir="output")
    for chunk in stream_chunks(args.transcript, args.delay):
        session.process_chunk(chunk)
        print(session.format_progress(chunk))
        session.dump_outputs()

    print("\n=== 完成 ===")
    print("最终结果已写入 output/logic_outline.json, "
          "output/background_knowledge.json, output/anchor_object.json")


if __name__ == "__main__":
    run()
