# System Design — Job Intelligence Agent

A multi-source job-search system: it ingests data from English-language job sources (a HackerNews "Who is Hiring" crawler + the public Greenhouse / Lever JSON APIs), stores all fields in MySQL, and lets the user ask natural-language questions. A **unified multi-field weighted scoring engine** then computes a composite relevance score for every job, an optional LLM reranker refines the textual-relevance signal for hard queries, a rule-based verifier filters out results that don't actually satisfy the user's constraints, and the pipeline returns ranked results — asking a clarifying question instead of guessing when a query is too underspecified to retrieve anything meaningful.

**Core selling point (original design)**: a domain-specific multi-field weighted scoring suite —
- Structured fields (salary, location, remote preference, etc.) → each gets its own **decay / proximity scoring function** (not hard filtering); e.g. with target salary $100k, $99k still scores high while $101k and $200k differ.
- Free-text job description → a **constrained Planner** picks the retrieval strategy per query (TF-IDF / BM25 / Dense embeddings / RRF fusion of BM25+Dense, see §3.4.1–3.4.1c) to provide the textual signal.
- All field scores are weight-combined into one composite relevance score: `S(job) = Σ wᵢ · scoreᵢ(job)`.
- Query-adaptive dynamic weight normalization: only the fields actually mentioned by the user are activated; the remaining weight is automatically renormalized.
- Hard filtering is reserved for absolute constraints only (e.g., a degree-requirement mismatch). The vast majority of matching is done through weighted ranking.

