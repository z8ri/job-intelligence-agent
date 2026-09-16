"""
Expand the training set: grow from the external HuggingFace dataset
(yiqing111/Engineering_Jobs_Insight_Dataset, 11185 rows) to ~800 clean samples,
merge with the original 120-sample v1 set, and write back to data/labeled_jobs.json.

Pipeline:
  1. Read data/external/engineering_jobs.csv
  2. **Blacklist filter** — drop non-software roles (PM, DBA, embedded, network eng, presales, etc.)
  3. **Whitelist keyword match** — high-confidence samples whose title hits a keyword are labeled directly
  4. **Truncate each category to PER_CATEGORY_QUOTA** (default 100); shortfalls are filled from "ambiguous samples"
  5. **Ambiguous samples** = titles that match no whitelist rule (e.g. plain "Software Engineer") -> labeled by GPT-4o-mini
  6. Merge v1 (120) + v2 additions (~700) -> write back to data/labeled_jobs.json

External samples use the job_id prefix "ext_" to distinguish them from hn_/gh_.
External samples have no tags field (not in the CSV); prepare_text skips tags and uses title + description only.

Usage:
    python -m src.classification.expand_training_set                # default 100 per category
    python -m src.classification.expand_training_set --per-cat 120
    python -m src.classification.expand_training_set --dry-run      # no LLM calls
"""

import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EXTERNAL_CSV = ROOT / "data" / "external" / "engineering_jobs.csv"
V1_BACKUP = ROOT / "data" / "labeled_jobs_v1_backup.json"
LABELED_PATH = ROOT / "data" / "labeled_jobs.json"
INTERMEDIATE_DIR = ROOT / "data" / "external"

CATEGORIES = ["backend", "frontend", "data", "devops", "fullstack", "mobile", "management"]

# ---------------------------------------------------------------------------
# Keyword rules (whitelist / blacklist)
# ---------------------------------------------------------------------------

# Whitelist: a title containing these terms gets the category directly (high confidence).
# Order matters: fullstack takes priority over backend/frontend (so "full stack" does not land in backend).
WHITELIST_RULES = [
    ("fullstack", [
        r"\bfull[\s-]?stack\b",
    ]),
    ("mobile", [
        r"\bios\b", r"\bandroid\b", r"\bmobile (?:engineer|developer|software)\b",
        r"\breact native\b", r"\bswift developer\b", r"\bkotlin developer\b",
        r"\bflutter\b",
    ]),
    ("management", [
        r"\bengineering manager\b", r"\bdirector of engineering\b",
        r"\bvp (?:of )?engineering\b", r"\bhead of engineering\b",
        r"\bcto\b", r"\bchief technology officer\b",
        r"\bsenior engineering manager\b", r"\bstaff engineering manager\b",
    ]),
    ("data", [
        r"\bdata scientist\b", r"\bdata engineer\b", r"\bml engineer\b",
        r"\bmachine learning engineer\b", r"\bai engineer\b",
        r"\bnlp engineer\b", r"\banalytics engineer\b",
        r"\bdata analyst\b", r"\bdata science\b",
        r"\bcomputer vision\b", r"\bml researcher\b",
        r"\bartificial intelligence engineer\b",
    ]),
    ("devops", [
        r"\bdevops\b", r"\bsre\b", r"\bsite reliability\b",
        r"\bplatform engineer\b", r"\binfrastructure engineer\b",
        r"\bcloud engineer\b", r"\bcloud devops\b",
        r"\bsystems engineer\b",  # note: in most postings "systems engineer" means SRE/infra
    ]),
    ("frontend", [
        r"\bfront[\s-]?end (?:engineer|developer|software)\b",
        r"\breact developer\b", r"\bui engineer\b", r"\bui developer\b",
        r"\bfrontend\b", r"\bweb developer\b",
        r"\bjavascript developer\b", r"\btypescript developer\b",
    ]),
    ("backend", [
        r"\bback[\s-]?end (?:engineer|developer|software)\b",
        r"\bbackend\b", r"\bserver engineer\b", r"\bapi engineer\b",
        r"\bdistributed systems engineer\b",
        r"\bjava developer\b", r"\bpython developer\b",
        r"\bgo developer\b", r"\bgolang developer\b",
        r"\bnode\.?js developer\b", r"\bruby developer\b",
        r"\b\.net developer\b",
    ]),
]

