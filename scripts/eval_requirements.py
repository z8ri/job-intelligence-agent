"""Requirement-understanding accuracy: parse each annotated request, compare with the gold conditions.

  python -m scripts.eval_requirements parse     # live LLM (one call per request, ~$0.01), writes parsed.json
  python -m scripts.eval_requirements score     # offline, writes metrics.json and report.md

Views: strict (field + strength + value), strength ignored, field ignored (text conditions matched by the
span of the user's words they quote). A request is exactly correct when every required gold condition is
matched, no extra condition was produced, no forbidden hard condition appears, and a clarification was
raised when one is expected.
"""

import argparse
import json
from pathlib import Path

from src.agent.conditions import ConditionParseError, parse_conditions

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "agent_eval" / "requirements_annotation.json"
OUT = ROOT / "data" / "eval_results_agent_run2" / "requirements"
ALIAS = {"us": "united states", "usa": "united states", "u.s.": "united states", "the us": "united states", "america": "united states",
         "uk": "united kingdom", "eu": "european union", "washington, dc": "washington dc", "washington d.c.": "washington dc",
         "bay area": "san francisco bay area", "nyc": "new york", "new york city": "new york", "la": "los angeles"}


def _norm_region(r: str) -> str:
    r = r.strip().lower()
    return ALIAS.get(r, r)


def _span(query: str, quote: str):
    i = query.casefold().find(quote.casefold())
    return (i, i + len(quote)) if i >= 0 else None


def _overlap(q, a, b) -> bool:
    sa, sb = _span(q, a), _span(q, b)
    if not sa or not sb:
        return False
    inter = max(0, min(sa[1], sb[1]) - max(sa[0], sb[0]))
    return inter >= 0.5 * min(sa[1] - sa[0], sb[1] - sb[0])


def _value_ok(gold: dict, pred: dict) -> bool:
    f, gv, pv = gold["field"], gold["value"], pred["value"]
    if f in ("role_focus", "role_avoid", "skill", "other"):
        return True  # decided by the quoted span, checked by the caller
    if f == "work_region":
        return {_norm_region(x) for x in gv} == {_norm_region(x) for x in pv["regions"]}
    if f == "remote_mode":
        return set(gv) == set(pv["modes"])
    if f == "employment_type":
        return set(gv) == set(pv["types"])
    if f == "seniority":
        if "max_years_required" in gold and pv.get("max_years_required") != gold["max_years_required"]:
            return False
        return pv.get("level") == str(gv).split()[0]
    if f == "salary":
        # compared as a yearly amount so "$30k per month" and "$360k per year" are the same requirement;
        # the basis (base/total) is reported separately because inventing one is a different kind of error
        def yearly(v):
            if v.get("min_amount") is None:
                return None
            return v["min_amount"] * {"year": 1, "month": 12, "hour": 2080}[v.get("period", "year")]
        a, b = yearly(gv), yearly(pv)
        amount_ok = (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= 0.01 * a)
        return amount_ok and str(gv.get("currency", "USD")).upper() == str(pv.get("currency", "USD")).upper()
    return False


def matches(gold: dict, pred: dict, query: str, mode: str) -> bool:
    text_kinds = ("role_focus", "role_avoid", "skill", "other")
    if mode == "nofield" and gold["field"] in text_kinds and pred["field"] in text_kinds:
        return _overlap(query, gold["quote"], pred["quote"])
    if gold["field"] != pred["field"]:
        return False
    if mode == "strict" and gold["strength"] != "either" and gold["strength"] != pred["strength"]:
        return False
    if gold["field"] in text_kinds:
        return _overlap(query, gold["quote"], pred["quote"])
    return _value_ok(gold, pred)


def score_request(req: dict, parsed: dict, mode: str) -> dict:
    q = req["query"]
    preds = list(parsed.get("conditions", []))
    used: set[int] = set()
    tp = miss = 0
    missing = []
    for g in req["conditions"]:
        if g.get("unscored"):
            # the schema cannot represent it: a prediction on the same field and span is set aside, neither hit nor extra
            same = next((i for i, p in enumerate(preds) if i not in used and p["field"] == g["field"] and _overlap(q, g["quote"], p["quote"])), None)
            if same is not None:
                used.add(same)
            continue
        hit = next((i for i, p in enumerate(preds) if i not in used and matches(g, p, q, mode)), None)
        if g.get("optional"):
            # acceptable-only statement: may be absent; if given it must be soft with exactly this value
            if hit is not None and preds[hit]["strength"] == "soft":
                used.add(hit)
            continue
        if hit is None:
            miss += 1
            missing.append(g["quote"])
        else:
            used.add(hit)
            tp += 1
    extras = [{"field": p["field"], "strength": p["strength"], "quote": p["quote"]} for i, p in enumerate(preds) if i not in used]
    forbidden = [p["field"] for p in preds if p["strength"] == "hard" and p["field"] in req.get("must_not_be_hard", [])]
    clar_ok = (not req.get("expects_clarification")) or bool(parsed.get("clarifications"))
    exact = miss == 0 and not extras and not forbidden and clar_ok and not parsed.get("failed")
    return {"tp": tp, "fn": miss, "fp": len(extras), "missing": missing, "extras": extras, "forbidden_hard": forbidden,
            "clarification_ok": clar_ok, "exact": exact}


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0}


