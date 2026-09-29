import json
import re

import pytest

from src.agent.evaluation import (
    BudgetExceeded, EvalQuery, FrozenLLM, ReplayMiss, annotate_job, check_split_isolation, compute_metrics,
    export_review, import_review, ndcg_at_k, paired_bootstrap, render_report, run_eval, score_system,
)
from src.agent.models import ConditionSet
from src.agent.retrieval import JobIndex
from src.agent.snapshots import Snapshot
from tests.test_agent_verification import FakeLLM

Q_DEV = "LLM applications in New York"
Q_HOLD = "Rust drivers in Berlin"


class Live:
    """Counts calls; behaves like the three live model endpoints for the fake corpus."""

    def __init__(self):
        self.calls = 0
        self.judge = FakeLLM()

    def parse(self, system, user):
        self.calls += 1
        if "LLM applications" in user:
            conds = [
                {"field": "role_focus", "strength": "hard", "quote": "LLM applications", "value": {"kind": "text", "text": "LLM applications"}},
                {"field": "work_region", "strength": "hard", "quote": "New York", "value": {"kind": "regions", "regions": ["New York"]}},
            ]
        else:
            conds = [
                {"field": "role_focus", "strength": "hard", "quote": "Rust drivers", "value": {"kind": "text", "text": "Rust drivers"}},
                {"field": "work_region", "strength": "hard", "quote": "Berlin", "value": {"kind": "regions", "regions": ["Berlin"]}},
            ]
        return json.dumps({"conditions": conds, "clarifications": []})

    def judge_call(self, system, user):
        self.calls += 1
        return self.judge(system, user)

    def annotate(self, system, user):
        self.calls += 1
        text = re.search(r"<job>(.*)</job>", user, re.S).group(1)
        ids = re.findall(r'"condition_id": "([^"]+)"', user)
        hard = {}
        for cid in ids:
            if cid.startswith("work_region"):
                hard[cid] = "satisfied" if "New York" in text else "violated" if "London" in text else "unstated"
            else:
                hard[cid] = "satisfied" if "LLM" in text else "violated"
        return json.dumps({"relevance": 2 if "LLM" in text else 0, "hard": hard, "reason": "r"})


def corpus():
    mk = lambda i, title, body: Snapshot.create(source="greenhouse", source_job_id=str(i), title=title, raw_content=body,
                                                 fetched_at="2026-03-01T00:00:00+00:00")
    return [
        mk(0, "Engineer 0", "Located in New York. Build LLM applications."),
        mk(1, "Engineer 1", "Located in London. Build LLM applications."),
        mk(2, "Engineer 2", "Located in New York. Build LLM applications."),
        mk(3, "Engineer 3", "Located somewhere. Build LLM applications."),
        mk(4, "Cook", "Cook meals daily."),
        mk(5, "Driver", "Drive trucks."),
        mk(6, "Rust dev", "Located in Berlin. Write Rust drivers."),
    ]


QUERIES = [EvalQuery("d1", "dev", "llm", Q_DEV), EvalQuery("h1", "holdout", "rust", Q_HOLD)]


def eval_run(tmp_path, live, *, mode="record", max_usd=None, name="out", log_name="log.db"):
    llm = FrozenLLM(tmp_path / log_name, mode=mode, max_usd=max_usd)
    out = run_eval(
        QUERIES, JobIndex(corpus()), None, llm, tmp_path / name,
        parse_live=live.parse if live else None, judge_live=live.judge_call if live else None,
        annotate_live=live.annotate if live else None, k=3, max_candidates=5, pool_depth=4,
    )
    return llm, out


# ---- FrozenLLM -----------------------------------------------------------------


def test_replay_mode_never_calls_live_and_raises_on_miss():
    llm = FrozenLLM(mode="replay")
    with pytest.raises(ReplayMiss):
        llm.view("x", lambda s, u: "never")("s", "u")


def test_record_then_replay_gives_same_response_and_counts_usage(tmp_path):
    calls = []
    rec = FrozenLLM(tmp_path / "l.db", mode="record")
    v = rec.view("judge", lambda s, u: calls.append(1) or "answer")
    assert v("sys", "user") == "answer" and v("sys", "user") == "answer"
    assert len(calls) == 1 and v.calls == 2 and v.usage()["prompt_tokens"] > 0
    rec.close()
    rep = FrozenLLM(tmp_path / "l.db", mode="replay")
    assert rep.view("j")("sys", "user") == "answer"