**LLM role declaration (updated for vNext)**: the LLM is used in preprocessing (query understanding / preference extraction / retrieval-strategy classification), **optionally inside ranking** (§3.4.1d LLM reranker — rescoring the Top-N candidates' textual relevance for queries the Planner classifies as needing it), and in post-processing (answer generation). This is a deliberate change from the original design: the LLM is still never the sole judge of a result — it only replaces one signal (`description`/text relevance) inside the same multi-field weighted-scoring formula, gated behind a rule-based Planner decision, and can be turned off via `config["use_reranker"]=False`. Everything else (salary/location/remote/tags/category scoring, weight normalization, hard filtering) remains traditional IR / rule-based, unaffected by the LLM.

---

## 1. System architecture

```
 ┌──────────────────────────────────────────────────────────┐
 │                  Data Ingestion Layer                     │
 │                                                          │
 │   HackerNews "Who is Hiring"     Greenhouse/Lever API     │
 │          │                            │                  │
 │          └──────────┬─────────────────┘                  │
 │                     ▼                                    │
 │              ┌─────────────┐                             │
 │              │  Web Spider  │  robots.txt compliant       │
 │              │  BFS crawl   │  ≥1.5s/page, 5s/thread       │
 │              └──────┬──────┘                             │
 │                     │ raw HTML                           │
 │                     ▼                                    │
 │              ┌─────────────┐                             │
 │              │ Info Extract │  BeautifulSoup + regex      │
 │              │  HTML Parse  │  structured + free text     │
 │              └──────┬──────┘                             │
 └─────────────────────┼────────────────────────────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
     ┌─────────────┐       ┌─────────────┐
     │   MySQL      │       │  IR index    │
     │ All fields    │       │ scikit-learn │
     │ + bulk read  │       │ TF-IDF vec.  │
     │              │       │              │
     └──────┬──────┘       └──────┬──────┘
            │   linked by job_id  │
 ───────────┼─────────────────────┼──────────────
            │                     │
            │   user NL question  │
            ▼                     │
     ┌────────────────────────────────┐
     │  LLM Query Understanding (pre)  │
     │  Extract preferences + weights  │
     │  + retrieval_mode classification│
     │  (occasional hard filter: deg.) │
     │  + merge with cross-turn memory │
     │    (session_id, MySQL)          │
     └─────────────┬──────────────────┘
       is_job_query=false │ needs_clarification │ else
              ▼            ▼                     ▼
          [reject]     [clarify]         ┌────────────────────────────────┐
           → END         → END           │  Query Expansion                │
                                          │  synonym / hypernym expansion   │
                                          │  "ML" → "machine learning, AI" │
                                          └─────────────┬──────────────────┘
                                                        │
                                                        ▼
                                          ┌────────────────────────────────┐
                                          │  Candidate loading              │
                                          │  MySQL bulk read                │
                                          │  (WHERE only for hard filters)  │
                                          └─────────────┬──────────────────┘
                                                        │
                        ┌───────────────────────────────┘
                        ▼
     ┌─────────────────────────────────────────────────┐
     │  Unified multi-field scoring                     │
     │                                                  │
     │  constrained Planner (retrieval_mode → strategy):│
     │    exact       → BM25                            │
     │    semantic    → RRF(BM25, Dense embeddings)      │
     │    exploratory → RRF(BM25, Dense) + LLM reranker  │
     │  (explicit config overrides the Planner's choice) │
     │                                                  │
     │  s1 = w1 · text_score(desc)   ← Planner/reranker  │
     │  s2 = w2 · salary_score(sal)                      │
     │  s3 = w3 · location_score(loc)                    │
     │  s4 = w4 · remote_score(rmt)                       │
     │  s5 = w5 · tag_overlap(tags)                       │
     │  S  = s1 + s2 + s3 + s4 + s5                       │
     └─────────────┬─────────────────────────────────────┘
                   │
                   ▼
     ┌────────────────────────────────┐
     │  Collection Fusion              │
     │  dual-source ranking (default   │
     │  final_score) + dedupe          │
     │  + min-max norm (optional)      │
     │  → top-K                         │
     └─────────────┬──────────────────┘
                   │
                   ▼
     ┌────────────────────────────────┐
     │  Verifier                       │
     │  valid / rejected / unknown     │
     │  (part-time·intern·no-salary…)  │
     └─────────────┬──────────────────┘
       0 valid & retry_count<1 │        │ else
              ▼                │        ▼
    (loop back to unified_scoring,     ┌────────────────────────────────┐
     forced to RRF+reranker, ≤1 retry) │  Job classification             │
                                       │  vector centroid → category     │
                                       │  backend / frontend / data /..  │
                                       └─────────────┬──────────────────┘
                                                     │
                                                     ▼
                                       ┌────────────────────────────────┐
                                       │  LLM NL answer generation (post)│
                                       │  (LangGraph orchestration)       │
                                       └────────────────────────────────┘
```

---

## 2. Data sources and crawling strategy

### Primary targets

| Source | Characteristics | Collection method |
|--------|-----------------|-------------------|
| **HackerNews "Who is Hiring"** | One thread per month, hundreds of postings; pure text mixing company / role / location / stack / description together | Crawl the HN thread page HTML (no API), parse the comment list, extract one job per top-level comment |
| **Greenhouse / Lever public JSON APIs** | Mainstream tech companies (Airbnb, Figma, Discord, …) post via ATS platforms such as Greenhouse, Lever, Ashby, etc., exposing unauthenticated JSON endpoints | Construct the company slug and call endpoints like `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` to read structured fields directly |

**Why these two sources**:
- Compliant: HN is crawl-friendly with mild anti-scraping; Greenhouse / Lever offer public APIs that need no anti-scraping work.
- Complementary formats: HN is free text (requires IE), while Greenhouse / Lever return semi-structured JSON (clean fields).
- Results from the two sources need to be normalized and merged → multi-source information fusion (Collection Fusion).

### Fallback plan

If crawling is blocked, fall back to a public Kaggle job dataset (e.g. "Data Scientist Jobs") as the data source, while still demonstrating crawler capability on simpler targets.

### Compliance practice

- Check and obey each site's robots.txt before crawling.
- Use a descriptive User-Agent: `JobIR-Bot/1.0 (research crawler; contact: <email>)`.
- Pause ≥1.5 seconds between successive page fetches and 5 seconds between thread crawls; no concurrent fetches.
- Download text pages only — no images / media.
- Limit the data scope (only HN "Who is Hiring" threads; only the public job endpoints on Greenhouse / Lever).

---

## 3. Core modules

### 3.1 Web Spider

**Responsibility**: given seed URLs, crawl target pages BFS and emit the raw HTML.

**Key components**:
- **URL Frontier**: a Python `deque` for BFS.
- **robots.txt parser**: `urllib.robotparser.RobotFileParser`, consulted before each fetch.
- **HTTP downloader**: `requests.get()`, with timeout (10s), retry (max 2), and User-Agent.
- **URL deduplication**: a `set()` of visited URLs to avoid re-fetching.
- **Rate limit**: `time.sleep(1.5)` between successive page fetches and `time.sleep(5)` between thread crawls.
- **Scope control**: only follow links inside the target domain.

**Output**: list of `{url: str, html: str, timestamp: str}`, persisted to JSON.

### 3.2 Information extraction (HTML → structured + free-text)

**Responsibility**: parse raw HTML into structured fields plus a free-text description.

**HN "Who is Hiring" extraction**:
- Each top-level comment = one job posting.
- Regex extraction:
  - Company: usually the first few tokens (uppercase / bold).
  - Location: matches "Remote" / "San Francisco, CA" / "Berlin, Germany", etc.
  - Salary: matches "$120k-$180k" / "$150,000", etc.
  - Remote tag: matches "Remote" / "Onsite" / "Hybrid".
  - Tech stack: matches a curated technology keyword list (Python, Go, React, AWS, …).
- Whatever text remains becomes the (free-text) job description.

**Greenhouse / Lever JSON extraction**:
- Consume the JSON response directly: `title`, `location.name`, `company`, `content` (HTML description).
- Strip tags from the description with BeautifulSoup; salary and remote (when not exposed by the endpoint) reuse the same regex extractors as HN.

**Output** per job:
```python
{
    "job_id": "hn_12345",
    "source": "hackernews",          # source identifier
    "company": "Stripe",
    "title": "Backend Engineer",
    "location": "San Francisco, CA",
    "remote": "remote",              # remote / onsite / hybrid
    "salary_min": 150000,            # may be None
    "salary_max": 200000,
    "tags": ["Python", "AWS", "PostgreSQL"],
    "description": "We are looking for..."  # free text
}
```

### 3.3 Storage layer

**MySQL schema**:

```sql
CREATE TABLE jobs (
    job_id      VARCHAR(64) PRIMARY KEY,
    source      VARCHAR(32) NOT NULL,      -- hackernews / greenhouse / lever
    company     VARCHAR(255),
    title       VARCHAR(255),
    location    VARCHAR(255),
    remote      ENUM('remote','onsite','hybrid','unknown'),
    salary_min  INT,
    salary_max  INT,
    degree_req  ENUM('none','bachelor','master','phd','unknown') DEFAULT 'unknown',
    category    ENUM('backend','frontend','data','devops','fullstack','mobile','management','other') DEFAULT 'other',
    description TEXT,
    publish_time DATETIME,                    -- posting time (HN comment time / Greenhouse postedAt)
    crawled_at  DATETIME
);

CREATE TABLE job_tags (
    job_id  VARCHAR(64),
    tag     VARCHAR(64),
    PRIMARY KEY (job_id, tag),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
);
```

**Role of MySQL**:
- **Primary use**: persistent storage + bulk retrieval. At query time the candidate set is loaded into Python memory via `SELECT * FROM jobs` and scored there.
- **Hard filtering** (used sparingly): `WHERE` clauses are reserved for absolute constraints, e.g. `WHERE degree_req IN ('none','bachelor')` to exclude jobs requiring a master's degree the user does not have.
- **No longer used for**: relevance filtering — we never use `WHERE` to drop jobs by salary range, location, etc.; those are scoring-function inputs.

**IR index file**:
- A scikit-learn TF-IDF matrix + vocabulary, serialized as a pickle.
- Linked to MySQL by `job_id`: the scoring engine can look up structured fields and textual relevance scores using the same key.

### 3.4 Retrieval and scoring engine

#### 3.4.1 Text retrieval (powered by scikit-learn)

This module uses a mature IR library and is **not** claimed as an original contribution.

**Implementation**:
- `sklearn.feature_extraction.text.TfidfVectorizer` builds a TF-IDF matrix over the corpus of job descriptions.
- Preprocessing (tokenization, stopword removal, stemming) is pipelined through `nltk` and supplied to `TfidfVectorizer` via a custom tokenizer.
- At query time, the user's keywords are run through `TfidfVectorizer.transform()` and compared with the document matrix using `sklearn.metrics.pairwise.cosine_similarity`.

**Output**: per job, a textual relevance score in `[0, 1]` — `score_description(query, job_id)` — consumed as one signal in the multi-field scoring engine.

**BM25 baseline** (added 2026-04-25, `src/ir/bm25.py`):

`JobBM25System` (built on `rank_bm25.BM25Okapi`) is added as a comparison baseline to TF-IDF. It shares `src/ir/preprocess.py` (tokenization + stopwords + Porter stem) with TF-IDF so both indexes ingest identically normalized input. BM25 raw scores have no theoretical upper bound; `get_similarities()` min-max normalizes to `[0, 1]` so that BM25 and TF-IDF cosine are on the same scale and can be fused.

`pipeline/graph.py::node_unified_scoring` switches between ranker modes via `config["ir_mode"]`: `tfidf` / `bm25` / `dense` / `hybrid` (50/50 raw-score average of TF-IDF+BM25) / `hybrid_rrf` (RRF fusion of BM25+Dense, see §3.4.1b–c). When `config` doesn't specify `ir_mode`, the constrained Planner (§3.4.1d) picks it from the query's classified `retrieval_mode`; `tfidf` remains the hard fallback default.

> **Note**: TF-IDF and BM25 are both standard IR techniques; this project consumes them through off-the-shelf libraries. The original contributions live in the multi-field scoring functions in the next subsection.

#### 3.4.1b Dense retrieval (`src/ir/dense.py`, added in vNext)

BM25/TF-IDF only match on literal term overlap — a query like "LLM Agent" won't retrieve a posting that says "build LLM-powered workflows with tool use and retrieval" because the two share no vocabulary. `JobDenseSystem` embeds every job's `title + description` with OpenAI `text-embedding-3-small` (batched, L2-normalized, cosine similarity via normalized dot product, then min-max scaled to `[0,1]` like the other text scorers). The index is trained once (`python -m src.ir.dense`) and persisted to `data/dense_model.pkl` as **plain data only** (job ids, embedding matrix, model name string — no custom class instances), specifically to avoid the `__main__`-class-path pickle trap already hit once with the TF-IDF model (see the `_TextPreprocessor` extraction in §3.4.1). `load_model()` also refuses to load an index built with a different `EMBEDDING_MODEL`, since embedding spaces from different models aren't comparable.

#### 3.4.1c Reciprocal Rank Fusion (`src/ir/rrf.py`, added in vNext)

BM25's raw score and Dense's cosine similarity live on incomparable scales, so a naive weighted average of the two would just be dominated by whichever happens to have larger magnitude for that query. RRF sidesteps this by fusing on **rank position** instead of raw score: `RRF(d) = Σᵢ 1/(k + rankᵢ(d))` with the standard `k=60` (Cormack et al., 2009). A document missing from one ranker's list simply contributes 0 from that source. Because RRF's own output magnitude is tiny (at most `2/(k+1)` when fusing two lists), it is re-min-max-normalized to `[0,1]` before being handed to the multi-field scoring engine — otherwise the `description` field (default weight 0.35, usually the largest) would be numerically swamped by the other fields regardless of actual textual relevance.

#### 3.4.1d LLM Reranker + constrained Planner (`src/scoring/reranker.py`, added in vNext)

BM25/TF-IDF/Dense all score "does this text look related", not "does this specific job actually satisfy what the user is asking for." `rerank()` sends the Top-`N` (`RERANK_TOP_N=50`) candidates' title + a 1200-character description snippet, together with the user's **original, unexpanded** query, to `gpt-4o-mini` (LLM+Schema style: structured `{job_id: score}` JSON output, not free-form text), and the returned scores **overwrite** the text-relevance component for just those N candidates — everything past N keeps its original coarse score. Any failure (network, malformed JSON, an id the LLM invented) degrades to `{}` and the pipeline silently keeps the coarse ranking; reranking is a refinement, never a blocking step.

Because this genuinely lets the LLM influence which jobs rank higher, it is gated behind a rule-based **constrained Planner**, not applied unconditionally: `query_understanding` classifies every query into one of three `retrieval_mode`s, and `_PLANNER_MODE_MAP` maps each to a retrieval/rerank combination —

| `retrieval_mode` | Meaning | `ir_mode` | `use_reranker` |
|---|---|---|---|
| `exact` | precise tech terms / exact titles — literal matching already works | `bm25` | `False` |
| `semantic` | intent is clear but wording may not literally overlap the job text | `hybrid_rrf` | `False` |
| `exploratory` | query is vague / underspecified — needs the broadest recall plus an extra relevance check | `hybrid_rrf` | `True` |

An explicit `config["ir_mode"]` / `config["use_reranker"]` always overrides the Planner's choice (used by the CLI's `--ir-mode`/`--rerank` flags and by `src/eval/*` ablation configs), so existing evaluation behavior is unaffected unless a caller opts in.

