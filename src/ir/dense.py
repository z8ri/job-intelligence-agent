"""Dense 检索：用 OpenAI embeddings 补 BM25/TF-IDF 词面检索漏掉的语义相关职位。

例：查询写"LLM Agent"，职位描述写"build LLM-powered workflows with tool use
and retrieval"——没有共同词项，BM25/TF-IDF 召回不到，但语义高度相关。

产物只 pickle 纯数据（job_ids / embeddings 数组 / model_name 字符串），不
pickle 任何自定义类实例，避免 tfidf.py 曾踩过的 pickle 类路径依赖 __main__
的问题（见 memory project_pickle_main_gotcha）。
"""

import pickle
from pathlib import Path

import numpy as np

from src.llm import EMBEDDING_MODEL, get_client

_EMBED_BATCH_SIZE = 100


def _embed_texts(client, texts: list[str]) -> np.ndarray:
    """分批调用 embeddings API，返回按输入顺序排列、已做 L2 归一化的矩阵。"""
    vectors: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        # API 按输入顺序返回，但每条结果自带 index，按它排序兜底，避免
        # job_id 和向量错位这种最隐蔽的 bug。
        ordered = sorted(resp.data, key=lambda item: item.index)
        vectors.extend(item.embedding for item in ordered)

    matrix = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class JobDenseSystem:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.model_path = self.data_dir / "dense_model.pkl"

        self.job_ids: list[str] = []
        self.embeddings: np.ndarray | None = None  # (N, dim)，行已 L2 归一化

    def train_from_db(self, api_key: str | None = None) -> None:
        from src.db.database import load_candidates

        jobs = load_candidates()
        texts = [f"{j.get('title', '')} {j.get('description', '')}" for j in jobs]
        self.job_ids = [j["job_id"] for j in jobs]

        print(f"对 {len(texts)} 条职位调用 {EMBEDDING_MODEL} 生成向量...")
        client = get_client(api_key)
        self.embeddings = _embed_texts(client, texts)

        self._save_model()
        print(f"Dense 模型已序列化至: {self.model_path}")

    def _save_model(self) -> None:
        with open(self.model_path, "wb") as f:
            pickle.dump(
                {
                    "job_ids": self.job_ids,
                    "embeddings": self.embeddings,
                    "model_name": EMBEDDING_MODEL,
                },
                f,
            )

    def load_model(self) -> bool:
        if not self.model_path.exists():
            print("未发现 Dense 模型，请先运行 train_from_db()")
            return False
        with open(self.model_path, "rb") as f:
            data = pickle.load(f)

        saved_model = data.get("model_name")
        if saved_model != EMBEDDING_MODEL:
            raise ValueError(
                f"{self.model_path} 是用 '{saved_model}' 生成的，"
                f"和当前 EMBEDDING_MODEL='{EMBEDDING_MODEL}' 不一致——"
                "两个模型的向量空间不可比，直接用会得到无意义的相似度。"
                "请重新运行 train_from_db() 生成新索引。"
            )

        self.job_ids = data["job_ids"]
        self.embeddings = data["embeddings"]
        return True

    def get_similarities(self, query_text: str, api_key: str | None = None) -> dict[str, float]:
        if self.embeddings is None:
            if not self.load_model():
                return {}

        client = get_client(api_key)
        query_vec = _embed_texts(client, [query_text])[0]

        scores = self.embeddings @ query_vec  # 行已归一化 → 点积 == cosine

        s_min, s_max = float(scores.min()), float(scores.max())
        if s_max <= s_min:
            return {jid: 0.0 for jid in self.job_ids}
        norm = (scores - s_min) / (s_max - s_min)
        return {jid: float(s) for jid, s in zip(self.job_ids, norm)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Train dense (OpenAI embedding) index from MySQL jobs table"
    )
    parser.add_argument(
        "--train", action="store_true",
        help="训练 Dense 索引（不传也会训练，flag 仅供脚本化使用）",
    )
    parser.parse_args()

    dense_system = JobDenseSystem()
    dense_system.train_from_db()
    print("\n测试查询: 'build LLM-powered workflows with tool use and retrieval'")
    scores = dense_system.get_similarities(
        "build LLM-powered workflows with tool use and retrieval"
    )
    top = sorted(scores.items(), key=lambda x: -x[1])[:5]
    for jid, s in top:
        print(f"  {jid}: {s:.4f}")
