"""Streamlit GUI：实时查看三条流水线的输出。

两种模式：
- 预制Demo：逐段播放 data/transcripts/*.json 中预先准备的文本
- 自由输入：在文本框里手动输入一段"主讲人"刚说的话，模拟真实使用场景

运行方式：
    streamlit run src/narrator_flow/app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from narrator_flow.flow import NarratorFlow
from narrator_flow.state import TranscriptChunk
from narrator_flow.streaming import stream_chunks

load_dotenv()

st.set_page_config(page_title="口述史实时分析 Agent", layout="wide")

DATA_DIR = Path("data/transcripts")


# ----------------------------------------------------------------------
# 处理一个 chunk（两种模式共用）
# ----------------------------------------------------------------------
def process_chunk(flow: NarratorFlow, chunk: TranscriptChunk) -> None:
    with st.spinner(f"正在处理第 {chunk.index + 1} 段（调用 DeepSeek，可能需要数十秒）..."):
        flow.process_chunk(chunk)


# ----------------------------------------------------------------------
# 三条流水线结果展示（两种模式共用）
# ----------------------------------------------------------------------
def render_pipelines(state) -> None:
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📜 流水线A：逻辑大纲")
        outline = state.logic_outline
        st.caption(f"更新方式：{outline.last_update_mode or '-'} | 事件数：{len(outline.events)}")
        if outline.raw_outline_text:
            st.markdown(outline.raw_outline_text)
        if outline.open_threads:
            st.markdown("**待澄清线索：**")
            for t in outline.open_threads:
                st.markdown(f"- {t}")
        with st.expander("原始 JSON"):
            st.json(outline.model_dump())

    with col2:
        st.subheader("📚 流水线B：背景知识")
        bg = state.background
        st.caption(f"年代估计：{bg.era_estimate or '未知'}（置信度 {bg.confidence:.2f}）")
        for n in bg.notes:
            st.markdown(f"- {n}")
        with st.expander("原始 JSON"):
            st.json(bg.model_dump())

    with col3:
        st.subheader("🖼️ 流水线C：锚定物 + 生图")
        anchor = state.anchor
        st.caption(
            f"候选：{anchor.candidate_name or '未确定'}（提及 {anchor.mention_count} 次） "
            f"| 详实度：{anchor.prompt_detail_score:.2f}"
        )
        if anchor.descriptive_attributes:
            st.markdown("**已知描述细节：**")
            for a in anchor.descriptive_attributes:
                st.markdown(f"- {a}")
        if anchor.image_prompt:
            st.markdown("**当前图像提示词：**")
            st.code(anchor.image_prompt, language="text")
        if anchor.image_generated and anchor.image_path:
            st.success(f"已触发生图（stub）：{anchor.image_path}")
            img_path = Path(anchor.image_path)
            if img_path.exists():
                st.text(img_path.read_text(encoding="utf-8"))
        with st.expander("原始 JSON"):
            st.json(anchor.model_dump())


# ----------------------------------------------------------------------
# 模式选择
# ----------------------------------------------------------------------
st.sidebar.title("控制面板")
mode = st.sidebar.radio("模式", ["预制 Demo 播放", "自由输入（实时模拟）"])


# ========================================================================
# 模式一：预制 Demo 播放
# ========================================================================
if mode == "预制 Demo 播放":

    def init_demo_state(transcript_path: str) -> None:
        st.session_state.demo_flow = NarratorFlow(
            transcript_path=transcript_path, output_dir=Path("output_gui/demo")
        )
        st.session_state.demo_chunks = list(stream_chunks(transcript_path))
        st.session_state.demo_cursor = 0
        st.session_state.demo_path = transcript_path
        st.session_state.demo_history = []

    transcript_files = sorted(DATA_DIR.glob("*.json"))
    transcript_names = [f.name for f in transcript_files]
    selected_name = st.sidebar.selectbox("选择 transcript 文件", transcript_names)
    selected_path = str(DATA_DIR / selected_name)

    if "demo_flow" not in st.session_state or st.session_state.get("demo_path") != selected_path:
        init_demo_state(selected_path)

    col_a, col_b = st.sidebar.columns(2)
    step_clicked = col_a.button("▶ 下一段", use_container_width=True)
    reset_clicked = col_b.button("⟲ 重置", use_container_width=True)
    auto_play = st.sidebar.checkbox("自动连续播放剩余全部段落", value=False)

    if reset_clicked:
        init_demo_state(selected_path)
        st.rerun()

    total = len(st.session_state.demo_chunks)
    cursor = st.session_state.demo_cursor
    st.sidebar.progress(cursor / total if total else 0, text=f"{cursor}/{total} 段")

    if (step_clicked or auto_play) and cursor < total:
        chunk = st.session_state.demo_chunks[cursor]
        process_chunk(st.session_state.demo_flow, chunk)
        st.session_state.demo_history.append(chunk)
        st.session_state.demo_cursor += 1
        if auto_play and st.session_state.demo_cursor < total:
            st.rerun()

    st.title("🌳 口述史实时分析 Agent — 预制Demo播放")

    flow = st.session_state.demo_flow
    state = flow.state

    st.subheader("叙述内容")
    if st.session_state.demo_history:
        last_chunk = st.session_state.demo_history[-1]
        st.markdown(f"**最新一段（第 {last_chunk.index + 1} 段）：**")
        st.info(last_chunk.text)
    else:
        st.caption("尚未播放任何段落，点击左侧「下一段」开始。")

    if cursor < total:
        st.caption(f"下一段预览（第 {st.session_state.demo_chunks[cursor].index + 1} 段）：")
        st.text(st.session_state.demo_chunks[cursor].text)
    else:
        st.success("全部段落已播放完毕。")

    with st.expander("已播放的全部原文", expanded=False):
        for c in st.session_state.demo_history:
            st.markdown(f"**[{c.index + 1}]** {c.text}")

    render_pipelines(state)


# ========================================================================
# 模式二：自由输入（实时模拟真实使用场景）
# ========================================================================
else:

    def init_free_state() -> None:
        st.session_state.free_flow = NarratorFlow(
            transcript_path="(manual-input)", output_dir=Path("output_gui/free")
        )
        st.session_state.free_history = []
        st.session_state.free_next_index = 0

    if "free_flow" not in st.session_state:
        init_free_state()

    reset_clicked = st.sidebar.button("⟲ 清空对话，重新开始", use_container_width=True)
    if reset_clicked:
        init_free_state()
        st.rerun()

    st.sidebar.info(
        "在下方输入框里输入主讲人刚刚说的一段话，点击「发送」后会立刻触发三条流水线的实时分析。"
        "可以一句一句输入，模拟真实边听边记的场景。"
    )

    st.title("🎙️ 口述史实时分析 Agent — 自由输入模式")

    flow = st.session_state.free_flow
    state = flow.state

    with st.expander("对话历史", expanded=True):
        if st.session_state.free_history:
            for c in st.session_state.free_history:
                st.markdown(f"**[{c.index + 1}]** {c.text}")
        else:
            st.caption("还没有任何输入，请在下方输入第一段叙述内容。")

    with st.form("free_input_form", clear_on_submit=True):
        user_text = st.text_area(
            "主讲人刚刚说的内容",
            height=120,
            placeholder="例如：我跟你说啊，我们家以前住的那个院子，门口有棵大槐树，可粗了……",
        )
        submitted = st.form_submit_button("发送 ▶")

    if submitted and user_text.strip():
        chunk = TranscriptChunk(index=st.session_state.free_next_index, text=user_text.strip())
        process_chunk(flow, chunk)
        st.session_state.free_history.append(chunk)
        st.session_state.free_next_index += 1
        st.rerun()

    render_pipelines(state)
