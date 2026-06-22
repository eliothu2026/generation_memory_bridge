"""生成"免 key 演示"用的预录回放快照。

输出 data/demo_replay/sample_story.replay.json：一个 {chunk_index: {slice: 对象}}
的稀疏快照表，描述 sample_story.json（大槐树故事）逐段处理时三条流水线**应该**
长成的样子。ReplayPipelines 据此逐段回放，无需任何 LLM 调用。

设计为"稀疏 + 累积"：只在某条流水线状态发生变化的 chunk 写入该 slice 的完整快照，
未写入的 chunk 保持上一次状态不变。这样既好维护，回放时又显得"活"。

注意：这些内容是为演示**人工编排**的合理结果，不是真实 LLM 输出；目的是让没有
API key 的人也能体验产品交互，而非复现某次真实运行。
"""

import json
from pathlib import Path

OUT = Path("data/demo_replay/sample_story.replay.json")

# ----------------------------------------------------------------------
# 流水线 B：背景知识（累积）
# ----------------------------------------------------------------------
_bg_notes = []
_background_at = {}  # chunk_index -> background slice


def bg(idx, era, _conf, *new_notes):
    # 第 2 个参数（旧的数字置信度）已弃用：不确定性改由 era 文本的措辞表达。
    # 保留形参只是为了不动下面 8 处调用；输出里不再写 confidence。
    for n in new_notes:
        if n not in _bg_notes:
            _bg_notes.append(n)
    _background_at[idx] = {
        "era_estimate": era,
        "notes": list(_bg_notes),
    }


bg(1, "20 世纪中后期中国农村（待确认）", 0.30,
   "村里仅有一台拖拉机，由专人驾驶，反映集体化时期农机稀缺、是重要生产资料。")
bg(3, "20 世纪 60–70 年代中国农村（集体化时期）", 0.55,
   "母亲在生产队'记工分'——按劳动记分分配，是人民公社时期的分配方式。")
bg(4, "20 世纪 60–70 年代中国农村（集体化时期）", 0.68,
   "哥哥'下乡当知青'，对应 1960s–70s 知识青年上山下乡运动。")
bg(6, "20 世纪 70 年代中国农村", 0.80,
   "粮食定量、凭'粮票'购买，是计划经济时期的票证制度；口粮时有不足需邻里相借。")
bg(7, "20 世纪 70 年代中国农村（人民公社体制）", 0.86,
   "提到'公社'，对应人民公社体制；全公社共用一台拖拉机，农忙排队耕地。")
bg(9, "20 世纪 70 年代中国农村（人民公社体制）", 0.88,
   "用'辘轳'从水井取水，反映当时农村无自来水的生活方式。")
bg(11, "20 世纪 70 年代末至 80 年代中国农村（家庭联产承包责任制初期）", 0.95,
   "'包产到户'/家庭联产承包责任制，标志农村改革开始（约 1978–1983），土地分户经营。")
bg(15, "20 世纪 70 年代末至 80 年代末中国农村（家庭联产承包责任制推行初期至中期）", 0.98,
   "父亲对报废旧拖拉机的不舍，体现农机承载的情感价值。")

# ----------------------------------------------------------------------
# 流水线 A：逻辑 / 时间线大纲（累积）
# ----------------------------------------------------------------------
_events = []
_logic_at = {}


def _outline_text():
    lines = ["## 时间线大纲", ""]
    for e in _events:
        period = f"（{e['period_hint']}）" if e.get("period_hint") else ""
        lines.append(f"{e['order']}. {period}{e['description']}")
    return "\n".join(lines)


def logic(idx, mode, open_threads, *new_events):
    for ev in new_events:
        _events.append(ev)
    _logic_at[idx] = {
        "events": [dict(e) for e in _events],
        "open_threads": list(open_threads),
        "raw_outline_text": _outline_text(),
        "last_update_mode": mode,
    }


def ev(order, desc, period=None, cause=None, effect=None, src=()):
    return {"order": order, "period_hint": period, "description": desc,
            "cause": cause, "effect": effect, "source_chunk_indices": list(src)}


_OT_BASE = [
    "具体年份未明（下乡、包产到户分别在哪一年）",
    "讲述者本人的出生年份与年龄未知",
    "院子 / 村庄的具体地点未知",
]

logic(0, "incremental", _OT_BASE,
      ev(1, "童年在老宅院生活，门口有一棵需两人合抱的大槐树，常在树下玩耍", "童年", src=[0]))
logic(1, "incremental", _OT_BASE + ["父亲驾驶的拖拉机型号 / 年代未知"],
      ev(2, "父亲是村里唯一的拖拉机手，常被各家请去帮忙", src=[1]))
logic(3, "incremental", _OT_BASE + ["母亲工分制下的家庭收入状况未知"],
      ev(3, "母亲在生产队记工分，天不亮即出工；兄弟二人在家由哥哥照看", src=[3]))
logic(4, "refine", _OT_BASE + ["哥哥下乡的山区具体位置未知", "是否还有其他兄弟姐妹"],
      ev(4, "哥哥（长五岁）下乡当知青，去更远的山里，一年回家一两次", "知青下乡时期", src=[4]))
