"""LLM modules: query understanding (preprocessing) + answer generation (postprocessing)."""

import os
from pathlib import Path
from openai import OpenAI

MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

_client: OpenAI | None = None


def _load_dotenv_once() -> None:
    """At startup, load KEY=VALUE pairs from the project-root .env into os.environ
    (existing env vars are not overridden). .env is gitignored; a single line
    OPENAI_API_KEY=sk-... is enough."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv_once()


def get_client(api_key: str | None = None) -> OpenAI:
    """Return a cached OpenAI client (avoids recreating the HTTP pool per call)."""
    global _client
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if _client is None or (api_key and api_key != _client.api_key):
        _client = OpenAI(api_key=key)
    return _client
