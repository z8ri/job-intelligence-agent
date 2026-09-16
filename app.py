"""Job Intelligence Agent — Streamlit chat UI.

Run: streamlit run app.py
"""

import base64
import html
import time
from pathlib import Path

import streamlit as st

import src.llm  # noqa: F401  (loads .env via auto-init)

ASSETS_DIR = Path(__file__).parent / "assets"


# ---------------------------------------------------------------------------
# Pipeline resources (cached singletons)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Booting pipeline…")
def get_pipeline_resources():
    from src.pipeline.graph import build_graph, _get_ir_system, _get_bm25_system, _get_dense_system
    import src.classification.classifier as clf_mod
    app = build_graph()
    _get_ir_system()
    _get_bm25_system()
    _get_dense_system()  # Planner can route to dense/hybrid_rrf on the very first query
    if clf_mod._classifier_instance is None:
        clf_mod.load_classifier()
    return app


# ---------------------------------------------------------------------------
# Page config + visual language
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Job Intelligence",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #faf9f5;
    --bg-card: #ffffff;
    --bg-soft: #f4f2ec;
    --border: #ebe9e0;
    --border-strong: #d9d6cc;
    --text: #28272a;
    --text-muted: #82817a;
    --accent: #c15f3c;
    --accent-soft: #f0e3da;
}

html, body, [data-testid="stAppViewContainer"] { background: var(--bg) !important; }
.stApp { background: var(--bg); font-family: 'Inter', system-ui, sans-serif; color: var(--text); }
[data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }

.block-container {
    max-width: 760px !important;
    padding-top: 2rem !important;
    padding-bottom: 8rem !important;
}

/* --- Sidebar (desktop layout) --- */
[data-testid="stSidebar"] {
    background: var(--bg) !important;
    background-color: var(--bg) !important;
    border-right: 1px solid var(--border) !important;
    width: 264px !important;
    min-width: 264px !important;
}
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div > div {
    background: var(--bg) !important;
    background-color: var(--bg) !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
[data-testid="stSidebar"] > div:first-child {
    padding: 1.4rem 0.9rem !important;
}

.sidebar-brand {
    text-align: center;
    padding: 0.4rem 0 1.3rem 0;
    margin-bottom: 0.8rem;
    border-bottom: 1px solid var(--border);
}
.sidebar-shield {
    width: 38px;
    height: auto;
    margin: 0 auto 0.7rem auto;
    display: block;
}
.sidebar-title {
    font-family: 'Newsreader', serif;
    font-size: 1.05rem;
    font-weight: 500;
    color: var(--text);
    letter-spacing: -0.005em;
}
.sidebar-subtitle {
    font-size: 0.68rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 4px;
    font-weight: 500;
}

.sidebar-section-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 1.6rem 0 0.5rem 0.2rem;
}
.sidebar-recent-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 0.85rem;
    color: var(--text);
    line-height: 1.4;
    margin-bottom: 6px;
}

/* Sidebar buttons: scoped style overriding the main outline-card look */
[data-testid="stSidebar"] .stButton > button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 9px 14px !important;
    font-size: 0.88rem !important;
    text-align: left !important;
    color: var(--text) !important;
    min-height: 38px !important;
    font-weight: 500 !important;
    line-height: 1.3 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-soft) !important;
    border-color: var(--border-strong) !important;
    color: var(--text) !important;
}

/* Active conversation uses type="primary": warm-gray background, slightly bolder weight. */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #e8e4d6 !important;
    background-color: #e8e4d6 !important;
    border: 1px solid #d4cfbe !important;
    color: var(--text) !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: #ddd9c8 !important;
    background-color: #ddd9c8 !important;
    border-color: #c8c2af !important;
    color: var(--text) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* Hide the sidebar's collapse button; keep collapsedControl (re-open arrow) visible. */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebar"] button[kind="header"],
[data-testid="stSidebar"] button[kind="headerNoPadding"] {
    display: none !important;
}

/* --- Hero --- */
.hero-title {
    font-family: 'Newsreader', serif;
    font-size: 2.8rem;
    font-weight: 400;
    color: var(--text);
    margin-top: 4.5rem;
    margin-bottom: 0.6rem;
    line-height: 1.12;
    letter-spacing: -0.015em;
}
.hero-sub {
    color: var(--text-muted);
    font-size: 1rem;
    margin-bottom: 2.8rem;
    line-height: 1.5;
}