def summarize(reqs: list[dict], rows: dict[str, dict]) -> dict:
    tp = sum(rows[r["id"]]["tp"] for r in reqs)
    fp = sum(rows[r["id"]]["fp"] for r in reqs)
    fn = sum(rows[r["id"]]["fn"] for r in reqs)
    ex = sum(rows[r["id"]]["exact"] for r in reqs)
    return {"requests": len(reqs), "tp": tp, "fp": fp, "fn": fn, **prf(tp, fp, fn), "exact_correct": ex, "exact_rate": round(ex / len(reqs), 3) if reqs else 0.0}


def parse_all() -> None:
    gold = json.loads(GOLD.read_text())
    out = {}
    for r in gold["requests"]:
        try:
            cs = parse_conditions(r["query"], run_id="requirements_eval")
            out[r["id"]] = {"conditions": [c.model_dump(mode="json") for c in cs.conditions],
                            "clarifications": [c.model_dump(mode="json") for c in cs.clarifications]}
        except ConditionParseError as e:
            out[r["id"]] = {"conditions": [], "clarifications": [], "failed": str(e)}
        print(r["id"], len(out[r["id"]]["conditions"]), "conditions", len(out[r["id"]]["clarifications"]), "clarifications")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "parsed.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


def score_all() -> None:
    gold = json.loads(GOLD.read_text())["requests"]
    parsed = json.loads((OUT / "parsed.json").read_text())
    metrics, per_request = {}, {}
    clean = [r for r in gold if "schema_gap" not in r]
    for mode in ("strict", "nostrength", "nofield"):
        rows = {r["id"]: score_request(r, parsed[r["id"]], "strict" if mode == "strict" else mode) for r in gold}
        metrics[mode] = {"all": summarize(gold, rows), "without_schema_gap_requests": summarize(clean, rows)}
        per_request[mode] = rows
    metrics["clarification"] = {
        "expected": sum(1 for r in gold if r.get("expects_clarification")),
        "raised_when_expected": sum(1 for r in gold if r.get("expects_clarification") and parsed[r["id"]]["clarifications"]),
        "raised_when_not_expected": sum(1 for r in gold if not r.get("expects_clarification") and parsed[r["id"]]["clarifications"]),
        "not_expected_total": sum(1 for r in gold if not r.get("expects_clarification")),
    }
    basis_total = basis_invented = 0
    for r in gold:
        for g in r["conditions"]:
            if g["field"] == "salary" and (g["value"] or {}).get("basis") == "unspecified":
                hit = next((p for p in parsed[r["id"]]["conditions"] if matches(g, p, r["query"], "strict")), None)
                if hit:
                    basis_total += 1
                    basis_invented += hit["value"].get("basis") != "unspecified"
    metrics["salary_basis_invented"] = {"matched_salary_conditions_without_stated_basis": basis_total, "parser_added_a_basis": basis_invented}
    metrics["forbidden_hard_violations"] = sum(1 for r in gold if per_request["strict"][r["id"]]["forbidden_hard"])
    (OUT / "metrics.json").write_text(json.dumps({"metrics": metrics, "per_request": per_request["strict"]}, ensure_ascii=False, indent=1))
    lines = ["# 需求理解准确率（30 条新需求，用户确认标注，gpt-4o-mini 解析）", ""]
    for mode, label in (("strict", "严格：字段+硬软+值"), ("nostrength", "忽略硬软"), ("nofield", "忽略字段（文本条件按引文位置匹配）")):
        m = metrics[mode]
        lines.append(f"- {label}：条件 P/R/F1 = {m['all']['precision']}/{m['all']['recall']}/{m['all']['f1']}；整条完全正确 {m['all']['exact_correct']}/{m['all']['requests']}；"
                     f"排除 {len(gold)-len(clean)} 条模式受限请求后 F1 {m['without_schema_gap_requests']['f1']}，完全正确 {m['without_schema_gap_requests']['exact_correct']}/{m['without_schema_gap_requests']['requests']}")
    lines += ["", f"- 澄清：应澄清的 {metrics['clarification']['expected']} 条中触发 {metrics['clarification']['raised_when_expected']}；不该澄清的 {metrics['clarification']['not_expected_total']} 条中多问 {metrics['clarification']['raised_when_not_expected']}",
              f"- 出现了不该有的硬条件的请求数：{metrics['forbidden_hard_violations']}", "", "## 逐条（严格）", ""]
    for r in gold:
        s = per_request["strict"][r["id"]]
        lines.append(f"- {r['id']} {'OK' if s['exact'] else 'X'} 漏：{s['missing']} 多：{[(e['field'], e['strength'], e['quote']) for e in s['extras']]}"
                     f"{' 禁止的硬条件：' + str(s['forbidden_hard']) if s['forbidden_hard'] else ''}{'' if s['clarification_ok'] else ' 应澄清未澄清'}")
    (OUT / "report.md").write_text("\n".join(lines))
    print("\n".join(lines[:9]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["parse", "score"])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    OUT = a.out
    parse_all() if a.command == "parse" else score_all()
