"""把 transcript + replay 两个现有产物合成前端离线模式用的 demo_script.json。

纯离线、无 LLM:只是读取并"逐段归并"已有数据,方便 React 前端一次 fetch、逐段回放。

输入:
- data/transcripts/sample_story.json          老人叙述,{title, chunks:[{index,text}]}
- data/demo_replay/sample_story.replay.json   逐段分析快照(稀疏 + 累积),键为字符串 chunk 索引

输出:
- frontend/public/demo_script.json            {session, steps:[{...}]}(共 18 步)

归并规则(与 ReplayPipelines 的语义一致):
- logic_outline / background / era_estimate:carry-forward,沿用"上一次出现"的值;
- new_background_notes:本段 background.notes 相对上一背景快照的"尾部增量"
  (已验证快照 notes 为严格前缀,故增量即新追加的那几条);
- follow_ups:该 chunk 自带的 follow_up(逐段新鲜,不累积);无则为空;
- anchor:v1 暂不纳入。

用法:python scripts/gen_demo_script.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT = REPO_ROOT / "data" / "transcripts" / "sample_story.json"
REPLAY = REPO_ROOT / "data" / "demo_replay" / "sample_story.replay.json"
OUT = REPO_ROOT / "frontend" / "public" / "demo_script.json"

# 会话展示信息(离线模式的"大槐树的故事")
SESSION_META = {
    "id": "demo-dahuaishu",
    "title": "大槐树的故事",
    "subtitle": "农村长辈回忆 1970–80 年代",
    "elder_name": "老张",
}


def _empty_timeline() -> dict:
    return {"events": [], "open_threads": [], "last_update_mode": None, "raw_outline_text": ""}


def build_steps(transcript: dict, replay: dict) -> list[dict]:
    chunks = sorted(transcript["chunks"], key=lambda c: c["index"])

    timeline = _empty_timeline()      # carry-forward 的当前时间线
    era_estimate = None               # carry-forward 的当前年代估计
    prev_notes: list[str] = []        # 上一背景快照的全部笔记(用于算增量)

    steps: list[dict] = []
    for chunk in chunks:
        idx = chunk["index"]
        snap = replay.get(str(idx), {})

        if "logic_outline" in snap:
            lo = snap["logic_outline"]
            timeline = {
                "events": lo.get("events", []),
                "open_threads": lo.get("open_threads", []),
                "last_update_mode": lo.get("last_update_mode"),
                "raw_outline_text": lo.get("raw_outline_text", ""),
            }

        new_notes: list[str] = []
        if "background" in snap:
            bg = snap["background"]
            notes = bg.get("notes", [])
            new_notes = notes[len(prev_notes):]   # 尾部增量(快照为严格前缀)
            prev_notes = notes
            era_estimate = bg.get("era_estimate", era_estimate)

        follow_ups = list(snap.get("follow_up", []))  # 逐段新鲜,无则 []

        steps.append({
            "index": idx,
            "elder_text": chunk["text"],
            "new_background_notes": new_notes,
            "era_estimate": era_estimate,
            "follow_ups": follow_ups,
            # 深拷贝一份当前时间线快照,避免后续 carry-forward 覆盖已写入的步骤
            "timeline": json.loads(json.dumps(timeline, ensure_ascii=False)),
        })

    return steps


def main() -> None:
    transcript = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))

    steps = build_steps(transcript, replay)
    payload = {"session": SESSION_META, "steps": steps}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 摘要,便于人工核对
    with_notes = [s["index"] for s in steps if s["new_background_notes"]]
    with_fu = [s["index"] for s in steps if s["follow_ups"]]
    final_events = len(steps[-1]["timeline"]["events"]) if steps else 0
    print(f"✅ 写出 {OUT.relative_to(REPO_ROOT)}")
    print(f"   步数: {len(steps)}")
    print(f"   有新增背景笔记的段: {with_notes}")
    print(f"   有交互提醒的段:     {with_fu}")
    print(f"   末段时间线事件数:   {final_events}")
    print(f"   末段年代估计:       {steps[-1]['era_estimate'] if steps else None}")


if __name__ == "__main__":
    main()
