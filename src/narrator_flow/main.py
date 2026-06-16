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
    parser.add_argument(
        "--demo",
        action="store_true",
        help="免 key 演示：回放预录结果，不调用任何 LLM（仅适用于示例 sample_story.json）",
    )
    args = parser.parse_args()

    if args.demo:
        print("[免 key 演示] 回放预录结果，不调用 DeepSeek。")
        out_dir = "output_demo"
        session = NarratorSession.demo(output_dir=out_dir)
    else:
        out_dir = "output"
        session = NarratorSession(output_dir=out_dir)
    for chunk in stream_chunks(args.transcript, args.delay):
        session.process_chunk(chunk)
        print(session.format_progress(chunk))
        session.dump_outputs()

    print("\n=== 完成 ===")
    print(f"最终结果已写入 {out_dir}/logic_outline.json, "
          f"{out_dir}/background_knowledge.json, {out_dir}/anchor_object.json")


if __name__ == "__main__":
    run()
