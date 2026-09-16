import json
import pickle
import re
import numpy as np
from pathlib import Path
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

class _TextPreprocessor:
    """独立于 JobIRSystem 的可序列化 tokenizer。

    之前 tokenizer=self._preprocess_pipeline 是绑定方法，pickle 会连带把
    JobIRSystem 实例（含 base_dir/data_dir/model_path 等 Path 属性）一起
    序列化；在 Windows 上存的是 WindowsPath，换到 macOS/Linux 加载会
    NotImplementedError。这里拆成只含 stemmer/stop_words 的独立对象，
    避免 pickle 里混入平台相关的 Path。
    """

    def __init__(self):
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))

    def __call__(self, text):
        text = re.sub(r'[^\w\s]', '', text.lower())
        tokens = word_tokenize(text)
        return [
            self.stemmer.stem(w)
            for w in tokens
            if w not in self.stop_words and len(w) > 2
        ]


class JobIRSystem:
    def __init__(self, user_email="jwang@jhu.edu"):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.model_path = self.data_dir / "tfidf_model.pkl"

        self._preprocessor = _TextPreprocessor()
        self.stemmer = self._preprocessor.stemmer
        self.stop_words = self._preprocessor.stop_words

        self.vectorizer = TfidfVectorizer(
            tokenizer=self._preprocessor,
            token_pattern=None,
            lowercase=False
        )
        self.tfidf_matrix = None
        self.job_ids = []

    def train_on_json(self, input_filename="structured_jobs.json"):
        input_path = self.data_dir / input_filename
        if not input_path.exists():
            print(f"找不到数据文件: {input_path}")
            return

        with open(input_path, 'r', encoding='utf-8') as f:
            jobs = json.load(f)

        corpus = [f"{j['title']} {j['description']}" for j in jobs]
        self.job_ids = [j['job_id'] for j in jobs]

        print(f"正在对 {len(corpus)} 条职位进行向量化训练...")
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

        self._save_model()
        print(f"模型与矩阵已序列化至: {self.model_path}")

    def _save_model(self):
        with open(self.model_path, 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'matrix': self.tfidf_matrix,
                'job_ids': self.job_ids
            }, f)

    def load_model(self):
        if not self.model_path.exists():
            print("未发现已保存的模型，请先运行 train_on_json()")
            return False
            
        with open(self.model_path, 'rb') as f:
            data = pickle.load(f)
            self.vectorizer = data['vectorizer']
            self.tfidf_matrix = data['matrix']
            self.job_ids = data['job_ids']
        return True

    def get_similarities(self, query_text):
        if self.tfidf_matrix is None:
            if not self.load_model(): return {}

        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        return {jid: float(score) for jid, score in zip(self.job_ids, similarities)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Train TF-IDF index over data/structured_jobs.json"
    )
    parser.add_argument(
        "--train", action="store_true",
        help="训练 TF-IDF 索引（不传也会训练，flag 仅供脚本化使用）",
    )
    parser.parse_args()

    ir_system = JobIRSystem()
    ir_system.train_on_json()

    test_query = "Python developer with machine learning experience"
    print(f"\n测试查询: '{test_query}'")

    scores = ir_system.get_similarities(test_query)

    top_jobs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:5]
    print("最相关的职位推荐:")
    for jid, score in top_jobs:
        print(f"  - Job ID: {jid} | Text Similarity Score: {score:.4f}")
