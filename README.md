# Job Intelligence Agent

Multi-source job-search system — natural-language queries + multi-field weighted scoring over English-language job postings, with a retrieval-strategy Planner, LLM reranking, result verification, and cross-turn preference memory (vNext).

## Background

This project started as coursework for **Information Retrieval and Web Agents** (EN.601.466/666) at Johns Hopkins University, taught by Prof. David Yarowsky, and has continued to evolve independently in this personal repository since.

## Overview

Ingests data from English-language job sources (HackerNews "Who is Hiring" crawler + the public Greenhouse / Lever JSON APIs), stores all fields in MySQL, and lets the user ask natural-language questions. A constrained Planner classifies each query (exact / semantic / exploratory) and picks a retrieval strategy — TF-IDF, BM25, Dense embeddings, or RRF fusion of BM25+Dense, optionally refined by an LLM reranker — then a multi-field weighted scoring engine computes a composite relevance score for every job. A rule-based Verifier filters out results that don't actually satisfy the user's constraints (and triggers one bounded retry if nothing survives), and preferences persist across turns within a session. See [docs/system_design.md](docs/system_design.md) for the full design, including what's original vs. library-based.

## Project layout

```
├── docs/                # System design, evaluation methodology, eval results, report draft
├── src/                 # Source code
│   ├── spider/          # Crawler + information extraction
│   ├── db/              # MySQL storage layer + cross-turn preference memory (memory.py)
│   ├── ir/              # TF-IDF / BM25 / Dense retrieval + RRF fusion + Query Expansion
│   ├── scoring/         # Multi-field scoring functions + Collection Fusion + LLM reranker + Verifier
│   ├── classification/  # Vector centroid classifier
│   ├── llm/             # LLM query understanding (incl. retrieval-mode classification) + answer generation
│   └── pipeline/        # LangGraph pipeline orchestration (constrained Planner, verification retry, clarify/reject)
├── data/                # Static data resources (synonyms, metro areas, etc.; `data/external/engineering_jobs.csv` is the public HuggingFace engineering-jobs dataset used to expand the v2 training set)
├── tests/               # Tests
└── eval/                # Evaluation experiments
```

## Quick start

### Prerequisites

1. **Conda env**: `conda activate jobir` (Python 3.11; dependencies in `requirements.txt`).
2. **MySQL 8.0**: start a local `job_intelligence` database (account / port noted in your local config), and run the ingest script once (≈ 2,311 records across both sources).
3. **`.env`**: at the project root, create `.env` with one line: `OPENAI_API_KEY=sk-...`.

### Command-line end-to-end

```bash
python -m src.pipeline.graph "remote senior backend python in NYC around 150k"
```

Returns an LLM-generated natural-language summary of the top-5 matching jobs.

### Interactive demo (recommended)

```bash
pip install -r requirements.txt
streamlit run app.py
```

The browser opens `http://localhost:8501`. The UI follows a modern conversational layout:

- **Left sidebar (264 px, persistent)**: top-left logo + "Job Intelligence" title / `✚ New chat` button / Recent chat list (click to switch; the current chat is highlighted with `primary` style).
- **Main area (max-width 760 px, centered)**: a welcome screen with 4 starter preset cards (Senior Python remote $150k+ / Frontend NYC hybrid / ML internship non-CS / Fullstack startup ~$130k) + a pill-shaped chat input at the bottom (Enter to submit, Shift+Enter for newline).
- **Answer area**: assistant natural-language summary + a "Top Matches" card section (each card shows category label / title / company · location / score / a 6-dimension score breakdown bar).
- **Pipeline live status**: each query expands an `st.status` block showing each node (query understanding → expansion → loading → scoring → fusion → verification → classification → answer generation) ticking off one by one. Non-job queries (e.g. "hi" / "weather today") short-circuit straight to the reject node; a genuinely underspecified query (e.g. "find me a job") short-circuits to a clarifying question instead of retrieving on no signal.
- **Retrieval strategy**: not hardcoded — the Planner classifies each query (exact / semantic / exploratory) and picks TF-IDF/BM25/Dense/RRF + whether to rerank; `top_k=5`. Ablation switches (forcing a specific `ir_mode` / Top-K / `equal_weights` / `skip_expansion`) live in `src/eval/*.py` for evaluation reproducibility and are not exposed in the demo UI.
- **Cross-turn memory**: each browser chat session carries a stable `session_id`, so preferences mentioned earlier in the same chat (e.g. "remote only") carry over to later turns that don't repeat them, without needing to re-state everything each message.
