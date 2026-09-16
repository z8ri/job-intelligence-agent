"""LLM modules: query understanding (preprocessing) + answer generation (postprocessing)."""

import os
from pathlib import Path
from openai import OpenAI

MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

_client: OpenAI | None = None


def _load_dotenv_once() -> None:
    """启动时把项目根 .env 里的 KEY=VALUE 注入 os.environ（已在 env 的不覆盖）。
    .env 已 gitignore；用户写一行 OPENAI_API_KEY=sk-... 即可。"""
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
