import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

from src.ir.preprocess import preprocess


class JobBM25System:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.model_path = self.data_dir / "bm25_model.pkl"

        self.bm25: BM25Okapi | None = None
        self.job_ids: list[str] = []

    def train_from_db(self) -> None:
        from src.db.database import load_candidates

        jobs = load_candidates()
        corpus = [preprocess(f"{j.get('title', '')} {j.get('description', '')}") for j in jobs]
        self.job_ids = [j["job_id"] for j in jobs]

        print(f"对 {len(corpus)} 条职位构建 BM25 索引...")
        self.bm25 = BM25Okapi(corpus)
        self._save_model()
        print(f"BM25 模型已序列化至: {self.model_path}")

    def _save_model(self) -> None:
        with open(self.model_path, "wb") as f:
            pickle.dump({"bm25": self.bm25, "job_ids": self.job_ids}, f)

    def load_model(self) -> bool:
        if not self.model_path.exists():
            print("未发现 BM25 模型，请先运行 train_on_json()")
            return False
        with open(self.model_path, "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.job_ids = data["job_ids"]
        return True

    def get_similarities(self, query_text: str) -> dict[str, float]:
        if self.bm25 is None:
            if not self.load_model():
                return {}

        tokens = preprocess(query_text)
        scores = self.bm25.get_scores(tokens)

        s_min, s_max = float(scores.min()), float(scores.max())
        if s_max <= s_min:
            return {jid: 0.0 for jid in self.job_ids}
        norm = (scores - s_min) / (s_max - s_min)
        return {jid: float(s) for jid, s in zip(self.job_ids, norm)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Train BM25 index from MySQL jobs table"
    )
    parser.add_argument(
        "--train", action="store_true",
        help="训练 BM25 索引（不传也会训练，flag 仅供脚本化使用）",
    )
    parser.parse_args()

    bm25_system = JobBM25System()
    bm25_system.train_from_db()
    print("\n测试查询: 'Python developer with machine learning experience'")
    scores = bm25_system.get_similarities("Python developer with machine learning experience")
    top = sorted(scores.items(), key=lambda x: -x[1])[:5]
    for jid, s in top:
        print(f"  {jid}: {s:.4f}")
