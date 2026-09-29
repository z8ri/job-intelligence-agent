"""One-off check: download/load the cross-encoder, time it, and score two sample pairs.

The first run downloads BAAI/bge-reranker-base (~1.1GB) into ~/.cache/huggingface.
"""

import resource
import time

from src.agent.rerank import DEFAULT_MODEL, CrossEncoderScorer

PAIRS = [
    ("build LLM agents", "Build LLM-powered agents with tool use and retrieval"),
    ("build LLM agents", "Design payment APIs in Go"),
]

scorer = CrossEncoderScorer(DEFAULT_MODEL, device="cpu")
t = time.time()
scorer.score(PAIRS[:1])
print(f"load + first call: {time.time() - t:.1f}s")
t = time.time()
scores = scorer.score(PAIRS)
print(f"second call ({len(PAIRS)} pairs): {time.time() - t:.2f}s")
print("scores:", [round(s, 3) for s in scores])
print(f"peak RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 2:.0f} MB")
assert scores[0] > scores[1], "relevant pair should outscore irrelevant pair"
print("ok")
