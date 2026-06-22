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

from narrator_flow.state import TranscriptChunk
from narrator_flow.streaming import stream_chunks
from narrator_flow.streaming_app.session import NarratorSession

load_dotenv()

st.set_page_config(page_title="口述史实时分析 Agent", layout="wide")

DATA_DIR = Path("data/transcripts")


# ----------------------------------------------------------------------
# 处理一个 chunk（两种模式共用）
# ----------------------------------------------------------------------
def process_chunk(session: NarratorSession, chunk: TranscriptChunk, demo: bool = False) -> None:
    msg = (f"正在回放第 {chunk.index + 1} 段（免 key 演示，瞬时）..." if demo
           else f"正在处理第 {chunk.index + 1} 段（调用 DeepSeek，可能需要数十秒）...")
    with st.spinner(msg):
        session.process_chunk(chunk)


# ----------------------------------------------------------------------
# 三条流水线结果展示（两种模式共用）
# ----------------------------------------------------------------------
def render_pipelines(state) -> None:
    # 第 4 条流水线：给年轻人的"建议追问"——最贴近对话当下、最可行动，放在最上方
    if getattr(state, "follow_up_questions", None):
        st.markdown("#### 💡 建议你可以这样追问")
        for q in state.follow_up_questions:
            st.success(q)
        st.caption("（这些是给“听的人”的实时建议，不会写入记忆档案；不想问可忽略）")

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
        st.caption(f"年代估计：{bg.era_estimate or '未知'}")
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
mode = st.sidebar.radio(
    "模式",
    ["预制 Demo 播放", "自由输入（实时模拟）", "🎙️ 音频上传（真实 ASR）",
     "📞 实时通话（实验）"],
)


# ========================================================================
# 模式一：预制 Demo 播放
# ========================================================================
if mode == "预制 Demo 播放":

    # 免 key 演示用的预录回放，目前只针对示例「老张的故事」准备了快照
    REPLAY_TRANSCRIPT = "sample_story.json"

    def init_demo_state(transcript_path: str, demo_mode: bool) -> None:
        if demo_mode:
            st.session_state.demo_session = NarratorSession.demo(
                output_dir=Path("output_gui/demo"), think_delay=0.3
            )
        else:
            st.session_state.demo_session = NarratorSession(output_dir=Path("output_gui/demo"))
        st.session_state.demo_chunks = list(stream_chunks(transcript_path))
        st.session_state.demo_cursor = 0
        st.session_state.demo_path = transcript_path
        st.session_state.demo_mode = demo_mode
        st.session_state.demo_history = []

    transcript_files = sorted(DATA_DIR.glob("*.json"))
    transcript_names = [f.name for f in transcript_files]
    selected_name = st.sidebar.selectbox("选择 transcript 文件", transcript_names)
    selected_path = str(DATA_DIR / selected_name)

    demo_mode = st.sidebar.checkbox(
        "🆓 免 key 演示（回放预录结果，不调用 AI）",
        value=True,
        help="勾选后无需 DeepSeek API key、不产生费用，瞬时回放预录的分析结果；"
             "取消勾选则调用真实 DeepSeek（需在 .env 配置 key）。",
    )
    if demo_mode and selected_name != REPLAY_TRANSCRIPT:
        st.sidebar.warning(f"免 key 回放目前只为「{REPLAY_TRANSCRIPT}」准备了预录结果，"
                           f"其他文件请取消勾选并配置 key。")

    # 切换 transcript 或切换演示开关时，重建会话
    if ("demo_session" not in st.session_state
            or st.session_state.get("demo_path") != selected_path
            or st.session_state.get("demo_mode") != demo_mode):
        init_demo_state(selected_path, demo_mode)

    col_a, col_b = st.sidebar.columns(2)
    step_clicked = col_a.button("▶ 下一段", use_container_width=True)
    reset_clicked = col_b.button("⟲ 重置", use_container_width=True)
    auto_play = st.sidebar.checkbox("自动连续播放剩余全部段落", value=False)

    if reset_clicked:
        init_demo_state(selected_path, demo_mode)
        st.rerun()

    total = len(st.session_state.demo_chunks)
    cursor = st.session_state.demo_cursor
    st.sidebar.progress(cursor / total if total else 0, text=f"{cursor}/{total} 段")

    if (step_clicked or auto_play) and cursor < total:
        chunk = st.session_state.demo_chunks[cursor]
        process_chunk(st.session_state.demo_session, chunk, demo=demo_mode)
        st.session_state.demo_history.append(chunk)
        st.session_state.demo_cursor += 1
        if auto_play and st.session_state.demo_cursor < total:
            st.rerun()

    st.title("🌳 口述史实时分析 Agent — 预制Demo播放")

    session = st.session_state.demo_session
    state = session.state

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
elif mode == "自由输入（实时模拟）":

    def init_free_state() -> None:
        st.session_state.free_session = NarratorSession(output_dir=Path("output_gui/free"))
        st.session_state.free_history = []
        st.session_state.free_next_index = 0

    if "free_session" not in st.session_state:
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

    session = st.session_state.free_session
    state = session.state

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
        process_chunk(session, chunk)
        st.session_state.free_history.append(chunk)
        st.session_state.free_next_index += 1
        st.rerun()

    render_pipelines(state)


