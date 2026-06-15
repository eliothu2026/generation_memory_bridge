"""CLI 入口：运行口述史实时分析 Agent demo。"""

import argparse

from dotenv import load_dotenv

from narrator_flow.flow import NarratorFlow


def run() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="口述史实时分析 Agent (CrewAI Flows demo)")
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

    flow = NarratorFlow(transcript_path=args.transcript, delay=args.delay)
    flow.kickoff()

    print("\n=== 完成 ===")
    print("最终结果已写入 output/logic_outline.json, "
          "output/background_knowledge.json, output/anchor_object.json")


if __name__ == "__main__":
    run()