#### 3.4.2 Multi-field scoring functions (this project's core original design)

> **This is the core original contribution of the project.** Every scoring function below is custom-designed for the job-search setting and does not depend on any existing library or algorithm. Each design encodes domain-specific judgments (asymmetric decay, tiered proximity, classification-match matrices, …) rather than simple thresholds or boolean matches.

All scoring functions return values in `[0, 1]`.

**Salary scoring — asymmetric Gaussian decay + "highest paying" sentinel**:

```python
def score_salary(job, target_salary):
    """
    Normal mode: the further from the target salary, the lower the score; asymmetric
        (overshooting hurts less than undershooting); missing salary → neutral 0.5.
    Sentinel mode (target_salary >= 500000): when the user says "highest paying X",
        the LLM emits target=999999 sentinel; we switch to a linear ramp (capped at
        $500k → 1.0) and missing salary drops from 0.5 to 0.0 — to keep n/a jobs
        from floating to the top of a high-pay query.
    """
    if not target_salary: return 1.0

    # "highest paying" sentinel
    is_highest_paying = target_salary >= 500000

    if job.salary_min is None and job.salary_max is None:
        return 0.0 if is_highest_paying else 0.5

    # pick the point in the salary range closest to the target
    if job.salary_min and job.salary_max:
        effective = max(job.salary_min, min(target_salary, job.salary_max))
    elif job.salary_min:
        effective = job.salary_min
    else:
        effective = job.salary_max

    if is_highest_paying:
        # linear ramp: higher salary → higher score, capped at 500k
        return min(effective / 500000, 1.0)

    delta = effective - target_salary
    sigma = 50000 if delta >= 0 else 20000  # asymmetric
    return math.exp(-((delta / sigma) ** 2))
    # Normal mode (target=100k): 99k→0.94, 101k→1.00, 80k→0.37, 200k→0.08
    # Sentinel mode (target=999999): 200k→0.4, 400k→0.8, 500k+→1.0, n/a→0.0
```

**Why the sentinel threshold is 500000**: it sits well above ordinary query targets (typically 100k–200k), so it cannot be triggered accidentally; `tests/test_scoring.py` covers 8 normal-mode regression cases; the evaluation sets all use `target_salary` between 100k and 200k, so **the evaluation numbers are unaffected by the sentinel branch** — it only kicks in when a demo user explicitly asks for "highest paying".

**Location scoring — tiered proximity**:

```python
# Pre-built lookup tables: 54 major US tech metros + 307 city aliases. No external API.
METRO_AREAS = {
    "new york": {
        "cities": ["new york", "brooklyn", "manhattan", "queens",
                   "jersey city", "hoboken", "newark"],
        "state": "ny",
        "neighbors": ["nj", "ct", "pa"]
    },
    "san francisco": {
        "cities": ["san francisco", "oakland", "berkeley",
                   "palo alto", "san jose", "mountain view"],
        "state": "ca",
        "neighbors": ["nv", "or"]
    },
    # ... more metros
}

# 50 states full-name → state-code table (added to handle
# users typing "Texas" / "California" etc. meaning "any city in that state";
# deliberately does not include bare "new york" / "washington" to avoid colliding
# with NYC metro / DC metro city names).
US_STATES = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
    "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de",
    "florida": "fl", "georgia": "ga", "texas": "tx", "washington state": "wa",
    "new york state": "ny",
    # ... 50 states + DC
}

def score_location(job_location, preferred_location):
    """
    Tiered scoring (refined remote tiers + 50-state full-name fallback):
    exact match / same-metro hit / state full-name + same-state city  → 1.0
    > pure Remote 0.9 > US-remote / same-metro+remote 0.85
    > same-state city 0.5 > foreign remote 0.4 > unknown 0.3 > other 0.1
    """
    if not preferred_location: return 1.0
    if job_location is None or job_location == "Unknown": return 0.3

    job_loc, pref_loc = normalize(job_location), normalize(preferred_location)
    if job_loc == pref_loc:                            return 1.0

    is_remote = "remote" in job_loc
    geo_part = strip_remote_tokens(job_loc)            # strip 'remote' / ' or ' / ' - '

    # NEW: state-level preference ("Texas" / "California" / ...) handled separately
    if pref_loc in US_STATES:
        target_state = US_STATES[pref_loc]
        if is_in_state_city(target_state, job_loc, geo_part):
            return 1.0 if not is_remote else 0.85
        if is_in_neighbor_state_city(target_state, job_loc, geo_part):
            return 0.5
        if is_remote and is_us_marker(geo_part):       return 0.85
        if is_remote and not geo_part:                 return 0.85   # pure remote
        if is_remote and geo_part:                     return 0.4
        return 0.1

    # City-level preference (original logic)
    if is_remote and not geo_part:                     return 0.9   # pure remote
    if is_remote and any(x in geo_part for x in ['us','usa','united states']):
                                                       return 0.85  # US-remote

    if is_same_metro(job_loc, pref_loc, geo_part):     return 1.0 if not is_remote else 0.85
    if is_same_state(job_loc, pref_loc, geo_part):     return 0.5

    if is_remote and geo_part:                         return 0.4   # foreign remote (e.g. Brazil-Remote)
    return 0.1
```

**Key changes**:
- Same-metro match raised from 0.8 → 1.0 (equivalent to "exact match"; this assumes `metro_areas.json` already has aliases such as 'NYC' / 'SF').
- Remote is split into 4 tiers: pure Remote / US-remote / same-metro+remote / foreign-remote.
- Foreign-remote (e.g. 'Brazil - Remote') drops from 0.9 → 0.4 to stop these jobs from crowding out genuinely local roles in the top results.
- **50-state full-name fallback**: when the user types "jobs in Texas", the LLM emits `preferred_location="Texas"`; the original city-level branch fell through to the 0.1 fallback. The new branch recognizes the full state name and scores all in-state metro cities at 1.0, neighboring-state cities at 0.5. Multi-word cities ("new orleans" / "san francisco") get a substring fallback so split-token comparisons don't miss.

