"""
扩展训练集：从外部 HuggingFace 数据集（yiqing111/Engineering_Jobs_Insight_Dataset，
11185 条）扩到 ~800 条干净样本，与原 120 条 v1 合并写回 data/labeled_jobs.json。

流程：
  1. 读 data/external/engineering_jobs.csv
  2. **黑名单过滤** — 剔除非软件类岗位（PM, DBA, Embedded, Network Eng, 售前等）
  3. **白名单关键词匹配** — title 命中关键词的高置信度样本直接打类别
  4. **每类截断到 PER_CATEGORY_QUOTA**（默认 100），不足的从"模糊样本"补
  5. **模糊样本** = 标题没匹配到任何白名单的（如纯 "Software Engineer"）→ 调 GPT-4o-mini 标
  6. 合并 v1 (120 条) + v2 新增 (~700) → 写回 data/labeled_jobs.json

外部样本的 job_id 前缀 = "ext_"，与 hn_/gh_ 区分。
外部样本无 tags 字段（CSV 里没），prepare_text 会跳过 tags，仅用 title + description。

用法：
    python -m src.classification.expand_training_set                # 默认每类 100
    python -m src.classification.expand_training_set --per-cat 120
    python -m src.classification.expand_training_set --dry-run      # 不调 LLM
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
# 关键词规则（白名单 / 黑名单）
# ---------------------------------------------------------------------------

# 白名单：title 含这些词 → 高置信度直接打类别
# 顺序敏感：fullstack 优先于 backend/frontend（避免 "full stack" 落到 backend）
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
        r"\bsystems engineer\b",  # 注意：systems engineer 在多数招聘里指 SRE/infra
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

# 黑名单：title 命中任一 → 整条丢弃（非我们 7 类范畴）
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
    r"\binternship\b", r"\bintern\b",  # 实习岗信息密度低，丢弃
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
    """按白名单匹配 title。返回类别名或 None（None 表示模糊样本）"""
    if not title:
        return None
    for cat, patterns in WHITELIST_COMPILED:
        for p in patterns:
            if p.search(title):
                return cat
    return None


# ---------------------------------------------------------------------------
# 数据清洗
# ---------------------------------------------------------------------------

def clean_text(s: str) -> str:
    """处理 CSV 里的乱码（"��" 是 UTF-8 BOM 残留）+ 去多余空白"""
    if not s:
        return ""
    s = s.replace("�", "'")  # mojibake → 普通撇号
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def load_external(path: Path) -> list[dict]:
    """读外部 CSV，过滤掉 description 太短或为空的行。"""
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
    返回 (labeled_by_keyword, ambiguous, blacklisted)
      labeled_by_keyword: 命中白名单 → 直接打 category
      ambiguous: title 没命中白名单也没黑名单 → 后面 LLM 处理
      blacklisted: 命中黑名单 → 丢弃
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
    """每类随机保留 quota 条；返回 (kept, per_category_kept_count)"""
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
    对模糊样本调 GPT-4o-mini，优先填补少数类。

    deficit_per_cat: {category: 还差多少条}
    max_calls: 最多调多少次 LLM
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
            break  # 所有类都满了

        # 构造 prompt
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
            print(f"  ! LLM 失败: {e}", file=sys.stderr)
            cat = None
            time.sleep(1.0)

        calls += 1

        if not cat:
            continue
        # 只保留还缺额的类
        if deficit.get(cat, 0) <= 0:
            continue

        results.append({**row, "category": cat, "label_source": "llm-gpt-4o-mini-supplement"})
        deficit[cat] = deficit.get(cat, 0) - 1

        if calls % 20 == 0:
            print(f"  LLM 已调 {calls} 次，已采纳 {len(results)} 条，缺额 {deficit}")

    print(f"  LLM 总共调用 {calls} 次，采纳 {len(results)} 条")
    return results


def to_labeled_record(row: dict, ext_idx_to_jid: dict[int, str]) -> dict:
    """转成 labeled_jobs.json 需要的格式（含 job_id 前缀 ext_）"""
    jid = ext_idx_to_jid[row["ext_idx"]]
    return {
        "job_id": jid,
        "title": row["title"],
        "company": row.get("company", ""),
        "tags": [],  # 外部数据集没有 tags
        "description": row["description"],
        "category": row["category"],
        "label_source": row.get("label_source", "keyword-rule"),
    }


def main(per_category_quota: int = 100, dry_run: bool = False, max_llm: int = 400) -> int:
    print(f"读取外部数据集 {EXTERNAL_CSV} ...")
    rows = load_external(EXTERNAL_CSV)
    print(f"有效行数：{len(rows)}（已剔除 desc<80 字符的）")

    # 给每行分配 ext_idx → ext_xxxxx 形式的 job_id
    ext_idx_to_jid = {row["ext_idx"]: f"ext_{row['ext_idx']:05d}" for row in rows}

    labeled_kw, ambiguous, blacklisted = assign_keyword_labels(rows)
    print(f"\n分配结果：")
    print(f"  关键词命中：{len(labeled_kw)}")
    print(f"  模糊样本（待 LLM）：{len(ambiguous)}")
    print(f"  黑名单丢弃：{len(blacklisted)}")

    # 关键词命中的初始分布
    kw_counts: dict[str, int] = {c: 0 for c in CATEGORIES}
    for j in labeled_kw:
        kw_counts[j["category"]] += 1
    print(f"\n关键词命中各类分布：")
    for c in CATEGORIES:
        print(f"  {c:12s} {kw_counts[c]:4d}")

    # 每类截断到 quota
    kw_kept, kept_counts = truncate_per_category(labeled_kw, per_category_quota)
    print(f"\n每类截断到 {per_category_quota} 后：")
    for c in CATEGORIES:
        print(f"  {c:12s} {kept_counts[c]:4d}")

    # 计算缺额（哪些类不够 quota，需要 LLM 从模糊样本里补）
    deficit = {c: max(0, per_category_quota - kept_counts[c]) for c in CATEGORIES}
    total_deficit = sum(deficit.values())
    print(f"\n总缺额：{total_deficit}")

    if dry_run:
        print("\n[dry-run] 不调 LLM，直接落盘 keyword-only 部分")
        llm_results = []
    elif total_deficit == 0:
        print("\n所有类均已满，无需 LLM 补")
        llm_results = []
    else:
        print(f"\n调 GPT-4o-mini 补 {total_deficit} 条（最多 {max_llm} 次调用）...")
        llm_results = supplement_with_llm(ambiguous, deficit, max_calls=max_llm)

    # 合并新数据
    new_records = (
        [to_labeled_record(r, ext_idx_to_jid) for r in kw_kept]
        + [to_labeled_record(r, ext_idx_to_jid) for r in llm_results]
    )

    # 加载 v1 备份（120 条）
    with V1_BACKUP.open("r", encoding="utf-8") as f:
        v1 = json.load(f)
    print(f"\nv1 备份：{len(v1)} 条")
    print(f"v2 新增：{len(new_records)} 条")

    # 合并
    merged = v1 + new_records
    print(f"合并总计：{len(merged)} 条")

    # 各类总分布
    final_counts: dict[str, int] = {c: 0 for c in CATEGORIES}
    for j in merged:
        final_counts[j["category"]] = final_counts.get(j["category"], 0) + 1
    print(f"\n合并后各类总分布：")
    for c in CATEGORIES:
        print(f"  {c:12s} {final_counts[c]:4d}")

    # 写回（dry-run 不写）
    if dry_run:
        print(f"\n[dry-run] 跳过写盘 {LABELED_PATH}")
    else:
        with LABELED_PATH.open("w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"\n已写入 {LABELED_PATH}（{len(merged)} 条）")

    # 中间产物：模糊样本和黑名单也写一份，方便调试
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
    ap.add_argument("--per-cat", type=int, default=100, help="每类目标样本数（默认 100）")
    ap.add_argument("--dry-run", action="store_true", help="不调 LLM 仅看分布")
    ap.add_argument("--max-llm", type=int, default=400, help="LLM 最多调用次数")
    args = ap.parse_args()
    sys.exit(main(per_category_quota=args.per_cat, dry_run=args.dry_run, max_llm=args.max_llm))