/* --- Suggested prompt buttons (outline cards) --- */
.stButton > button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    text-align: left !important;
    color: var(--text) !important;
    font-weight: 500 !important;
    font-size: 0.92rem !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
    min-height: 64px;
    line-height: 1.45;
    white-space: normal !important;
    justify-content: flex-start !important;
}
.stButton > button:hover {
    border-color: var(--border-strong) !important;
    background: #fdfcf8 !important;
    color: var(--text) !important;
}
.stButton > button:focus { outline: none !important; box-shadow: 0 0 0 3px var(--accent-soft) !important; }
.stButton > button p { color: inherit !important; }

/* --- Chat input: pill input (fixed-bottom, soft elevated) --- */
/* Kill the white slab. DOM nesting:
   [stBottom] (white) > div.st-emotion-cache-* (white) > [stBottomBlockContainer] > [stChatInput] */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {
    background: var(--bg) !important;
    background-color: var(--bg) !important;
    border-top: none !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] {
    background: var(--bg) !important;
    background-color: var(--bg) !important;
    border-top: none !important;
    padding: 1.5rem 1rem 1.8rem 1rem !important;
}

/* 2. Pill outer shell (the white rounded rectangle) */
[data-testid="stChatInput"] > div {
    background: var(--bg-card) !important;
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 24px !important;
    box-shadow: 0 4px 16px rgba(40, 39, 42, 0.05),
                0 1px 2px rgba(40, 39, 42, 0.04) !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
    overflow: hidden !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #b4afa1 !important;
    box-shadow: 0 6px 22px rgba(40, 39, 42, 0.08),
                0 1px 2px rgba(40, 39, 42, 0.04) !important;
}

/* 3. Kill BaseWeb's gray inner wrappers (the gray rectangle inside the pill) */
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] [data-baseweb="input"],
[data-testid="stChatInput"] > div > div,
[data-testid="stChatInput"] > div > div > div {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* 4. Textarea itself */
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    color: var(--text) !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 1rem !important;
    line-height: 1.55 !important;
    padding: 18px 22px !important;
    min-height: 56px !important;
    caret-color: var(--accent) !important;
    resize: none !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-muted) !important;
    opacity: 0.62 !important;
    font-size: 1rem !important;
    font-family: 'Inter', system-ui, sans-serif !important;
}
[data-testid="stChatInput"] textarea:focus {
    box-shadow: none !important;
    outline: none !important;
}

/* 5. Submit button hidden completely (Enter to submit) */
[data-testid="stChatInput"] button,
[data-testid="stChatInput"] button[kind="primary"],
[data-testid="stChatInput"] [data-testid="stChatInputSubmitButton"] {
    display: none !important;
}

/* --- Chat messages: minimalist chat-style --- */
/* USER: custom HTML bubble (rendered via raw markdown, bypasses streamlit chat_message).
   ASSISTANT: streamlit chat_message stripped down to plain text, no avatar. */

.msg-user-row {
    display: flex;
    justify-content: flex-end;
    margin: 0.6rem 0;
    width: 100%;
}
.msg-user-bubble {
    background: #efece2;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 11px 17px;
    max-width: 78%;
    color: var(--text);
    line-height: 1.5;
    font-size: 1rem;
    font-family: 'Inter', system-ui, sans-serif;
    word-wrap: break-word;
    white-space: pre-wrap;
}