**Remote-preference scoring — categorical match matrix**:

```python
# rows = user preference, columns = job attribute
REMOTE_SCORE = {
    #                remote  hybrid  onsite  unknown
    "remote":      { "remote": 1.0, "hybrid": 0.4, "onsite": 0.1, "unknown": 0.3 },
    "hybrid":      { "remote": 0.6, "hybrid": 1.0, "onsite": 0.5, "unknown": 0.4 },
    "onsite":      { "remote": 0.2, "hybrid": 0.6, "onsite": 1.0, "unknown": 0.4 },
}

def score_remote(job_remote, preferred_remote):
    if preferred_remote is None:
        return 1.0  # user did not specify → treat all jobs equally
    return REMOTE_SCORE.get(preferred_remote, {}).get(job_remote, 0.3)
```

**Skill-tag scoring — modified Jaccard**:

```python
def score_tags(job_tags, desired_tags):
    """
    intersection / |user-desired tags|. The denominator is the user's set,
    because extra skills required by the job should not penalize the match.
    """
    if not desired_tags:
        return 1.0  # not specified → does not affect ranking
    if not job_tags:
        return 0.0
    job_set = set(t.lower() for t in job_tags)
    desired_set = set(t.lower() for t in desired_tags)
    return len(job_set & desired_set) / len(desired_set)
```

#### 3.4.3 Composite scoring and ranking (original design)

> The dynamic weight-normalization mechanism — assigning weights only to fields the query activated and renormalizing the rest — is independently designed for this project, not lifted from any existing framework.

```python
# default weights
DEFAULT_WEIGHTS = {
    "description": 0.35,  # textual relevance is usually the dominant signal
    "salary":      0.20,
    "location":    0.15,
    "remote":      0.10,
    "tags":        0.10,
    "category":    0.10,  # job-category match
}

def compute_final_score(job, preferences, weights):
    """
    Unified multi-field scoring. Only fields touched by the query are scored;
    others' weights are zeroed out and the remainder is renormalized.
    """
    scores = {}

    if preferences.description_keywords:
        scores["description"] = score_description(preferences.description_keywords, job.job_id)
    if preferences.target_salary:
        scores["salary"] = score_salary(job, preferences.target_salary)
    if preferences.preferred_location:
        scores["location"] = score_location(job.location, preferences.preferred_location)
    if preferences.remote_preference:
        scores["remote"] = score_remote(job.remote, preferences.remote_preference)
    if preferences.desired_tags:
        scores["tags"] = score_tags(job.tags, preferences.desired_tags)
    if preferences.preferred_category:
        scores["category"] = score_category(job.category, preferences.preferred_category)

    # renormalize weights only over the active fields
    active_weights = {k: weights[k] for k in scores}
    w_sum = sum(active_weights.values())
    if w_sum == 0:
        return 0.0
    return sum(scores[k] * active_weights[k] / w_sum for k in scores)
```

#### 3.4.4 Third-party libraries this module depends on

| Capability | Library | Role |
|------------|---------|------|
| TF-IDF vectorization + cosine similarity | `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`) | **Standard IR infrastructure**, not original |
| BM25 retrieval | `rank_bm25` (`BM25Okapi`) | **Standard IR infrastructure**, not original; used as a TF-IDF baseline |
| English tokenization | `nltk.word_tokenize` | Preprocessing helper |
| Stopwords | `nltk.corpus.stopwords` | Preprocessing helper |
| Stemming | `nltk.stem.PorterStemmer` | Preprocessing helper |
| Vector arithmetic | `numpy` | Compute helper |

> **Original vs library** dispatch: the TF-IDF retrieval pipeline is built entirely on scikit-learn — no original claim there. The original contributions are the multi-field scoring functions of §3.4.2 and the dynamic weight-normalization mechanism of §3.4.3.

#### 3.4.5 Original contributions vs library dependencies (summary)