# Blacklist: a title matching any of these is dropped entirely (outside our 7 categories)
BLACKLIST_PATTERNS = [
    r"\bproduct manager\b", r"\bproduct owner\b", r"\bscrum master\b",
    r"\bbusiness analyst\b", r"\bsystem(?:s)? analyst\b",
    r"\bsales engineer\b", r"\bpresales\b", r"\bpre-sales\b",
    r"\bsolutions architect\b", r"\bsolutions engineer\b",
    r"\bsolutions consultant\b",
    r"\bnetwork engineer\b", r"\bnetwork administrator\b",
    r"\bdatabase administrator\b", r"\b\bdba\b",
    r"\bembedded\b", r"\bfirmware\b", r"\bhardware engineer\b",
    r"\bphysical security\b", r"\bsecurity guard\b",
    r"\bqa engineer\b", r"\bquality assurance\b", r"\btest engineer\b",
    r"\bautomation tester\b",
    r"\bux designer\b", r"\bui designer\b", r"\bvisual designer\b",
    r"\bgraphic designer\b", r"\bproduct designer\b",
    r"\btechnical writer\b", r"\bdocumentation\b",
    r"\bsupport engineer\b", r"\btechnical support\b",
    r"\bcustomer success\b",
    r"\bproject manager\b", r"\bprogram manager\b",
    r"\binternship\b", r"\bintern\b",  # internship postings carry little signal; drop them
    r"\bmechanical engineer\b", r"\bcivil engineer\b",
    r"\bchemical engineer\b", r"\belectrical engineer\b",
    r"\bnuclear\b",
    r"\baccount manager\b", r"\baccount executive\b",
    r"\bvp (?:of )?(?:sales|marketing|product|operations|finance|hr|people)\b",
    r"\bdirector of (?:sales|marketing|product|operations|finance|hr|people)\b",
    r"\b(?:hiring|recruitment|talent) manager\b",
    r"\b(?:legal|finance|hr|marketing|sales|operations) (?:manager|director|lead)\b",
]

WHITELIST_COMPILED = [
    (cat, [re.compile(p, re.IGNORECASE) for p in patterns])
    for cat, patterns in WHITELIST_RULES
]
BLACKLIST_COMPILED = [re.compile(p, re.IGNORECASE) for p in BLACKLIST_PATTERNS]


def is_blacklisted(title: str) -> bool:
    if not title:
        return True
    return any(p.search(title) for p in BLACKLIST_COMPILED)


def keyword_classify(title: str) -> str | None:
    """Match the title against the whitelist. Returns a category name or None (None = ambiguous sample)."""
    if not title:
        return None
    for cat, patterns in WHITELIST_COMPILED:
        for p in patterns:
            if p.search(title):
                return cat
    return None


# ---------------------------------------------------------------------------
# Data cleaning
# ---------------------------------------------------------------------------

def clean_text(s: str) -> str:
    """Fix mojibake in the CSV ("��" is a leftover UTF-8 BOM) and collapse extra whitespace."""
    if not s:
        return ""
    s = s.replace("�", "'")  # mojibake -> plain apostrophe
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_external(path: Path) -> list[dict]:
    """Read the external CSV, dropping rows whose description is empty or too short."""
    rows = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            title = clean_text(row.get("Job Title", ""))
            desc = clean_text(row.get("Description", ""))
            if not title or not desc or len(desc) < 80:
                continue
            rows.append({
                "ext_idx": i,
                "title": title,
                "company": clean_text(row.get("Company", "")),
                "description": desc,
            })
    return rows