/* Assistant chat_message: strip framing, hide avatar, full-width plain text */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0.5rem 0 !important;
    gap: 0 !important;
    align-items: flex-start !important;
}
[data-testid="stChatMessage"] [data-testid^="chatAvatarIcon"],
[data-testid="stChatMessage"] [data-testid^="stChatMessageAvatar"] {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"],
[data-testid="stChatMessage"] > div:last-child {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
    max-width: 100% !important;
    color: var(--text) !important;
    margin: 0 !important;
}

/* --- Job result cards --- */
.jobs-heading {
    margin-top: 1.4rem;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-muted);
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
[data-testid="stContainer"] > [data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 4px !important;
}
.job-cat {
    color: var(--accent);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.job-title { font-size: 1rem; font-weight: 600; color: var(--text); margin: 0 0 2px 0; }
.job-meta { font-size: 0.85rem; color: var(--text-muted); }

/* --- Status block (pipeline progress) --- */
[data-testid="stStatusWidget"], details[data-testid="stExpander"] {
    background: var(--bg-soft) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}

/* --- Progress bars --- */
.stProgress > div > div > div > div { background: var(--accent) !important; }

/* --- Metric --- */
[data-testid="stMetric"] { background: transparent !important; }
[data-testid="stMetricValue"] {
    font-family: 'Newsreader', serif !important;
    font-weight: 500 !important;
    color: var(--text) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* --- Divider --- */
hr { border-color: var(--border) !important; opacity: 0.6; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Suggested starter prompts
# ---------------------------------------------------------------------------

PRESET_QUERIES = [
    {"emoji": "💵", "title": "Senior Python · remote · $150k+",
     "query": "senior python engineer remote $150k+"},
    {"emoji": "🏙️", "title": "Frontend role in NYC, hybrid welcomed",
     "query": "frontend job in NYC hybrid"},
    {"emoji": "🧪", "title": "ML internship open to non-CS majors",
     "query": "ML internship that accepts non-CS major"},
    {"emoji": "🌐", "title": "Fullstack at a startup, ~$130k",
     "query": "fullstack engineer at startup hybrid 130k"},
]

NODE_LABELS = {
    "query_understanding": "Understanding your query",
    "query_expansion":     "Expanding keywords",
    "candidate_loading":   "Loading candidates",
    "unified_scoring":     "Multi-field scoring",
    "collection_fusion":   "Fusing scores",
    "verification":        "Verifying results",
    "classification":      "Classifying categories",
    "answer_generation":   "Generating answer",
    "reject":              "Not a job query — skipping retrieval",
    "clarify":             "Need a bit more detail — asking a follow-up",
}


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

@st.cache_data
def _shield_b64() -> str:
    with open(ASSETS_DIR / "jhu_shield.svg", "rb") as f:
        return base64.b64encode(f.read()).decode()


# --- Conversation history helpers ---------------------------------------------

def _new_conv_id() -> str:
    return f"conv_{int(time.time() * 1000)}"


def _save_current_to_history() -> None:
    """Persist the active conversation into the history dict (no-op if empty)."""
    cur_id = st.session_state.get("current_conv_id")
    msgs = st.session_state.get("messages") or []
    if not cur_id or not msgs:
        return
    title = msgs[0]["content"]
    if len(title) > 42:
        title = title[:42] + "…"
    st.session_state.conversations[cur_id] = {
        "title": title,
        "messages": list(msgs),
    }


def _new_conversation() -> None:
    """Save the active conversation, then start a fresh empty one."""
    _save_current_to_history()
    st.session_state.current_conv_id = _new_conv_id()
    st.session_state.messages = []


def _load_conversation(conv_id: str) -> None:
    """Save the active conversation, then switch to a saved one."""
    _save_current_to_history()
    conv = st.session_state.conversations.get(conv_id)
    if not conv:
        return
    st.session_state.current_conv_id = conv_id
    st.session_state.messages = list(conv["messages"])


def render_sidebar():
    with st.sidebar:
        st.markdown(
            f'<div class="sidebar-brand">'
            f'<img src="data:image/svg+xml;base64,{_shield_b64()}" class="sidebar-shield" alt="JHU"/>'
            f'<div class="sidebar-title">Job Intelligence</div>'
            f'<div class="sidebar-subtitle">IRWA · 26 Spring</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if st.button("✚  New chat", key="sidebar_new_chat", use_container_width=True):
            _new_conversation()
            st.rerun()

        # Keep the active conversation's snapshot in the history dict in sync,
        # so its title preview updates as the conversation grows.
        _save_current_to_history()

        if st.session_state.conversations:
            st.markdown('<div class="sidebar-section-label">Recent</div>', unsafe_allow_html=True)
            for conv_id in reversed(list(st.session_state.conversations.keys())):
                conv = st.session_state.conversations[conv_id]
                is_current = conv_id == st.session_state.current_conv_id
                if st.button(
                    conv["title"],
                    key=f"conv_{conv_id}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary",
                ):
                    if conv_id != st.session_state.current_conv_id:
                        _load_conversation(conv_id)
                        st.rerun()


def render_welcome():
    st.markdown('<div class="hero-title">What kind of role are you looking for?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-sub">Ask in plain English — salary, location, tech stack, '
        'remote vs. hybrid. We search 2,311 tech positions and rank by multi-field fit.</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    for i, p in enumerate(PRESET_QUERIES):
        with cols[i % 2]:
            if st.button(f"{p['emoji']}  {p['title']}", key=f"preset_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": p["query"]})
                st.rerun()


def render_job_results(result):
    jobs = result.get("classified_jobs") or []
    if not jobs:
        return

    st.markdown('<div class="jobs-heading">Top Matches</div>', unsafe_allow_html=True)
    for idx, job in enumerate(jobs):
        with st.container(border=True):
            cat = (job.get("predicted_category") or "").upper()
            title = job.get("title") or "Untitled position"
            company = job.get("company") or "—"
            location = job.get("location") or "—"
            score = job.get("final_score") or 0.0

            cols = st.columns([4, 1])
            with cols[0]:
                if cat:
                    st.markdown(f'<div class="job-cat">{cat}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="job-title">{title}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="job-meta">{company} · {location}</div>', unsafe_allow_html=True)
            with cols[1]:
                st.metric("Score", f"{score:.2f}")

            bd = job.get("score_breakdown") or {}
            if bd:
                st.divider()
                items = list(bd.items())
                b_cols = st.columns(len(items))
                for j, (k, v) in enumerate(items):
                    with b_cols[j]:
                        st.caption(k.replace("_", " ").title())
                        st.progress(min(max(float(v), 0.0), 1.0))


def render_message(msg):
    role = msg["role"]
    content = msg["content"]

    if role == "user":
        # User: warm beige bubble, right-aligned, rendered as raw HTML to bypass
        # streamlit's chat_message internals. Escape user content to avoid XSS.
        safe = html.escape(content).replace("\n", "<br>")
        st.markdown(
            f'<div class="msg-user-row"><div class="msg-user-bubble">{safe}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        # Assistant: plain markdown text, no avatar, no bubble (minimalist chat style).
        with st.chat_message("assistant"):
            st.markdown(content)
            if "results" in msg:
                render_job_results(msg["results"])


def run_pipeline(app, query, session_id):
    """Stream pipeline updates inside an st.status block.

    No `ir_mode` in config: the Planner (query_understanding's retrieval_mode
    classification) picks TF-IDF/BM25/Dense/RRF + reranker per query. Passing
    session_id lets preferences carry over across turns within the same chat.
    """
    state = {"user_query": query, "top_k": 5, "config": {}, "session_id": session_id}
    with st.status("Thinking…", expanded=False) as status:
        for chunk in app.stream(state, stream_mode="updates"):
            for node, updates in chunk.items():
                label = NODE_LABELS.get(node, node.replace("_", " ").title())
                st.markdown(f"·  {label}")
                if updates:
                    state.update(updates)
        status.update(label="Done", state="complete")
    return state


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversations" not in st.session_state:
        st.session_state.conversations = {}
    if "current_conv_id" not in st.session_state:
        st.session_state.current_conv_id = _new_conv_id()

    render_sidebar()

    if not st.session_state.messages:
        render_welcome()

    # Render existing chat history
    for msg in st.session_state.messages:
        render_message(msg)

    # New input
    user_input = st.chat_input("Ask about salary, location, tech stack…")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun()

    # If the latest message is from the user with no assistant reply yet, run the pipeline.
    needs_response = (
        st.session_state.messages
        and st.session_state.messages[-1]["role"] == "user"
    )
    if needs_response:
        last_query = st.session_state.messages[-1]["content"]
        with st.chat_message("assistant"):
            try:
                app = get_pipeline_resources()
                result = run_pipeline(app, last_query, st.session_state.current_conv_id)
                answer = result.get("answer") or "Here are the top matches I found."
                st.markdown(answer)
                render_job_results(result)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "results": result,
                })
            except Exception as e:
                err = f"Pipeline error: {e}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
        st.rerun()


if __name__ == "__main__":
    main()
