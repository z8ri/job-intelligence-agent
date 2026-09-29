import json

from src.agent.compare_view import evidence_lines, load_results, metrics_rows, paired_rows, system_columns, verdict_of
from src.agent.evaluation import compute_metrics
from src.agent.models import Condition, ConditionSet, RegionsValue

REGION = Condition(field="work_region", strength="hard", quote="NY", value=RegionsValue(regions=["New York"]))
CS = ConditionSet(raw_query="jobs in NY", conditions=[REGION])


def make_run():
    return {
        "split": "dev", "conditions": CS.model_dump(mode="json"),
        "systems": {
            "retrieval": {"shown": ["a", "b", "c"], "usage": None},
            "verify_ondemand": {"shown": ["a", "d"], "excluded": ["b"], "status": "complete", "reasons": [],
                                "usage": {"llm_calls": 3, "prompt_tokens": 30, "completion_tokens": 9, "est_cost_usd": 0.001}},
        },
    }


def label(ok, source="silver"):
    return {"relevance": 2, "hard": {REGION.id: "satisfied" if ok else "violated"}, "reason": "r", "source": source}


LABELS = {"a": label(True), "b": label(False), "d": label(True, "human")}
LOOKUP = lambda k: {"title": f"T-{k}", "company": "Co"}


def test_verdict_of():
    hard = [REGION.id]
    assert verdict_of(None, hard) == "unlabeled"
    assert verdict_of(LABELS["a"], hard) == "valid" and verdict_of(LABELS["b"], hard) == "wrong"


def test_system_columns_order_labels_and_excluded():
    cols = system_columns(make_run(), LABELS, LOOKUP)
    assert [c["system"] for c in cols] == ["retrieval", "verify_ondemand"]
    assert [(r["job_key"], r["verdict"]) for r in cols[0]["rows"]] == [("a", "valid"), ("b", "wrong"), ("c", "unlabeled")]
    assert cols[1]["excluded"] == [{"job_key": "b", "title": "T-b"}]
    assert cols[1]["rows"][1]["label_source"] == "human"


def test_metric_tables_from_real_compute_metrics():
    runs = {"q1": make_run()}
    m = compute_metrics(runs, {"q1": LABELS}, k=3)
    rows = metrics_rows(m, "dev")
    assert {r["system"] for r in rows} == {"Retrieval (role/skill text)", "+ on-demand verification (backfill)"}
    assert metrics_rows(m, "holdout") == [] and paired_rows(m, "holdout") == []
    assert all(k in rows[0] for k in ("valid@3", "nDCG@3", "LLM calls/q"))


def test_load_results_tolerates_missing_files(tmp_path):
    assert load_results(tmp_path) == {"runs": {}, "qrels": {}, "metrics": None, "manifest": None}
    (tmp_path / "runs.json").write_text(json.dumps({"q": 1}))
    assert load_results(tmp_path)["runs"] == {"q": 1}


def test_evidence_lines():
    ex = [{"title": "Eng", "company": "", "evidence": [{"quote": "Located in London.", "reason": "region"}]}]
    assert evidence_lines(ex) == ['Eng (-): "Located in London." — region']
    assert evidence_lines([{"title": "x"}]) == []