# ========================================================================
# 模式三：音频上传（真实 ASR → 真实分析）
# ========================================================================
elif mode == "🎙️ 音频上传（真实 ASR）":
    import tempfile

    st.sidebar.info(
        "上传一段口述录音，用本地 faster-whisper 转成文字后，逐段送入三条流水线分析。"
        "\n\n注意：① 需先安装 ASR 依赖 `pip install -e \".[asr]\"`；"
        "② 分析调用真实 DeepSeek，需在 .env 配置 key。"
    )
    asr_model = st.sidebar.selectbox(
        "ASR 模型大小", ["tiny", "base", "small", "medium"], index=2,
        help="越大越准越慢；small 在中文与速度间较平衡。首次使用会下载模型。",
    )

    def init_audio_state() -> None:
        st.session_state.audio_session = NarratorSession(output_dir=Path("output_gui/audio"))
        st.session_state.audio_chunks = []
        st.session_state.audio_cursor = 0
        st.session_state.audio_history = []
        st.session_state.audio_name = None

    if "audio_session" not in st.session_state:
        init_audio_state()

    st.title("🎙️ 口述史实时分析 Agent — 音频上传（真实 ASR）")

    uploaded = st.file_uploader("上传录音文件", type=["wav", "mp3", "m4a", "flac", "ogg"])

    # 新文件上传后：转写成片段
    if uploaded is not None and uploaded.name != st.session_state.get("audio_name"):
        init_audio_state()
        st.session_state.audio_name = uploaded.name
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = tmp.name
        try:
            from narrator_flow.streaming_app.asr import transcribe_to_chunks
            with st.spinner(f"正在用 faster-whisper（{asr_model}）转写音频，首次会下载模型，请稍候…"):
                st.session_state.audio_chunks = transcribe_to_chunks(tmp_path, model_size=asr_model)
            st.success(f"转写完成：共 {len(st.session_state.audio_chunks)} 个片段。")
        except RuntimeError as e:
            st.error(str(e))
        except Exception as e:  # noqa: BLE001
            st.error(f"转写失败：{e}")

    chunks = st.session_state.audio_chunks
    if chunks:
        with st.expander("转写全文（ASR 结果）", expanded=True):
            for c in chunks:
                done = "✅" if c.index < st.session_state.audio_cursor else "⏳"
                st.markdown(f"{done} **[{c.index + 1}]** {c.text}")

        total = len(chunks)
        cursor = st.session_state.audio_cursor
        col_a, col_b = st.sidebar.columns(2)
        step_clicked = col_a.button("▶ 分析下一段", use_container_width=True)
        reset_clicked = col_b.button("⟲ 重置分析", use_container_width=True)
        st.sidebar.progress(cursor / total if total else 0, text=f"已分析 {cursor}/{total} 段")

        if reset_clicked:
            sess = NarratorSession(output_dir=Path("output_gui/audio"))
            st.session_state.audio_session = sess
            st.session_state.audio_cursor = 0
            st.rerun()

        if step_clicked and cursor < total:
            process_chunk(st.session_state.audio_session, chunks[cursor])
            st.session_state.audio_cursor += 1
            st.rerun()

    render_pipelines(st.session_state.audio_session.state)


