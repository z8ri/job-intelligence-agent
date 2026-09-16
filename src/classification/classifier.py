"""
Rocchio-style vector centroid classifier for job categories.

Uses scikit-learn TfidfVectorizer to build TF-IDF representations,
computes centroid vectors per category, and classifies by cosine similarity.

7 categories: backend, frontend, data, devops, fullstack, mobile, management
"""

import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import classification_report, confusion_matrix
import joblib

CATEGORIES = [
    "backend", "frontend", "data", "devops",
    "fullstack", "mobile", "management",
]


class JobClassifier:
    """Rocchio-style centroid classifier for job categories."""

    def __init__(self):
        self.vectorizer: TfidfVectorizer | None = None
        self.centroids: dict[str, np.ndarray] = {}

    def _check_trained(self):
        if not self.vectorizer or not self.centroids:
            raise RuntimeError("Classifier not trained or loaded")

    @staticmethod
    def prepare_text(job: dict) -> str:
        """Combine title + tags + description into a single text string."""
        parts = []
        if job.get("title"):
            parts.append(job["title"])
        tags = job.get("tags")
        if tags:
            if isinstance(tags, list):
                parts.append(" ".join(tags))
            else:
                parts.append(str(tags))
        if job.get("description"):
            parts.append(job["description"])
        return " ".join(parts)

    def train(self, labeled_jobs: list[dict]) -> dict:
        """
        Train classifier from labeled data.

        Args:
            labeled_jobs: list of dicts, each with:
                - "category": str (one of CATEGORIES)
                - Either "text": str (pre-combined text)
                  or "title"/"tags"/"description" fields to combine

        Returns:
            dict with training stats: {samples_per_category, total, vocab_size}
        """
        texts = []
        labels = []
        for job in labeled_jobs:
            text = job.get("text") or self.prepare_text(job)
            category = job["category"]
            if category not in CATEGORIES:
                continue
            texts.append(text)
            labels.append(category)

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=10000,
            sublinear_tf=True,
        )
        tfidf_matrix = self.vectorizer.fit_transform(texts)

        self.centroids = {}
        labels_arr = np.array(labels)
        samples_per_category = {}
        for cat in CATEGORIES:
            mask = labels_arr == cat
            count = int(mask.sum())
            samples_per_category[cat] = count
            if count > 0:
                cat_vectors = tfidf_matrix[mask]
                centroid = cat_vectors.mean(axis=0)
                self.centroids[cat] = np.asarray(centroid).flatten()

        return {
            "samples_per_category": samples_per_category,
            "total": len(texts),
            "vocab_size": len(self.vectorizer.vocabulary_),
        }

    def predict(self, job_text: str) -> tuple[str, dict[str, float]]:
        """
        Predict category for a single job.

        Args:
            job_text: combined text (title + tags + description)

        Returns:
            (predicted_category, confidence_scores)
            confidence_scores maps each category to its cosine similarity
        """
        return self.predict_batch([job_text])[0]

    def predict_batch(self, job_texts: list[str]) -> list[tuple[str, dict[str, float]]]:
        """Batch prediction for efficiency."""
        self._check_trained()

        vecs = self.vectorizer.transform(job_texts)

        cat_names = list(self.centroids.keys())
        centroid_matrix = np.vstack([self.centroids[c] for c in cat_names])
        sim_matrix = cosine_similarity(vecs, centroid_matrix)  # (n_jobs, n_categories)

        results = []
        for i in range(len(job_texts)):
            scores = {cat_names[j]: float(sim_matrix[i, j]) for j in range(len(cat_names))}
            predicted = max(scores, key=scores.get)
            results.append((predicted, scores))
        return results

    def save(self, directory: str) -> None:
        """Save trained model to disk."""
        self._check_trained()

        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.vectorizer, dir_path / "vectorizer.joblib")
        np.savez(
            dir_path / "centroids.npz",
            **{cat: vec for cat, vec in self.centroids.items()},
        )

        meta = {"categories": list(self.centroids.keys())}
        with open(dir_path / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f)

    @classmethod
    def load(cls, directory: str) -> "JobClassifier":
        """Load a trained classifier from disk."""
        dir_path = Path(directory)
        instance = cls()
        instance.vectorizer = joblib.load(dir_path / "vectorizer.joblib")

        data = np.load(dir_path / "centroids.npz")
        with open(dir_path / "meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)

        instance.centroids = {cat: data[cat] for cat in meta["categories"]}
        return instance

    def evaluate(self, test_jobs: list[dict]) -> dict:
        """
        Evaluate classifier on labeled test set.

        Args:
            test_jobs: list of dicts with "text" or title/tags/description + "category"

        Returns:
            dict with accuracy, classification_report, confusion_matrix
        """
        texts = []
        true_labels = []
        for job in test_jobs:
            text = job.get("text") or self.prepare_text(job)
            texts.append(text)
            true_labels.append(job["category"])

        predictions = self.predict_batch(texts)
        pred_labels = [p[0] for p in predictions]

        correct = sum(1 for t, p in zip(true_labels, pred_labels) if t == p)
        accuracy = correct / len(true_labels) if true_labels else 0.0

        present_labels = sorted(set(true_labels + pred_labels))
        report = classification_report(
            true_labels, pred_labels, labels=present_labels, output_dict=True,
        )
        cm = confusion_matrix(true_labels, pred_labels, labels=present_labels)

        return {
            "accuracy": accuracy,
            "classification_report": report,
            "confusion_matrix": cm.tolist(),
            "labels": present_labels,
        }


# ---------------------------------------------------------------------------
# Module-level convenience functions (for pipeline integration)
# ---------------------------------------------------------------------------

_classifier_instance: JobClassifier | None = None
_default_model_dir = str(Path(__file__).parent.parent.parent / "models" / "classifier")


def load_classifier(model_dir: str | None = None) -> None:
    """Load classifier into module-level singleton."""
    global _classifier_instance
    _classifier_instance = JobClassifier.load(model_dir or _default_model_dir)


def classify_job(job_text: str) -> tuple[str, dict[str, float]]:
    """
    Classify a single job. Loads model on first call if needed.

    Args:
        job_text: combined text (title + tags + description)

    Returns:
        (predicted_category, {category: similarity_score})
    """
    global _classifier_instance
    if _classifier_instance is None:
        load_classifier()
    return _classifier_instance.predict(job_text)


def train_and_save(
    data_path: str = "data/labeled_jobs.json",
    model_dir: str | None = None,
) -> dict:
    """
    Train classifier from labeled JSON file and save model.

    Args:
        data_path: path to JSON file containing labeled jobs
        model_dir: directory to save trained model

    Returns:
        training stats dict
    """
    with open(data_path, "r", encoding="utf-8") as f:
        labeled_jobs = json.load(f)

    clf = JobClassifier()
    stats = clf.train(labeled_jobs)
    clf.save(model_dir or _default_model_dir)
    print(f"训练完成: {stats['total']} 条数据, 词汇量 {stats['vocab_size']}")
    print(f"各类别样本数: {stats['samples_per_category']}")
    print(f"模型已保存到: {model_dir or _default_model_dir}")
    return stats


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python classifier.py train [data_path] [model_dir]  # 训练并保存")
        print("  python classifier.py predict <text>                  # 预测单条文本")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd in ("train", "--train"):
        rest = sys.argv[2:]
        dp = rest[0] if len(rest) >= 1 else "data/labeled_jobs.json"
        md = rest[1] if len(rest) >= 2 else None
        train_and_save(dp, md)
    elif cmd in ("predict", "--predict") and len(sys.argv) >= 3:
        text = " ".join(sys.argv[2:])
        cat, scores = classify_job(text)
        print(f"预测类别: {cat}")
        for c, s in sorted(scores.items(), key=lambda x: -x[1]):
            print(f"  {c}: {s:.4f}")
    else:
        print(f"未知命令: {cmd}")
