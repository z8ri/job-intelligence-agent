"""Comparison page: pipeline stages side by side, eval metrics, optional live search.

Run: streamlit run app.py  (this page appears in the sidebar)
"""

from pathlib import Path

import streamlit as st

from src.agent.compare_view import evidence_lines, load_results, metrics_rows, paired_rows, system_columns
from src.agent.snapshots import SnapshotStore

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "data" / "eval_results_agent" / "run1"
SNAPSHOTS = ROOT / "data" / "agent" / "snapshots.db"
BADGE = {"valid": "✅", "wrong": "❌", "unlabeled": "▫️"}

st.set_page_config(page_title="Agent comparison", layout="wide")
st.title("Pipeline comparison")

res = load_results(RESULTS)
tab_q, tab_m, tab_live = st.tabs(["Per query", "Metrics", "Live search"])


@st.cache_resource
def _store():
    return SnapshotStore(SNAPSHOTS) if SNAPSHOTS.exists() else None


def lookup(key: str) -> dict:
    store = _store()
    snap = store.latest(key) if store else None
    return {"title": snap.title, "company": snap.company} if snap else {"title": key, "company": ""}


with tab_q:
    if not res["runs"]:
        st.info(f"No eval results under {RESULTS}. Run `python -m scripts.run_agent_eval run` first.")
    else:
        ids = [q for q, r in res["runs"].items() if "error" not in r]
        qid = st.selectbox("Query", ids, format_func=lambda i: f"{i} ({res['runs'][i]['split']}): {res['runs'][i]['conditions']['raw_query']}")
        run = res["runs"][qid]
        cols = system_columns(run, res["qrels"].get(qid, {}), lookup)
        st.caption("✅ confirmed match · ❌ labelled, not a confirmed match · ▫️ unlabeled. Labels are silver unless marked human.")
        for col, c in zip(st.columns(len(cols)), cols):
            with col:
                st.subheader(c["title"])
                for r in c["rows"]:
                    src = " (human)" if r["label_source"] == "human" else ""
                    st.markdown(f"{BADGE[r['verdict']]} **{r['rank']}.** {r['title']} — {r['company']}{src}")
                if c["excluded"]:
                    with st.expander(f"Excluded with evidence ({len(c['excluded'])})"):
                        for e in c["excluded"]:
                            st.write(e["title"])
                for reason in c["reasons"]:
                    st.warning(reason)
                if c["usage"]:
                    st.caption(f"LLM calls {c['usage']['llm_calls']} · est ${c['usage']['est_cost_usd']:.4f}")

with tab_m:
    if not res["metrics"]:
        st.info("No metrics.json yet. Run `python -m scripts.run_agent_eval report`.")
    else:
        if res["manifest"]:
            st.json(res["manifest"], expanded=False)
        for split in res["metrics"]["summary"]:
            st.subheader(split)
            st.dataframe(metrics_rows(res["metrics"], split), hide_index=True)
            st.dataframe(paired_rows(res["metrics"], split), hide_index=True)
        st.caption("Small query counts: differences are indicative unless the interval excludes 0.")

with tab_live:
    st.caption("Calls a running service (uvicorn src.agent.api:create_default_app --factory). Spends LLM budget; off by default.")
    base = st.text_input("Service URL", "http://127.0.0.1:8000")
    query = st.text_input("Request")
    if st.button("Search", disabled=not query):
        import requests

        try:
            body = requests.post(f"{base}/search", json={"query": query}, timeout=120).json()
        except Exception as e:
            st.error(f"service unreachable: {e}")
        else:
            st.write(f"status: **{body.get('status')}**")
            for reason in body.get("reasons", []):
                st.warning(reason)
            for j in body.get("kept", []):
                st.markdown(f"**{j['rank']}.** {j['title']} — {j.get('company') or ''}")
            lines = evidence_lines(body.get("excluded", []))
            if lines:
                with st.expander(f"Excluded with evidence ({len(lines)})"):
                    for line in lines:
                        st.write(line)
