"""Pure helpers behind the comparison page (no Streamlit imports, so they are testable)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from src.agent.evaluation import SYSTEM_ORDER, is_valid
from src.agent.models import ConditionSet

SYSTEM_LABELS = {
    "retrieval_raw": "Retrieval (raw request)",
    "retrieval": "Retrieval (role/skill text)",
    "rerank": "+ Cross-Encoder rerank",
    "verify_fixed": "+ verify top-k only",
    "verify_ondemand": "+ on-demand verification (backfill)",
    "verify_full": "+ verify everything",
}


def load_results(out_dir: str | Path) -> dict:
    out = Path(out_dir)
    read = lambda name: json.loads((out / name).read_text()) if (out / name).exists() else None
    return {"runs": read("runs.json") or {}, "qrels": read("qrels.json") or {}, "metrics": read("metrics.json"),
            "manifest": read("manifest.json")}


def verdict_of(label: dict | None, hard_ids: list[str]) -> str:
    """valid | wrong | unlabeled — 'wrong' means labelled but not a confirmed match."""
    if label is None:
        return "unlabeled"
    return "valid" if is_valid(label, hard_ids) else "wrong"


def system_columns(run: dict, labels: dict[str, dict], lookup: Callable[[str], dict]) -> list[dict]:
    """One entry per system, in pipeline order, each with ranked rows and excluded-with-reason."""
    hard_ids = [c.id for c in ConditionSet.model_validate(run["conditions"]).hard()]
    cols = []
    for name in SYSTEM_ORDER:
        s = run["systems"].get(name)
        if s is None:
            continue
        rows = []
        for rank, key in enumerate(s["shown"], 1):
            info = lookup(key)
            label = labels.get(key)
            rows.append({"rank": rank, "job_key": key, "title": info.get("title", key), "company": info.get("company", ""),
                         "verdict": verdict_of(label, hard_ids), "label_reason": (label or {}).get("reason", ""),
                         "label_source": (label or {}).get("source", "")})
        cols.append({
            "system": name, "title": SYSTEM_LABELS[name], "rows": rows,
            "excluded": [{"job_key": k, "title": lookup(k).get("title", k)} for k in s.get("excluded", [])],
            "status": s.get("status"), "reasons": s.get("reasons", []), "usage": s.get("usage"),
        })
    return cols


def metrics_rows(metrics: dict, split: str) -> list[dict]:
    block = metrics.get("summary", {}).get(split)
    if not block:
        return []
    k = metrics["k"]
    return [
        {"system": SYSTEM_LABELS[n], f"valid@{k}": r["valid"], f"wrong@{k}": r["wrong_accept"], f"unlabeled@{k}": r["unlabeled"],
         f"nDCG@{k}": r["ndcg"], "LLM calls/q": r["llm_calls"], "est $/q": r["est_cost_usd"], "queries": r["queries"]}
        for n, r in block["systems"].items()
    ]


def paired_rows(metrics: dict, split: str) -> list[dict]:
    block = metrics.get("summary", {}).get(split)
    if not block:
        return []
    return [
        {"comparison": f"{p['a']} - {p['b']}", "what": p["what"], "n": p["queries"], "mean diff": p["valid_diff_mean"],
         "95% CI": f"[{p['valid_diff_ci95'][0]:+.2f}, {p['valid_diff_ci95'][1]:+.2f}]",
         "win/loss/tie": f"{p['wins']}/{p['losses']}/{p['ties']}"}
        for p in block["paired"]
    ]


def evidence_lines(excluded: list[dict]) -> list[str]:
    """Readable lines for the 'excluded (with evidence)' list of a live service response."""
    lines = []
    for job in excluded:
        for ev in job.get("evidence", []):
            lines.append(f"{job['title']} ({job.get('company') or '-'}): \"{ev['quote']}\" — {ev.get('reason') or 'conflicts with a hard condition'}")
    return lines