# ========================================================================
# 模式四：实时通话（实验，阶段1：连续麦 → VAD 切句 → 实时字幕）
# ========================================================================
else:
    import queue as _queue

    st.title("📞 实时通话 — 实时字幕（实验·阶段1）")
    st.sidebar.info(
        "连续麦克风 → VAD 自动切句 → faster-whisper 逐句转写为字幕。"
        "\n\n阶段1 只验证'麦→字幕'链路，暂不接入分析。"
        "\n需安装：`pip install -e \".[live]\"`；首次会下载语音模型（国内设 HF 镜像）。"
    )
    asr_model = st.sidebar.selectbox("ASR 模型大小", ["tiny", "base", "small"], index=0,
                                     help="实时场景建议 tiny/base 更跟手；small 更准但更慢。")

    # 惰性导入可选依赖，缺了给友好提示而非崩溃
    try:
        from streamlit_webrtc import WebRtcMode, webrtc_streamer
        from narrator_flow.streaming_app.live_capture import (
            VADSegmenter, frame_to_pcm16, transcribe_pcm16,
        )
        _live_ok = True
    except Exception as e:  # noqa: BLE001
        _live_ok = False
        st.error(f"实时通话依赖未就绪：{e}\n请运行：pip install -e \".[live]\"")

    if _live_ok:
        if "live_transcript" not in st.session_state:
            st.session_state.live_transcript = []

        col_l, col_r = st.columns([1, 3])
        with col_l:
            if st.button("🗑 清空字幕", use_container_width=True):
                st.session_state.live_transcript = []
        with col_r:
            st.caption("点击下方 START 并允许麦克风权限；说完一句停顿约 0.7s 即自动出字。")

        webrtc_ctx = webrtc_streamer(
            key="live-call",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=512,
            media_stream_constraints={"audio": True, "video": False},
        )

        status = st.empty()
        transcript_box = st.empty()

        def _render_transcript() -> None:
            lines = st.session_state.live_transcript
            transcript_box.markdown(
                "#### 实时字幕\n" + ("\n".join(f"- {t}" for t in lines) if lines
                                     else "_（还没有内容，开始说话试试）_")
            )

        _render_transcript()

        if webrtc_ctx.state.playing:
            segmenter = VADSegmenter()
            status.info("🎙️ 通话中…（持续聆听）")
            while True:
                try:
                    frames = webrtc_ctx.audio_receiver.get_frames(timeout=1)
                except _queue.Empty:
                    status.warning("⏳ 等待音频…（确认已允许麦克风）")
                    continue
                except Exception:  # noqa: BLE001 — 连接已断开
                    break
                for frame in frames:
                    try:
                        pcm = frame_to_pcm16(frame)
                    except Exception:  # noqa: BLE001
                        continue
                    for utt in segmenter.add(pcm):
                        status.info("📝 正在转写一句…")
                        text = transcribe_pcm16(utt, model_size=asr_model)
                        if text:
                            st.session_state.live_transcript.append(text)
                            _render_transcript()
                status.info("🎙️ 通话中…（持续聆听）")
        else:
            status.caption("未在通话。点击 START 开始。")
