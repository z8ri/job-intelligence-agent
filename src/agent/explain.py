"""Explain why the list changed after the user revised their conditions.

Compares two stored result envelopes (previous version, new version) and, for every job whose
place changed, says what moved it:

  * status changes (entered / left the list, excluded / restored) name the condition and the
    verified quote that decided it;
  * a rank move inside the list is decomposed exactly: a job's soft score is
    sum(weight * score) / sum(weight), so each condition contributes weight*score/total and the
    per-condition differences add up to the score difference. Weight or strength changes of one
    condition therefore show up on every job, including through the change of the total.
"""

from __future__ import annotations

MIN_CONTRIBUTION = 0.005


def _by_key(items: list[dict]) -> dict[str, dict]:
    return {j["job_key"]: j for j in items}


def _contributions(job: dict) -> dict[str, float]:
    rows = job.get("soft_breakdown") or []
    total = sum(r["weight"] for r in rows)
    if total <= 0:
        return {}
    return {r["condition_id"]: r["weight"] * r["score"] / total for r in rows}


def _label(cond: dict | None, condition_id: str) -> str:
    return f'"{cond["quote"]}" ({cond["field"]})' if cond else condition_id


def _condition_changes(old: dict[str, dict], new: dict[str, dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for cid in old.keys() - new.keys():
        out[cid] = f"removed condition {_label(old[cid], cid)}"
    for cid in new.keys() - old.keys():
        out[cid] = f"added {new[cid]['strength']} condition {_label(new[cid], cid)}"
    for cid in old.keys() & new.keys():
        parts = []
        if old[cid]["strength"] != new[cid]["strength"]:
            parts.append(f"strength {old[cid]['strength']} -> {new[cid]['strength']}")
        if old[cid].get("weight") != new[cid].get("weight") and new[cid]["strength"] == "soft":
            parts.append(f"weight {old[cid].get('weight')} -> {new[cid].get('weight')}")
        if parts:
            out[cid] = f"{_label(new[cid], cid)}: " + ", ".join(parts)
    return out


def _evidence_text(job: dict) -> str:
    ev = job.get("evidence") or []
    return "; ".join(f'"{e["quote"]}"' for e in ev if e.get("quote"))


def explain_rank_changes(previous: dict, current: dict) -> dict:
    """`previous` / `current`: result envelopes (kept, excluded, unverified, conditions)."""
    old_conds = {c["id"]: c for c in (previous.get("conditions") or {}).get("conditions", [])}
    new_conds = {c["id"]: c for c in (current.get("conditions") or {}).get("conditions", [])}
    changed = _condition_changes(old_conds, new_conds)

    old_kept, new_kept = _by_key(previous["kept"]), _by_key(current["kept"])
    old_excl, new_excl = _by_key(previous["excluded"]), _by_key(current["excluded"])
    old_unv = _by_key(previous["unverified"])

    def status(job_key: str, kept: dict, excl: dict, unv: dict | None = None) -> str:
        if job_key in kept:
            return "kept"
        if job_key in excl:
            return "excluded"
        return "unverified" if unv is not None and job_key in unv else "absent"

    jobs = []
    for key in list(dict.fromkeys([*old_kept, *new_kept, *old_excl, *new_excl])):
        before, after = status(key, old_kept, old_excl, old_unv), status(key, new_kept, new_excl)
        if before == after == "excluded":
            continue
        job = new_kept.get(key) or new_excl.get(key) or old_kept.get(key) or old_excl.get(key)
        entry = {"job_key": key, "title": job.get("title"), "old_status": before, "new_status": after,
                 "old_rank": old_kept[key]["rank"] if key in old_kept else None,
                 "new_rank": new_kept[key]["rank"] if key in new_kept else None, "reasons": []}
        reasons = entry["reasons"]

        if before == "kept" and after == "kept":
            entry["change"] = ("up" if entry["new_rank"] < entry["old_rank"] else
                               "down" if entry["new_rank"] > entry["old_rank"] else "same")
            entry["old_soft_score"], entry["new_soft_score"] = old_kept[key].get("soft_score"), new_kept[key].get("soft_score")
            old_c, new_c = _contributions(old_kept[key]), _contributions(new_kept[key])
            drivers = sorted(((cid, new_c.get(cid, 0.0) - old_c.get(cid, 0.0)) for cid in old_c.keys() | new_c.keys()),
                             key=lambda kv: -abs(kv[1]))
            for cid, delta in drivers:
                if abs(delta) < MIN_CONTRIBUTION:
                    continue
                cause = changed.get(cid)
                reasons.append({"condition_id": cid, "score_delta": round(delta, 4),
                                "text": f"{_label(new_conds.get(cid) or old_conds.get(cid), cid)} "
                                        f"{'raised' if delta > 0 else 'lowered'} the soft score by {abs(delta):.3f}"
                                        + (f" ({cause})" if cause else "")})
            if entry["change"] == "same" and not reasons:
                continue
            if not reasons:
                reasons.append({"condition_id": None, "score_delta": 0.0,
                                "text": "same soft score; order among equals follows the retrieval ranking or other jobs moved"})
        elif after == "kept":
            entry["change"] = "entered"
            if before == "excluded":
                cids = [e["condition_id"] for e in old_excl[key].get("evidence", [])]
                why = "; ".join(changed.get(c, "") for c in cids if changed.get(c)) or "conditions changed"
                reasons.append({"condition_id": cids[0] if cids else None, "score_delta": None,
                                "text": f"no longer excluded ({why}); earlier evidence: {_evidence_text(old_excl[key])}"})
            else:
                reasons.append({"condition_id": None, "score_delta": None,
                                "text": "not in the previous list; verified this time because exclusions freed room"})
        elif after == "excluded":
            entry["change"] = "excluded"
            cids = [e["condition_id"] for e in new_excl[key].get("evidence", [])]
            why = "; ".join(changed.get(c, "") for c in cids if changed.get(c)) or "conditions changed"
            reasons.append({"condition_id": cids[0] if cids else None, "score_delta": None,
                            "text": f"now excluded ({why}); evidence: {_evidence_text(new_excl[key])}"})
        else:
            entry["change"] = "left"
            reasons.append({"condition_id": None, "score_delta": None,
                            "text": "pushed out of the list by jobs that now rank higher or by the verification budget"})
        jobs.append(entry)

    counts = {k: sum(1 for j in jobs if j["change"] == k) for k in ("up", "down", "entered", "left", "excluded")}
    return {
        "from_version": previous.get("condition_version"), "to_version": current.get("condition_version"),
        "condition_changes": [{"condition_id": cid, "text": t} for cid, t in changed.items()],
        "summary": counts, "jobs": jobs,
    }