logic(6, "incremental", _OT_BASE + ["哥哥下乡的山区具体位置未知"],
      ev(5, "粮食定量、凭粮票购买，口粮不足时向邻居借", "计划经济时期", src=[6]))
logic(7, "incremental", _OT_BASE,
      ev(6, "全公社共用父亲这一台拖拉机，农忙时排队耕地数日", src=[7]))
logic(9, "full_rerun", _OT_BASE,
      ev(7, "院子东边有水井，用辘轳摇水，是童年深刻印象", src=[9]))
logic(10, "incremental", _OT_BASE,
      ev(8, "哥哥某年夏天自山里回乡探亲，在槐树下石桌讲述山里见闻一整晚", src=[10]))
logic(11, "incremental", _OT_BASE,
      ev(9, "包产到户，土地分到各户；父亲的拖拉机改为给各家轮流耕地、按天收费",
         "约 1978–1983 改革初期", src=[11]))
logic(14, "refine", _OT_BASE,
      ev(10, "哥哥最终自山里回乡定居，在老宅旁盖起小房，离槐树仅几步", src=[14]))
logic(15, "incremental", _OT_BASE,
      ev(11, "拖拉机使用近二十年后报废，父亲不舍丢弃，停在院角多年", src=[15]))
logic(16, "incremental", _OT_BASE,
      ev(12, "多年后回乡，老槐树仍在，树干多疤痕但更枝繁叶茂、树荫更大", "当下", src=[16]))
logic(17, "incremental", _OT_BASE,
      ev(13, "槐树下的石桌仍在，边角磨圆、桌面被坐得发亮", "当下", src=[17]))

# ----------------------------------------------------------------------
# 流水线 C：记忆锚点（大槐树）
# ----------------------------------------------------------------------
_attrs = []
_anchor_at = {}


def anchor(idx, mentions, score, ready, prompt, *new_attrs):
    for a in new_attrs:
        if a not in _attrs:
            _attrs.append(a)
    _anchor_at[idx] = {
        "candidate_name": "大槐树",
        "mention_count": mentions,
        "descriptive_attributes": list(_attrs),
        "image_prompt": prompt,
        "prompt_detail_score": score,
        "is_ready_for_generation": ready,
        "image_generated": False,
        "image_path": None,
    }


_P_EARLY = "An old Chinese scholar tree (huai tree) in a rural courtyard."
_P_MID = ("An old, very thick Chinese scholar tree at the gate of an old rural "
          "courtyard, trunk so wide it takes two people to embrace, cracked bark, "
          "a stone table under it where villagers rest and play chess.")
_P_FULL = ("A majestic old Chinese scholar tree (huai tree) standing at the gate of "
           "an old northern-Chinese rural courtyard. The trunk is extremely thick, "
           "needing two people to embrace, with deeply cracked, weathered bark and "
           "many scars from years. Lush, broad canopy casting a wide shade. A worn "
           "stone table sits beneath it, edges rounded and surface polished smooth "
           "from decades of use. A magpie nest rests in the upper branches. Warm "
           "late-afternoon sunlight casts a long shadow across the courtyard. "
           "Nostalgic, peaceful, photorealistic, golden-hour lighting.")

anchor(0, 1, 0.15, False, _P_EARLY,
       "老宅院门口的老槐树", "树干极粗，需两人合抱")
anchor(2, 2, 0.30, False, _P_MID,
       "树下有一张石头桌子", "石桌供村民夏天乘凉、下棋、打牌")
anchor(5, 3, 0.42, False, _P_MID,
       "树皮开裂，呈一道道纵向裂纹")
anchor(8, 4, 0.55, False, _P_MID,
       "傍晚夕阳下，树影被拉得很长，横跨整个院子")
anchor(10, 5, 0.62, False, _P_MID,
       "石桌是家人团聚、谈天的地方")
anchor(12, 6, 0.72, False, _P_MID,
       "树上有喜鹊窝", "每年春天喜鹊归巢，被视为好兆头")
anchor(13, 8, 0.85, True, _P_FULL,
       "冬季落叶后，光秃枝干落满雪，远看如水墨画", "四季变化分明")
anchor(16, 9, 0.88, True, _P_FULL,
       "树干布满疤痕（岁月痕迹）", "枝繁叶茂，树荫宽大")
anchor(17, 10, 0.90, True, _P_FULL,
       "石桌边角磨圆、桌面被坐得发亮（长年使用痕迹）",
       "承载童年与家族记忆的情感地标")

# ----------------------------------------------------------------------
# 合并为稀疏快照表
# ----------------------------------------------------------------------
snapshots = {}
for idx in sorted(set(_background_at) | set(_logic_at) | set(_anchor_at)):
    entry = {}
    if idx in _background_at:
        entry["background"] = _background_at[idx]
    if idx in _logic_at:
        entry["logic_outline"] = _logic_at[idx]
    if idx in _anchor_at:
        entry["anchor"] = _anchor_at[idx]
    snapshots[str(idx)] = entry

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"已生成 {OUT}：{len(snapshots)} 个 chunk 的快照")
print(f"  背景笔记最终 {len(_bg_notes)} 条 | 时间线事件最终 {len(_events)} 个 "
      f"| 锚点属性最终 {len(_attrs)} 条")