def assign_keyword_labels(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Returns (labeled_by_keyword, ambiguous, blacklisted)
      labeled_by_keyword: whitelist hit -> category assigned directly
      ambiguous: title hits neither whitelist nor blacklist -> handled by the LLM later
      blacklisted: blacklist hit -> dropped
    """
    labeled, ambiguous, blacklisted = [], [], []
    for row in rows:
        if is_blacklisted(row["title"]):
            blacklisted.append(row)
            continue
        cat = keyword_classify(row["title"])
        if cat:
            labeled.append({**row, "category": cat, "label_source": "keyword-rule"})
        else:
            ambiguous.append(row)
    return labeled, ambiguous, blacklisted


def truncate_per_category(labeled: list[dict], quota: int, seed: int = 42) -> tuple[list[dict], dict[str, int]]:
    """Randomly keep up to `quota` samples per category; returns (kept, per_category_kept_count)."""
    random.seed(seed)
    by_cat: dict[str, list[dict]] = {c: [] for c in CATEGORIES}
    for j in labeled:
        by_cat[j["category"]].append(j)

    kept = []
    counts = {}
    for cat, items in by_cat.items():
        random.shuffle(items)
        chosen = items[:quota]
        kept.extend(chosen)
        counts[cat] = len(chosen)
    return kept, counts


def supplement_with_llm(
    ambiguous: list[dict],
    deficit_per_cat: dict[str, int],
    max_calls: int,
) -> list[dict]:
    """
    Label ambiguous samples with GPT-4o-mini, prioritizing under-filled categories.

    deficit_per_cat: {category: how many samples are still missing}
    max_calls: upper bound on LLM calls
    """
    from src.llm import MODEL, get_client
    from src.classification.auto_label import (
        SYSTEM_PROMPT, _FEW_SHOT_MESSAGES,
    )

    if max_calls <= 0:
        return []

    client = get_client()
    random.seed(42)
    random.shuffle(ambiguous)

    results: list[dict] = []
    deficit = dict(deficit_per_cat)
    calls = 0

    for row in ambiguous:
        if calls >= max_calls:
            break
        if all(v <= 0 for v in deficit.values()):
            break  # every category is full

        # build the prompt
        title = row["title"]
        desc = row["description"][:600]
        user_text = f"Title: {title}\nTags: (none)\nDescription: {desc}"
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *_FEW_SHOT_MESSAGES,
            {"role": "user", "content": user_text},
        ]
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=10,
            )
            raw = resp.choices[0].message.content.strip().lower().strip(".,!?\"'` \n")
            cat = None
            if raw in CATEGORIES:
                cat = raw
            else:
                for c in CATEGORIES:
                    if c in raw:
                        cat = c
                        break
        except Exception as e:
            print(f"  ! LLM call failed: {e}", file=sys.stderr)
            cat = None
            time.sleep(1.0)

        calls += 1

        if not cat:
            continue
        # only keep categories that still have a shortfall
        if deficit.get(cat, 0) <= 0:
            continue

        results.append({**row, "category": cat, "label_source": "llm-gpt-4o-mini-supplement"})
        deficit[cat] = deficit.get(cat, 0) - 1

        if calls % 20 == 0:
            print(f"  LLM calls: {calls}, accepted: {len(results)}, remaining deficit: {deficit}")

    print(f"  LLM calls total: {calls}, accepted {len(results)} samples")
    return results


def to_labeled_record(row: dict, ext_idx_to_jid: dict[int, str]) -> dict:
    """Convert to the labeled_jobs.json record format (job_id gets the ext_ prefix)."""
    jid = ext_idx_to_jid[row["ext_idx"]]
    return {
        "job_id": jid,
        "title": row["title"],
        "company": row.get("company", ""),
        "tags": [],  # the external dataset has no tags
        "description": row["description"],
        "category": row["category"],
        "label_source": row.get("label_source", "keyword-rule"),
    }


def main(per_category_quota: int = 100, dry_run: bool = False, max_llm: int = 400) -> int:
    print(f"Reading external dataset {EXTERNAL_CSV} ...")
    rows = load_external(EXTERNAL_CSV)
    print(f"Valid rows: {len(rows)} (rows with desc < 80 chars dropped)")

    # assign each row a job_id of the form ext_xxxxx from its ext_idx
    ext_idx_to_jid = {row["ext_idx"]: f"ext_{row['ext_idx']:05d}" for row in rows}

    labeled_kw, ambiguous, blacklisted = assign_keyword_labels(rows)
    print(f"\nAssignment:")
    print(f"  keyword hits: {len(labeled_kw)}")
    print(f"  ambiguous (pending LLM): {len(ambiguous)}")
    print(f"  blacklisted (dropped): {len(blacklisted)}")

    # initial distribution of keyword hits
    kw_counts: dict[str, int] = {c: 0 for c in CATEGORIES}
    for j in labeled_kw:
        kw_counts[j["category"]] += 1
    print(f"\nKeyword-hit distribution by category:")
    for c in CATEGORIES:
        print(f"  {c:12s} {kw_counts[c]:4d}")

    # truncate each category to the quota
    kw_kept, kept_counts = truncate_per_category(labeled_kw, per_category_quota)
    print(f"\nAfter truncating each category to {per_category_quota}:")
    for c in CATEGORIES:
        print(f"  {c:12s} {kept_counts[c]:4d}")

    # compute the deficit (categories below quota that the LLM must fill from ambiguous samples)
    deficit = {c: max(0, per_category_quota - kept_counts[c]) for c in CATEGORIES}
    total_deficit = sum(deficit.values())
    print(f"\nTotal deficit: {total_deficit}")

    if dry_run:
        print("\n[dry-run] skipping LLM; writing the keyword-only portion")
        llm_results = []
    elif total_deficit == 0:
        print("\nAll categories are full; no LLM supplement needed")
        llm_results = []
    else:
        print(f"\nCalling GPT-4o-mini to fill {total_deficit} samples (at most {max_llm} calls)...")
        llm_results = supplement_with_llm(ambiguous, deficit, max_calls=max_llm)

    # merge the new data
    new_records = (
        [to_labeled_record(r, ext_idx_to_jid) for r in kw_kept]
        + [to_labeled_record(r, ext_idx_to_jid) for r in llm_results]
    )

    # load the v1 backup (120 samples)
    with V1_BACKUP.open("r", encoding="utf-8") as f:
        v1 = json.load(f)
    print(f"\nv1 backup: {len(v1)} samples")
    print(f"v2 additions: {len(new_records)} samples")

    # merge
    merged = v1 + new_records
    print(f"Merged total: {len(merged)} samples")

    # overall distribution by category
    final_counts: dict[str, int] = {c: 0 for c in CATEGORIES}
    for j in merged:
        final_counts[j["category"]] = final_counts.get(j["category"], 0) + 1
    print(f"\nMerged distribution by category:")
    for c in CATEGORIES:
        print(f"  {c:12s} {final_counts[c]:4d}")

    # write back (skipped on dry-run)
    if dry_run:
        print(f"\n[dry-run] skipping write to {LABELED_PATH}")
    else:
        with LABELED_PATH.open("w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {LABELED_PATH} ({len(merged)} samples)")

    # intermediate artifacts: also dump ambiguous and blacklisted samples for debugging
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
    with (INTERMEDIATE_DIR / "ambiguous_titles_sample.json").open("w", encoding="utf-8") as f:
        json.dump([{"ext_idx": r["ext_idx"], "title": r["title"]}
                   for r in ambiguous[:200]], f, ensure_ascii=False, indent=2)
    with (INTERMEDIATE_DIR / "blacklisted_titles_sample.json").open("w", encoding="utf-8") as f:
        json.dump([{"ext_idx": r["ext_idx"], "title": r["title"]}
                   for r in blacklisted[:200]], f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-cat", type=int, default=100, help="target samples per category (default 100)")
    ap.add_argument("--dry-run", action="store_true", help="skip LLM calls, only show the distribution")
    ap.add_argument("--max-llm", type=int, default=400, help="maximum number of LLM calls")
    args = ap.parse_args()
    sys.exit(main(per_category_quota=args.per_cat, dry_run=args.dry_run, max_llm=args.max_llm))