def test_budget_guard_blocks_live_calls_and_is_persistent(tmp_path):
    big = "x" * 300_000  # ~100k prompt tokens ~ $0.015 with gpt-4o-mini pricing
    llm = FrozenLLM(tmp_path / "l.db", mode="record", max_usd=0.02)
    live_calls = []
    v = llm.view("j", lambda s, u: live_calls.append(1) or "ok")
    v("s", big)
    with pytest.raises(BudgetExceeded):
        v("s", big + "y")
    assert len(live_calls) == 1
    llm.close()
    again = FrozenLLM(tmp_path / "l.db", mode="record", max_usd=0.02)  # spend survives restarts
    assert again.live_spent_usd() > 0.01
    with pytest.raises(BudgetExceeded):
        again.view("j", lambda s, u: "ok")("s", big + "z")
    assert again.view("j")("s", big) == "ok"  # a recorded prompt is free


# ---- query isolation --------------------------------------------------------------


def test_split_isolation_flags_shared_group_and_paraphrase():
    qs = [
        EvalQuery("a", "dev", "g1", "Machine learning engineer roles in New York"),
        EvalQuery("b", "holdout", "g1", "Rust systems programmer"),
        EvalQuery("c", "holdout", "g2", "Machine learning engineer role in New York City"),
        EvalQuery("d", "holdout", "g3", "Technical writer, remote"),
    ]
    problems = " | ".join(check_split_isolation(qs))
    assert "group 'g1'" in problems and "a and c look like paraphrases" in problems
    assert "a and d" not in problems
    assert check_split_isolation([qs[0], qs[3]]) == []


# ---- annotation and metrics -----------------------------------------------------------


def test_annotate_job_parses_validates_and_defaults_unstated():
    cs = ConditionSet.model_validate(json.loads(json.dumps({"raw_query": Q_DEV, "conditions": [
        {"field": "work_region", "strength": "hard", "quote": "New York", "value": {"kind": "regions", "regions": ["New York"]}}]})))
    snap = corpus()[0]
    good = annotate_job(lambda s, u: json.dumps({"relevance": 1, "hard": {}, "reason": "r"}), snap, cs)
    assert good["relevance"] == 1 and list(good["hard"].values()) == ["unstated"]
    replies = iter(["not json", json.dumps({"relevance": 2, "hard": {}})])
    assert annotate_job(lambda s, u: next(replies), snap, cs)["relevance"] == 2  # one retry after invalid output
    bad = iter(["not json", json.dumps({"relevance": 7, "hard": {}})])
    assert annotate_job(lambda s, u: next(bad), snap, cs) is None  # out-of-range relevance is not accepted
    assert annotate_job(lambda s, u: "nope", snap, cs) is None


def lab(rel, **hard):
    return {"relevance": rel, "hard": hard, "source": "silver"}


def test_valid_requires_all_hard_conditions_confirmed():
    labels = {"a": lab(2, h="satisfied"), "b": lab(2, h="unstated"), "c": lab(2, h="violated"), "d": lab(0, h="satisfied")}
    s = score_system(["a", "b", "c", "d", "zzz"], labels, ["h"], 5)
    assert s["valid"] == 1 and s["wrong_accept"] == 2 and s["unlabeled"] == 1  # c violated, d irrelevant


def test_ndcg_uses_shared_ideal_and_zero_when_nothing_valid():
    labels = {"a": lab(2, h="satisfied"), "b": lab(1, h="satisfied"), "c": lab(2, h="unstated")}
    assert ndcg_at_k(["a", "b"], labels, ["h"], 2) == pytest.approx(1.0)
    assert ndcg_at_k(["b", "a"], labels, ["h"], 2) < 1.0
    assert ndcg_at_k(["c"], {"c": lab(2, h="unstated")}, ["h"], 3) == 0.0


def test_paired_bootstrap_is_deterministic_and_brackets_the_mean():
    d = [1, 0, 2, 1, 0, 1]
    lo, hi = paired_bootstrap(d)
    assert (lo, hi) == paired_bootstrap(d) and lo <= sum(d) / len(d) <= hi
    assert paired_bootstrap([]) == (0.0, 0.0)