| Component | Implementation | Originality |
|-----------|---------------|-------------|
| Text preprocessing (tokenize / stopwords / stem) | nltk | Standard library |
| TF-IDF vectorization + cosine similarity | scikit-learn | Standard library |
| Salary scoring (asymmetric Gaussian decay) | Custom design | **Original** |
| Location scoring (tiered proximity) | Custom design + hand-built lookup tables | **Original** |
| Remote-preference scoring (categorical match matrix) | Custom design | **Original** |
| Skill-tag scoring (modified Jaccard) | Custom design | **Original** |
| Composite scoring + dynamic weight normalization | Custom design | **Original** |
| Query Expansion (synonyms + hypernym/hyponym) | Hand-built domain synonym table + standard expansion logic | **Original** (the synonym table) |
| Job classification (vector centroid classifier) | Rocchio-style with scikit-learn | Standard method (training set labeling is original) |
| Collection Fusion (cross-source normalization) | Min-max normalization (standard method) | Standard method |
| Query understanding (LLM preference extraction + retrieval_mode classification) | LLM API calls | Preprocessing helper (the prompt design is original) |
| Dense retrieval (semantic embedding similarity) | OpenAI `text-embedding-3-small` API | **Standard IR infrastructure**, not original |
| Reciprocal Rank Fusion (multi-retriever fusion) | Standard algorithm (Cormack et al. 2009) | Standard method |
| LLM reranker (Top-N relevance rescoring) | LLM API calls (LLM+Schema structured scoring) | Ranking-stage helper, gated by the rule-based Planner (the prompt design and the Planner's exact/semantic/exploratory routing rule are original) |
| Verifier (valid/rejected/unknown labeling + bounded retry) | Custom regex + control-flow design | **Original** |
| Cross-turn preference memory (session-scoped merge) | Custom design (MySQL-backed, not LangGraph checkpointer) | **Original** |
| Answer generation (LLM formatting) | LLM API calls | Post-processing helper |

> The project's core academic contribution: **for the job-search setting, we designed a domain-specific multi-field scoring suite that replaces traditional boolean filtering with continuous scoring, enabling finer-grained relevance ranking.** This design is independent of the text-retrieval library used and is what sets this project apart from "library + LLM" baselines.

### 3.5 Structured query understanding (LLM preprocessing stage)

> **Module placement**: this module sits in the **preprocessing stage**. The LLM converts user natural language into a structured preference object, which is then handed off to the traditional IR scoring engine. The LLM does not participate in retrieval, scoring, or ranking.

**Core flow**:

```
user question → prompt injection (field spec + few-shot) → LLM emits preference JSON → format check → into scoring engine
                                                                                       ↓ format error
                                                                              feedback to LLM → regenerate (max 2 retries)
```

**LLM task**: not to generate SQL, but to extract a **structured preference object** with target values + importance per field.

**Prompt sketch**:
```
You are a job-search query understanding assistant. From the user's natural-language
question, extract the following preference fields and output JSON. Set unmentioned
fields to null.

Fields:
- is_job_query: bool. Whether the user is asking about job/career/role search.
  Greetings, smalltalk, weather, math, etc. → false (added in the demo phase to
  drive upstream reject routing; see §3.9).
- description_keywords: list of keywords from the description text.
- target_salary: target annual salary (integer).
- preferred_location: preferred work location.
- remote_preference: remote / hybrid / onsite.
- desired_tags: list of desired tech-stack tags.
- preferred_category: category preference (backend / frontend / data / devops / fullstack / mobile / management).
- weight_adjustments: fields the user emphasized + importance (high/medium/low).
- hard_filters: list of absolute constraints (e.g. degree requirement) to exclude on.

Output JSON only, no explanation.
```

**Few-shot examples** (14 hard-coded: 10 positive + 3 negative + 1 vague-but-valid):

```
# Positive 1: multi-field extraction
Q: "Remote Python jobs above 150k"
{ "target_salary": 150000, "remote_preference": "remote",
  "desired_tags": ["Python"], "weight_adjustments": {"salary": "high", "remote": "high"} ... }

# Positive 2: multi tech tokens + location
Q: "ML roles near New York, ideally over 120k"
{ "description_keywords": ["machine learning"], "target_salary": 120000,
  "preferred_location": "New York", "desired_tags": ["Machine Learning"],
  "preferred_category": "data", "weight_adjustments": {"location": "high", "salary": "medium"} ... }

# Positive 3: hard filter
Q: "Junior dev positions, no PhD required"
{ "description_keywords": ["junior", "entry level"],
  "hard_filters": [{"field": "degree_req", "exclude": ["phd"]}] ... }

# Positive 9: single tech token → still a job query, into desired_tags
Q: "python"
{ "is_job_query": True, "desired_tags": ["Python"] ... }

# Positive 10: "highest paying" sentinel → target=999999 triggers score_salary sentinel branch
Q: "Highest paying Go developer positions"
{ "description_keywords": ["Go developer"], "target_salary": 999999,
  "desired_tags": ["Go"], "weight_adjustments": {"salary": "high"} ... }

# Negative 1-3: non-job query, is_job_query=False → graph routes to reject node
Q: "hi"                  → { "is_job_query": False, ... all null ... }
Q: "What's the weather"  → { "is_job_query": False, ... all null ... }
Q: "1 + 1 = ?"           → { "is_job_query": False, ... all null ... }

# Vague-but-valid: vague but still a job query, is_job_query=True, all fields empty
Q: "find me a job please" → { "is_job_query": True, ... all null ... }
```

**Importance → weight mapping**:
- `"high"` → field weight × 2.0
- `"medium"` → field weight × 1.0 (default)
- `"low"` → field weight × 0.5
- All adjusted weights are renormalized so they sum to 1.0.

**Validation rules**: output must be valid JSON, with type-correct fields (salary integer, tags list, etc.). On failure, the error is fed back to the LLM and we retry.

### 3.6 Query Expansion

> **Method family**: Term Clustering / Query Expansion.

**Motivation**: user query terms are often incomplete. A user searching "ML jobs" almost certainly also wants jobs whose descriptions mention "machine learning" or "deep learning", but the bare term "ML" cannot match these documents. Query expansion solves this by automatically supplementing synonyms and related terms.

**Implementation — domain synonym table (hand-built + auto-augmented)**:

```python
# Hand-built synonym / abbreviation table for tech terms
TECH_SYNONYMS = {
    "ml":       ["machine learning", "ML"],
    "ai":       ["artificial intelligence", "AI"],
    "dl":       ["deep learning"],
    "nlp":      ["natural language processing", "NLP"],
    "cv":       ["computer vision"],
    "js":       ["javascript", "JS"],
    "ts":       ["typescript", "TS"],
    "k8s":      ["kubernetes"],
    "postgres": ["postgresql", "postgres"],
    "gcp":      ["google cloud platform", "google cloud"],
    "aws":      ["amazon web services"],
    "fe":       ["frontend", "front-end", "front end"],
    "be":       ["backend", "back-end", "back end"],
    "devops":   ["dev ops", "site reliability", "SRE"],
    "infra":    ["infrastructure"],
    # ... ~90 mappings (tech ~60 + titles ~20 + locations ~10)
}

# Hypernym / hyponym relations
TECH_HIERARCHY = {
    "machine learning": ["deep learning", "reinforcement learning", "supervised learning"],
    "frontend":         ["react", "vue", "angular", "svelte"],
    "backend":          ["django", "flask", "express", "spring"],
    "database":         ["mysql", "postgresql", "mongodb", "redis"],
    "cloud":            ["aws", "gcp", "azure"],
    # ...
}

def expand_query(keywords, tags):
    """
    Expand description_keywords and desired_tags.
    1. Synonym expansion: look up TECH_SYNONYMS and add all synonym forms.
    2. Hypernym/hyponym expansion (optional, controlled): e.g. "database" →
       also retrieve "mysql", "postgresql", etc.
    3. Deduplicate + keep the original term.
    """
    expanded_kw = set(keywords) if keywords else set()
    expanded_tags = set(tags) if tags else set()

    for term in list(expanded_kw):
        normalized = term.lower().strip()
        if normalized in TECH_SYNONYMS:
            expanded_kw.update(TECH_SYNONYMS[normalized])

    for tag in list(expanded_tags):
        normalized = tag.lower().strip()
        if normalized in TECH_SYNONYMS:
            expanded_tags.update(TECH_SYNONYMS[normalized])
        # optional: expand one level down through the hypernym/hyponym table
        if normalized in TECH_HIERARCHY:
            expanded_tags.update(TECH_HIERARCHY[normalized])

    return list(expanded_kw), list(expanded_tags)
```

**Expansion examples**:

| Original query | After expansion |
|---------------|-----------------|
| keywords=["ML jobs"] | keywords=["ML jobs", "machine learning"] |
| tags=["JS", "TS"] | tags=["JS", "TS", "javascript", "typescript"] |
| tags=["database"] | tags=["database", "mysql", "postgresql", "mongodb", "redis"] |
| keywords=["k8s infra"] | keywords=["k8s infra", "kubernetes", "infrastructure"] |

**Position in the pipeline**: LLM extracts preferences → **Query Expansion** → into the scoring engine. Expansion runs after the LLM and before scoring; the expanded keywords feed both TF-IDF text retrieval and tag-match scoring.

> **Originality note**: the synonym table and the hypernym/hyponym table are hand-built domain resources designed for the tech-recruiting setting. The expansion logic itself is standard query-expansion technique.

### 3.7 Automatic job classification (vector centroid classifier)

> **Method family**: Vector Models + Supervised IR / vector-space classification.

**Motivation**: assign each job a category label (backend / frontend / data / devops / fullstack / mobile / management) for two purposes:
1. **The user can filter or browse by category**: e.g. "show me all data engineering jobs".
2. **Provides classification accuracy as an independent evaluation metric.**

**Implementation — vector centroid classification (Rocchio-style)**:

```python
# Training stage: build TF-IDF centroid vectors per category
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

# 1. Training-set labeling (v1: 120 + v2: 613 = 733 entries):
#    v1 (2026-04-20): stratified sample of 120 jobs from the crawl, GPT-4o-mini
#       initial labeling → export prompt → independent re-labeling by Claude /
#       ChatGPT / Gemini → majority vote + manual tie-breaking.
#    v2 (2026-04-24): adds the public HuggingFace dataset
#       yiqing111/Engineering_Jobs_Insight_Dataset (MIT, 11,185 entries) +
#       keyword whitelist/blacklist filtering down to 613 entries +
#       GPT-4o-mini gap-filling + 3-LLM re-labeling + majority vote → merged
#       with v1 to produce data/labeled_jobs.json (733 entries).
CATEGORIES = ["backend", "frontend", "data", "devops", "fullstack", "mobile", "management"]

# 2. Use TfidfVectorizer to embed each job's description + title + tags
vectorizer = TfidfVectorizer(...)  # reuse the §3.4.1 vectorizer or train separately
train_vectors = vectorizer.fit_transform(train_texts)

# 3. Compute the centroid vector per category
centroids = {}
for cat in CATEGORIES:
    cat_vectors = train_vectors[labels == cat]
    centroids[cat] = cat_vectors.mean(axis=0)

# Classification stage: cosine similarity between a new job and each centroid
from sklearn.metrics.pairwise import cosine_similarity

def classify_job(job_text):
    """
    Return (predicted_category, confidence_scores).
    confidence_scores is a dict of cosine similarities to each centroid.
    """
    vec = vectorizer.transform([job_text])
    scores = {}
    for cat, centroid in centroids.items():
        scores[cat] = cosine_similarity(vec, centroid)[0][0]
    predicted = max(scores, key=scores.get)
    return predicted, scores
```

**Classification flow**:
1. **Offline stage** (training-set preparation, two phases, 733 entries):
   - **v1 (2026-04-20, 120 entries)**: stratified sample of 120 jobs from MySQL (~15 per class via keyword pre-filter + the rest random fill, ensuring all 7 classes are covered).
     - **GPT-4o-mini initial labeling** (`src/classification/auto_label.py`): Temperature=0.0, with prompt rules to handle HackerNews multi-role posts (classify by the first / most-emphasized role; do not over-use `fullstack`).
     - **Multi-LLM cross-validation** (`src/classification/export_review_prompt.py`): 20% subsample exported as a unified prompt → independent re-labeling by Claude / GPT / Gemini → outputs collected in `data/reviews/*.json`.
     - **Majority vote merge + manual tie-breaking**: human resolves entries where the LLMs disagree; otherwise the majority vote is taken.
   - **v2 expansion (2026-04-24, +613 entries)**: small classes such as `mobile` were stuck at 33 entries; we add the public HuggingFace dataset `yiqing111/Engineering_Jobs_Insight_Dataset` (MIT, 11,185 entries):
     - **Keyword whitelist/blacklist filtering**: keep 613 semantically clear entries.
     - **GPT-4o-mini gap-filling + 3-LLM re-labeling + majority vote**: same flow as v1.
     - **Merge**: v1 120 + v2 613 = **733 entries** → written to `data/labeled_jobs.json`.
   - **Build the 7 TF-IDF centroid vectors**: based on the 733-entry training set.
2. **Ingest stage**: every newly crawled job is auto-classified, with the category written to `jobs.category` in MySQL.
3. **Query stage**: the user can filter or weight by category (e.g. "data engineering jobs" → activates the `category` field score).

**Integration with the scoring engine (2026-04-25: argmax-aware soft scoring)**:

To stay consistent with the project's anti-hard-filter stance, `score_category` is no longer 0/1 hard match. Instead, we use the classifier's 7-d cosine output (written to `data/category_scores.json` by `batch_predict --apply`; gold entries get a one-hot) to do soft scoring:

```python
def score_category(job, preferred_category):
    """argmax-aware soft scoring:
       argmax==target → 1.0 (hard reward; full credit when classification is correct)
       argmax!=target → cosine[target] (partial credit when classification is wrong but close)
    """
    if preferred_category is None:
        return 1.0
    cat_scores = self.category_scores_map.get(job["job_id"])
    if cat_scores:
        if max(cat_scores, key=cat_scores.get) == preferred_category:
            return 1.0
        return float(cat_scores.get(preferred_category, 0.0))
    # Fallback (when the map is missing): hard match.
    return 1.0 if job.get("category") == preferred_category else 0.0
```

> **Design tradeoff note**: pure cosine soft scoring (returning `cat_scores[target]` directly) measurably dropped the `with_category` ablation config's P@5 from 0.465 to 0.375 (-0.09) — the cosine for non-gold entries (1578/2311) sits in the 0.1–0.4 range, the "hard reward" for correct predictions gets diluted, and incorrect predictions also get small credit, washing out the description / salary signal. The argmax-aware compromise gives 1.0 to correct predictions (equivalent to hard match) and partial credit to wrong predictions whose target-class cosine is high (where hard match would give 0). With this, the `with_category` config's nDCG@10 goes 0.639 → 0.641 (slight improvement), P@5 stays at 0.465 — preserving the anti-hard-filter stance without letting classifier noise drag the numbers down.

The scoring engine adds a `category` field with default weight 0.10. `DEFAULT_WEIGHTS` becomes:

```python
DEFAULT_WEIGHTS = {
    "description": 0.35,
    "salary":      0.20,
    "location":    0.15,
    "remote":      0.10,
    "tags":        0.10,
    "category":    0.10,  # added
}
```

> **Originality note**: vector centroid classification is a classical IR classification method (Rocchio classifier) implemented with scikit-learn. The training-set labeling pipeline (GPT-4o-mini initial labeling + multi-LLM cross-validation + majority-vote merge + manual tie-breaking) and the category taxonomy are original work; the LLM is used only to assist labeling, and final quality is enforced by multi-model cross-validation plus human adjudication.

### 3.8 Unified scoring and ranking

**Core idea (updated for vNext)**: within the core IR stage there is no routing branch — every job query goes through the same scoring formula, and the only difference is which fields get activated. The pipeline as a whole, however, now does branch at two points that sit *outside* the scoring engine itself: `query_understanding` can short-circuit to `reject` (non-job query) or `clarify` (job query, but too underspecified to retrieve anything meaningful — see §3.10), and `verification` can loop back to `unified_scoring` once with a strengthened retrieval config if nothing verified as valid (see §3.11). Neither branch changes how a single scoring pass computes `S(job)`.

**Unified scoring flow**:
1. LLM extracts preferences → Query Expansion expands keywords → determine which fields have target values (active) and which do not (skipped).
2. Apply `weight_adjustments` to default weights, then renormalize over active fields.
3. Iterate over all candidate jobs; for each job compute per-field scores and the weighted sum.
4. Sort by composite score descending and return top-K.

**Dynamic weight-adjustment examples**:

| User query | Active fields | Renormalized weights |
|---------|---------|-------------------|
| "Python jobs with good work-life balance" | description, tags | desc=0.73, tags=0.27 |
| "Remote jobs in NYC above 150k" | salary(high), location, remote(high) | salary=0.40, loc=0.15, remote=0.20 → renormalized to salary=0.53, loc=0.20, remote=0.27 |
| "ML engineer positions" | description, tags | desc=0.73, tags=0.27 |

**Hard filtering (absolute constraints only)**:

Hard filtering is applied at candidate-load time via SQL `WHERE`, **only when partial matching is meaningless**:

| Hard-filter scenario | Description | SQL |
|-----------|------|-----|
| Degree requirement | The job requires a master's, the user only has a bachelor's → fully exclude | `WHERE degree_req IN ('none','bachelor','unknown')` |
| Visa restriction | The job does not sponsor visas, the user needs sponsorship → fully exclude | `WHERE visa_sponsor = TRUE` |

**Why salary / location are not hard-filtered**: with target salary 100k, a $99k job still has 0.94 relevance and should not be excluded. When searching New York, a New Jersey job still has 1.0 same-metro relevance (after the `metro_areas` aliases cover 'NYC' etc.) and also should not be excluded.

**Collection Fusion node behaviour** (`src/scoring/fusion.py:fuse_and_rank`): merging dual-source candidates supports three independent flags `normalize` / `dedupe` / `top_k` —

| Flag | Default | Behaviour | When to enable |
|------|------|------|---------|
| `normalize=False` | ✓ | Sort by `final_score` desc and take top-K | **Current production config** (pool_eval / demo both use the default) |
| `normalize=True` | | Min-max normalize within each source group, then sort by `normalized_score` | Kept only as an ablation comparison |
| `dedupe=True` | | Deduplicate by (company, title) so the same job posted under multiple `job_id`s does not flood the top-K | **Enabled on the demo path** (`graph.py:node_collection_fusion` passes `dedupe=True`); pool_eval uses its own evaluation code that bypasses this node, so the ablation numbers are unaffected |

**Why `normalize` is bypassed by default**: empirically, min-max normalization forced both sources' "local maxima" to equal 1.0, which let the smaller source (Greenhouse, 178 entries — only 7.7% of the corpus) repeatedly push edge-case jobs (e.g. 'Brazil - Remote') into the top-10. We bypass it by default, while keeping `normalize_scores` as an optional tool and as the regression baseline.

**Why the demo path enables `dedupe`**: HN "Who is Hiring" is a monthly thread — the same company / role gets posted across multiple monthly threads, producing different `job_id`s in IE. Without dedup, a demo user searching "senior python remote" sees companies like River / RINSE appearing 2–3 times in the top-5 (observed repeatedly during manual testing). `dedupe` defaults off and is explicitly enabled by the graph, so the pool_eval evaluation path keeps its original behaviour.

### 3.9 LLM answer generation (post-processing stage)

> **Module placement**: this module sits in the **post-processing stage**. Retrieval and ranking are already done by the traditional IR scoring engine; the LLM only formats the already-ranked top-K into a natural-language answer. The LLM does not affect ranking.

**LangGraph state diagram (vNext, 10 nodes)**:

```
START → [pre] query_understanding ──[is_job_query=false]──────────────────> reject → END
                                  ──[needs_clarification=true]────────────> clarify → END
                                  ──[else]──> [core IR] query_expansion → candidate_loading
                                            → unified_scoring → collection_fusion → verification
                                                                                  ──[0 valid & retry_count<1]──┐
                                                                                  ──[else]──> classification    │
                                                                                            → [post] answer_generation → END
                                                                                  └────────── loop back to unified_scoring
```

**Per-node description**:

| Node | Stage | Function | Implementation |
|------|------|------|------|
| `query_understanding` | preprocessing | Extracts the preference JSON, the `is_job_query` intent flag, and (vNext) the `retrieval_mode` classification for the Planner; merges with cross-turn memory when `session_id` is set (§3.12) | LLM + few-shot prompt |
| `query_expansion` | **core IR** | Expands keywords and tags via synonyms / hypernyms | Domain synonym table |
| `candidate_loading` | data load | Loads candidates from MySQL (applying hard filters if any) | SQL SELECT |
| `unified_scoring` | **core IR** | Constrained Planner selects TF-IDF/BM25/Dense/RRF (+ optional LLM reranker, §3.4.1d) for the textual signal, then computes the multi-field composite score per candidate | Multi-field scoring functions + Planner |
| `collection_fusion` | **core IR** | Merges dual-source candidates + selects top-K; demo path enables (company, title) dedup | Default sort by `final_score` desc + dedup (see end of §3.8) |
| `verification` (vNext) | **post-scoring guard** | Labels each result `valid`/`rejected`/`unknown` against hard-to-score constraints (part-time/intern title, missing salary data); if zero results verify as `valid`, forces a single retry with a stronger retrieval config | Rule-based, no LLM call (§3.11) |
| `classification` | **core IR** | Attaches a category label to each top-K result, supporting category-grouped display | Vector centroid classifier |
| `answer_generation` | post-processing | Sends top-K + the original question to the LLM to produce the answer, honestly flagging `unknown`-verification results as caveated rather than confirmed | LLM natural-language generation |
| `reject` | short-circuit | When `is_job_query=false`, short-circuit here, output a polite refusal + empty results, skipping the core IR nodes | Static text generation (no LLM call) |
| `clarify` (vNext) | short-circuit | When the query is a genuine cold-start (no cross-turn memory) classified `exploratory` with every preference field empty, ask a clarifying question instead of retrieving on no signal at all | Static text generation (no LLM call) |

**Answer generation**: the retrieval result (top-5 / top-10 jobs and their per-dimension scores) plus the user's original question are sent to the LLM, which produces a structured natural-language answer (list / comparison / summary) annotated with per-dimension match explanations, and calls out any `unknown`-verification job's caveat explicitly rather than presenting it as fully confirmed.

### 3.10 Clarifying questions instead of guessing (`node_clarify`, added in vNext)

An `exploratory`-classified query (§3.4.1d) with literally no extractable signal — no keywords, salary, location, remote preference, tags, or category — gives the retrieval stage nothing to rank on; guessing at that point just returns noise. `_route_after_understanding` routes to `clarify` only when **all** of the following hold: `is_job_query` is true, the session had no prior cross-turn memory to fall back on (§3.12), `retrieval_mode == "exploratory"`, and every preference field is empty. This is intentionally narrow — a query that's vague but still carries *some* signal (e.g. "find me a Python job") still flows through the normal `exploratory` retrieval path (broadest recall + reranker), since that's exactly what the Planner's `exploratory` mode exists to handle; asking a clarifying question on every mildly vague query would make step ④ (Planner) pointless.

### 3.11 Verifier and bounded retry (`src/scoring/verifier.py`, added in vNext)

Ranking score and actual eligibility are different things: a job can score highly on textual/field relevance while still being a part-time or internship posting when the user wants full-time work, or have no disclosed salary at all when the user specified a target salary — the salary scorer treats missing data as neutral (0.5), which is correct for ranking but not the same as "verified to meet the requirement." `verify_jobs()` runs after `collection_fusion`, purely rule-based (regex on title + a target-salary/missing-data check — no LLM call, since this doesn't need semantic understanding and a rule is faster, cheaper, and fully deterministic), and labels each ranked job:

- **`rejected`**: title matches a non-fulltime pattern (`part-time`, `intern(s/ship/ships)`, `temporary`, `temp`, `(1099)`, `(Contractor)`, bare `contract` — with a negative-lookbehind so "Smart Contract Engineer" isn't caught) **and** the user's own query doesn't also mention that same category (so a query that's explicitly asking for an internship doesn't have its own results rejected).
- **`unknown`**: the user specified a `target_salary` but the job has no `salary_min`/`salary_max` on file — relevance can't be verified either way. These are kept (not dropped) but flagged; `answer_generation` (§3.9) surfaces the caveat instead of presenting the match as confirmed.
- **`valid`**: everything else.

`rejected` jobs are dropped from `verified_jobs`; if that leaves **zero** `valid` jobs and this is the first pass (`retry_count < 1`), `node_verification` loops back to `unified_scoring` with `config` forced to `{"ir_mode": "hybrid_rrf", "use_reranker": True}` — the strongest retrieval combination available — and retries once. This is a graceful-degradation design, not a guarantee: if the query already ran under `hybrid_rrf`+reranker, the retry is a no-op (same candidates score the same way again), and vNext's requirement is only "retry at most once," not "retry until something verifies."

### 3.12 Cross-turn preference memory (`src/db/memory.py`, added in vNext)

LangGraph's own `interrupt`/checkpointer machinery wasn't adopted here; instead, a `session_id` (optional — `None` behaves exactly like the pre-vNext single-turn pipeline) keys a `preferences` JSON blob in a small MySQL table (`user_memory`, see `src/db/schema.sql`). On each call, `node_query_understanding` loads any prior memory for that session, then **merges** it with the current turn's freshly-extracted preferences: a field the user explicitly mentioned this turn always wins; a field left unmentioned (null/empty) falls back to what was remembered from before. Only the "stable profile" fields are persisted/inherited this way — `description_keywords`, `target_salary`, `preferred_location`, `remote_preference`, `desired_tags`, `preferred_category`, `hard_filters`. Fields that represent a judgment about *this specific utterance* — `is_job_query`, `weight_adjustments`, `retrieval_mode` — are never inherited from memory, since e.g. an emphasis the user expressed once ("salary is really important to me *right now*") shouldn't silently keep amplifying the salary weight on every future turn where they didn't say that again. The merged (not just the raw current-turn) preferences are written back after merging, so memory always reflects the latest complete picture.

---

## 4. Query examples

### Example 1: "Remote Python jobs above 150k"

| Step | Content |
|------|------|
| Preference extraction | target_salary=150000, remote="remote", tags=["Python"], weights: salary=high, remote=high |
| Active fields | salary(×2.0), remote(×2.0), tags(×1.0) → renormalized: salary=0.40, remote=0.40, tags=0.20 |
| Scoring example | JobA (remote, Python, $160k) → 1.0×0.4 + 1.0×0.4 + 1.0×0.2 = **1.00**; JobB (hybrid, Python, $140k) → 0.94×0.4 + 0.4×0.4 + 1.0×0.2 = **0.73** |

### Example 2: "Jobs in New York, ideally around 120k"

| Step | Content |
|------|------|
| Preference extraction | preferred_location="New York", target_salary=120000, weights: location=high, salary=medium |
| Active fields | location(×2.0), salary(×1.0) → renormalized: location=0.67, salary=0.33 |
| Scoring example | NYC job at $120k → 1.0×0.67 + 1.0×0.33 = **1.00**; **NJ job at $115k → 0.8×0.67 + 0.94×0.33 = 0.85 (not filtered out!)**; Chicago at $120k → 0.1×0.67 + 1.0×0.33 = 0.40 |

### Example 3: "Companies with good work-life balance for junior devs"

| Step | Content |
|------|------|
| Preference extraction | description_keywords=["work-life balance", "junior", "mentorship"] |
| Active fields | description only → weight=1.0 |
| Scoring example | Pure TF-IDF cosine-similarity ranking |

### Example 4: "Remote ML engineer at startups, 200k+, no PhD required"

| Step | Content |
|------|------|
| Preference extraction | description_keywords=["ML engineer", "startup"], remote="remote", target_salary=200000, tags=["Machine Learning"], hard_filters=[{degree_req exclude: phd}] |
| **Query Expansion** | tags: ["Machine Learning"] → ["Machine Learning", "deep learning", "reinforcement learning", "supervised learning"]; keywords: ["ML engineer"] → ["ML engineer", "machine learning"] |
| Hard filter | SQL: `WHERE degree_req != 'phd'` → exclude jobs requiring a PhD |
| Active fields | description, salary, remote, tags → all four scored |
| Scoring example | Per-field weighted composite score, **a $99k ML role still appears but ranks low (salary_score=0.00) — not entirely removed** |
| **Classification** | top-K results: 70% data, 30% backend → the answer groups by category |

### Example 5: "Highest paying Go developer positions"

| Step | Content |
|------|------|
| Preference extraction | tags=["Go"], target_salary=999999 (extreme target so high salaries are favored), weights: salary=high |
| Active fields | salary(×2.0), tags(×1.0) → renormalized: salary=0.67, tags=0.33 |
| Scoring example | Naturally sorted descending by salary score; high-pay Go jobs rank first |

### Example 6: "What tech stacks are most in demand for backend roles?"

| Step | Content |
|------|------|
| Preference extraction | description_keywords=["backend"] |
| Post-processing | IR retrieves top-50 backend-relevant jobs → aggregate the `tags` field counts → LLM generates the analysis report |

---

## 5. Risks and mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Crawl blocked / anti-scraping escalates | Medium | High | Fall back to a public Kaggle job dataset |
| HN posting format inconsistent | High | Medium | Regex fallbacks + skip unparseable entries while logging the parse-failure rate |
| High salary-missing rate | High | Low | Missing-salary jobs return a neutral 0.5 (no reward / no penalty); evaluations report the with-salary subset separately |
| Preference-extraction accuracy too low | Medium | Medium | More few-shot examples + JSON validation + error-feedback retry |
| Insufficient data hurts IR quality | Low | Medium | Crawl multiple monthly HN threads (300–500 entries each) for broader coverage |

---

## 6. Compliance

For academic-integrity transparency, the following are explicitly stated in the report:

### Third-party libraries used

| Library | Purpose | Touches core IR? |
|---------|---------|------------------|
| scikit-learn | TF-IDF vectorization + cosine similarity | Yes (standard IR infrastructure, not original) |
| rank_bm25 | BM25 retrieval (baseline) | Yes (standard IR infrastructure, not original) |
| nltk | Tokenization / stopwords / stemming | Preprocessing helper |
| BeautifulSoup | HTML parsing | Data-collection helper |
| requests | HTTP requests | Data-collection helper |
| numpy | Vector arithmetic | Compute helper |
| mysql-connector | Database connectivity | Storage helper |
| LangGraph | LLM orchestration | Pre/post-processing helper |
| OpenAI API (`gpt-4o-mini`) | LLM calls (preprocessing, reranker, post-processing) | Pre/post-processing helper; **also touches ranking** via the optional reranker (§3.4.1d) — see the updated LLM role declaration at the top of this document |
| OpenAI API (`text-embedding-3-small`) | Dense retrieval embeddings (§3.4.1b) | Yes (standard IR infrastructure, not original) |

### Data sources

- All data is acquired through our own crawlers from public websites, in accordance with each site's robots.txt.

### Original-contribution declaration

The original contributions of this project are concentrated in the following items; everything else is implemented through the libraries above:
1. **Multi-field scoring function design** (§3.4.2): salary asymmetric decay, location tiered proximity, remote match matrix, modified Jaccard for tags.
2. **Dynamic weight-normalization mechanism** (§3.4.3): query-adaptive field activation and weight redistribution.
3. **Domain-specific query-expansion resources** (§3.6): hand-built tech-domain synonym table (~90 mappings: tech ~60 + titles ~20 + locations ~10) and hypernym/hyponym table.
4. **Domain-specific data structures**: hand-built lookup tables of major US tech metros and their neighboring states.
5. **Job-classification training-set labeling** (§3.7): 733 jobs (v1: 120 stratified-sampled HN entries + v2: 613 entries from a public HuggingFace dataset, processed through keyword whitelist/blacklist + GPT-4o-mini gap-filling + Claude/ChatGPT/Gemini three-way cross-validation + majority vote + manual tie-breaking).
6. **System-integration design**: the pipeline architecture wiring LLM preprocessing, query expansion, traditional IR retrieval, multi-field scoring, vector classification, and LLM post-processing into one workflow.
7. **Constrained Planner** (§3.4.1d): the rule mapping a query's classified `retrieval_mode` to a concrete retrieval/reranker combination, and the decision to let an explicit `config` override it.
8. **Verifier + bounded retry** (§3.11): the rule-based valid/rejected/unknown classification and the single-retry-on-zero-valid control flow.
9. **Cross-turn preference-memory design** (§3.12): the field-level merge policy (stable-profile fields inherit from memory, per-utterance judgments never do) and its session-scoped MySQL persistence, built independently of LangGraph's own checkpointer mechanism.
10. **Clarify short-circuit** (§3.10): the narrow trigger condition for asking a clarifying question instead of retrieving on zero signal.

### vNext scope note

This document has been updated to describe the **vNext** version of the pipeline (Dense retrieval + RRF fusion, LLM reranker, Verifier + bounded retry, constrained Planner, clarifying questions, cross-turn preference memory — items 7–10 above plus §3.4.1b–d). The evaluation numbers referenced elsewhere in this repo under `data/eval_results/` predate vNext and reflect the pre-vNext pipeline (TF-IDF/BM25 only, no reranker/verifier/memory); vNext's own evaluation lives under `data/eval_results_vnext/`.