# ---- end to end -----------------------------------------------------------------------


def test_run_eval_produces_all_systems_and_labels(tmp_path):
    live = Live()
    llm, out = eval_run(tmp_path, live)
    assert out["stopped"] is None
    run = out["runs"]["d1"]
    assert set(run["systems"]) == {"retrieval_raw", "retrieval", "verify_fixed", "verify_ondemand", "verify_planned", "verify_full", "verify_full_confirmed_first"}
    u = {n: run["systems"][n]["usage"]["llm_calls"] for n in ("verify_fixed", "verify_ondemand", "verify_full")}
    assert u["verify_fixed"] <= u["verify_ondemand"] <= u["verify_full"] and u["verify_fixed"] == 3
    assert set(out["qrels"]["d1"]) == set(run["pool"])
    fixed = run["systems"]["verify_fixed"]["shown"]
    assert "greenhouse:1" not in run["systems"]["verify_ondemand"]["shown"]  # London job excluded with evidence
    assert len(run["systems"]["verify_ondemand"]["shown"]) >= len(fixed)  # backfill never shows fewer
    m = compute_metrics(out["runs"], out["qrels"], k=3)
    assert set(m["summary"]) == {"dev", "holdout"}
    assert m["summary"]["dev"]["systems"]["verify_ondemand"]["valid"] >= m["summary"]["dev"]["systems"]["retrieval"]["valid"]
    assert "verify_ondemand" in render_report(m, {"snapshots": 7})


def test_replay_reproduces_a_recorded_run_exactly_without_network(tmp_path):
    live = Live()
    eval_run(tmp_path, live, name="a")
    calls = live.calls
    eval_run(tmp_path, None, mode="replay", name="b")
    assert live.calls == calls
    assert (tmp_path / "a" / "runs.json").read_text() == (tmp_path / "b" / "runs.json").read_text()
    assert (tmp_path / "a" / "qrels.json").read_text() == (tmp_path / "b" / "qrels.json").read_text()


def test_run_is_idempotent_and_resumes_after_budget_stop(tmp_path):
    live = Live()
    llm = FrozenLLM(tmp_path / "log.db", mode="record", max_usd=0.0)  # nothing may be spent
    out = run_eval(QUERIES, JobIndex(corpus()), None, llm, tmp_path / "o", parse_live=live.parse,
                   judge_live=live.judge_call, annotate_live=live.annotate, k=3, max_candidates=5)
    assert out["stopped"].startswith("BudgetExceeded") and out["runs"] == {} and live.calls == 0
    llm2, out2 = eval_run(tmp_path, live, name="o")
    assert out2["stopped"] is None and set(out2["runs"]) == {"d1", "h1"}
    n = live.calls
    eval_run(tmp_path, live, name="o")
    assert live.calls == n  # nothing recomputed


def test_review_export_is_blind_and_import_overrides_silver(tmp_path):
    live = Live()
    _, out = eval_run(tmp_path, live)
    idx = JobIndex(corpus())
    path = tmp_path / "review.csv"
    n = export_review(out["runs"], idx, path, split="dev")
    text = path.read_text()
    assert n == len(out["runs"]["d1"]["pool"]) and "verify_" not in text and "retrieval" not in text.split("\n", 1)[1]
    hard_id = next(iter(out["qrels"]["d1"].values()))["hard"]
    cid = next(iter(hard_id))
    rows = path.read_text().splitlines()
    import csv as _csv
    with open(path, newline="") as f:
        data = list(_csv.DictReader(f))
    data[0]["relevance"] = "0"
    data[0]["hard_status"] = f"{cid}=violated"
    data[1]["relevance"] = "9"  # invalid
    with open(path, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=data[0].keys())
        w.writeheader()
        w.writerows(data)
    merged, problems = import_review(path, out["qrels"], out["runs"])
    assert merged == 1 and len(problems) == 1 and "line 3" in problems[0]
    assert out["qrels"]["d1"][data[0]["job_key"]]["source"] == "human"
    assert out["qrels"]["d1"][data[0]["job_key"]]["hard"][cid] == "violated"
