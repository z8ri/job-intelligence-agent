import math
import json
import numpy as np
from pathlib import Path

class ScoringEngine:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.metro_areas = self._load_data("metro_areas.json")
        # 7 类 cosine 向量，用于 score_category 软评分；缺失则退回硬匹配
        self.category_scores_map = self._load_data("category_scores.json")
        
        # 默认权重配置
        self.DEFAULT_WEIGHTS = {
            "description": 0.35,
            "salary":      0.20,
            "location":    0.15,
            "remote":      0.10,
            "tags":        0.10,
            "category":    0.10
        }
        
        # 远程偏好匹配矩阵
        self.REMOTE_MATRIX = {
            "remote":      { "remote": 1.0, "hybrid": 0.4, "onsite": 0.1, "unknown": 0.3, "remote_or_onsite": 1.0 },
            "hybrid":      { "remote": 0.6, "hybrid": 1.0, "onsite": 0.5, "unknown": 0.4, "remote_or_onsite": 0.8 },
            "onsite":      { "remote": 0.2, "hybrid": 0.6, "onsite": 1.0, "unknown": 0.4, "remote_or_onsite": 1.0 },
            "remote_or_onsite": { "remote": 1.0, "hybrid": 0.8, "onsite": 1.0, "unknown": 0.5, "remote_or_onsite": 1.0 }
        }

        # 美国 50 州 full name → state code（用于 score_location 识别"jobs in Texas"等
        # 州级偏好；故意不收 "new york" / "washington" 单字，避免与 NYC 都会区
        # 城市 "new york" / DC 都会区城市 "washington" 冲突，强制让用户用 "new york state" /
        # "washington state" 表达州级意图）
        self.US_STATES = {
            "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
            "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de",
            "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id",
            "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks",
            "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md",
            "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms",
            "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv",
            "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm",
            "new york state": "ny",
            "north carolina": "nc", "north dakota": "nd",
            "ohio": "oh", "oklahoma": "ok", "oregon": "or",
            "pennsylvania": "pa", "rhode island": "ri", "south carolina": "sc",
            "south dakota": "sd", "tennessee": "tn", "texas": "tx", "utah": "ut",
            "vermont": "vt", "virginia": "va",
            "washington state": "wa",
            "west virginia": "wv", "wisconsin": "wi", "wyoming": "wy",
        }

    def _load_data(self, filename):
        path = self.base_dir / "data" / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    # 1. 薪资评分：非对称高斯衰减 + "highest paying" 哨兵模式
    def score_salary(self, job, target_salary):
        """
        通常模式：score = exp(-(delta / sigma)^2)，高于目标 sigma=50000，低于目标 sigma=20000。

        哨兵模式（target_salary >= 500000）：用户说"highest paying"等语义时，
        LLM 抽出极高 target，此时改用线性升档（薪资越高分越高，500k 上限封顶 1.0），
        salary 缺失工作惩罚到 0.0 而非中性 0.5，避免 n/a 工作冒到高薪查询的顶部。
        """
        if not target_salary: return 1.0
        s_min = job.get("salary_min") or None  # 把 0 当作缺失
        s_max = job.get("salary_max") or None

        # "highest paying" 语义：target_salary 哨兵值 >=500k 时进入"越高越好"模式
        is_highest_paying = target_salary >= 500000

        if s_min is None and s_max is None:
            # 普通模式：缺失薪资 → 中性 0.5；哨兵模式：缺失 → 0（无数据无法排序高薪）
            return 0.0 if is_highest_paying else 0.5

        if s_min is not None and s_max is not None:
            effective = max(s_min, min(target_salary, s_max))
        else:
            effective = s_min if s_min is not None else s_max

        if is_highest_paying:
            # 线性升档，500k 封顶；保留单调"高薪 → 高分"语义
            return min(effective / 500000, 1.0)

        delta = effective - target_salary
        sigma = 50000 if delta >= 0 else 20000
        return math.exp(-((delta / sigma) ** 2))

    # 2. 地点评分：分层近邻打分（远程档位细化）
    def score_location(self, job_loc, pref_loc):
        if not pref_loc:
            return 1.0
        if not job_loc or job_loc == "Unknown":
            return 0.3

        job_loc, pref_loc = job_loc.lower(), pref_loc.lower()

        if job_loc == pref_loc:
            return 1.0

        is_remote = "remote" in job_loc
        has_or = " or " in job_loc

        geo_part = (
            job_loc.replace("remote", "")
                   .replace(" or ", " ")
                   .replace(" - ", " ")
                   .replace(",", " ")
                   .replace("(", " ").replace(")", " ")
                   .strip()
        )
        geo_tokens = set(geo_part.split())

        # 州级偏好（"Texas" / "California" 等 full state name）单独走分支：
        # 用户意图是"该州任意城市都行"，应给 1.0 而非走 city-level fallback 落 0.1
        if pref_loc in self.US_STATES:
            target_state = self.US_STATES[pref_loc]
            in_state_cities: set[str] = set()
            neighbor_state_cities: set[str] = set()
            for _, info in self.metro_areas.items():
                cities = set(c.lower() for c in info.get("cities", []))
                if info.get("state") == target_state:
                    in_state_cities |= cities
                if target_state in info.get("neighbors", []):
                    neighbor_state_cities |= cities

            # 多词城市（如 "new orleans" / "san francisco"）会被 split 成多 token，
            # 单纯走 set & 比对会漏掉，加 substring 兜底（仅对含空格的城市，避免 "la"
            # 这种短 alias 误命中 "atlanta"）
            multi_word_in_state = {c for c in in_state_cities if " " in c}
            multi_word_neighbor = {c for c in neighbor_state_cities if " " in c}

            in_state_hit = (
                target_state in geo_tokens  # "austin, tx" 含 state code
                or job_loc in in_state_cities
                or geo_part in in_state_cities
                or bool(geo_tokens & in_state_cities)
                or any(c in geo_part for c in multi_word_in_state)
            )
            if in_state_hit:
                return 1.0 if not is_remote else 0.85
            neighbor_hit = (
                bool(geo_tokens & neighbor_state_cities)
                or geo_part in neighbor_state_cities
                or any(c in geo_part for c in multi_word_neighbor)
            )
            if neighbor_hit:
                return 0.5
            us_markers = {"us", "usa", "u.s.", "u.s.a.", "america"}
            if is_remote and (us_markers & geo_tokens or "united states" in geo_part):
                return 0.85
            if is_remote and not geo_part:
                return 0.85
            if is_remote and geo_part:
                return 0.4
            return 0.1

        # 纯 remote
        if is_remote and not geo_part:
            return 0.9

        # 'Remote or Onsite' / 'Remote or Hybrid' 等纯模式词组合：等价于"任选模式" → 0.9
        if is_remote and has_or and geo_tokens and \
           geo_tokens.issubset({"onsite", "hybrid", "office", "in-office"}):
            return 0.9

        # 'Remote or X' 形式：用户可任选远程或 X，至少 0.9；如 X 同 pref 都会区，给 0.85
        if is_remote and has_or:
            for metro, info in self.metro_areas.items():
                cities = set(c.lower() for c in info.get("cities", []))
                if pref_loc in cities and (geo_part in cities or geo_tokens & cities):
                    return 0.85
            return 0.9

        # 美国境内远程：用 token 级匹配（避免 'us' 被 'austin'/'houston' 子串误命中）
        us_markers = {"us", "usa", "u.s.", "u.s.a.", "america"}
        if is_remote and (us_markers & geo_tokens or "united states" in geo_part):
            return 0.85

        # 'X - Remote' 或纯地理（无 ' or '）
        for metro, info in self.metro_areas.items():
            cities = set(c.lower() for c in info.get("cities", []))
            if pref_loc in cities and (job_loc in cities or geo_part in cities or geo_tokens & cities):
                return 1.0 if not is_remote else 0.85
            if info.get("state") in (job_loc, pref_loc) and \
               (job_loc in cities or pref_loc in cities or geo_part in cities or geo_tokens & cities):
                return 0.5

        if is_remote and geo_part:
            return 0.4

        return 0.1

    # 3. 标签评分：修正 Jaccard 系数
    def score_tags(self, job_tags, desired_tags):
        if not desired_tags: return 1.0
        if not job_tags: return 0.0
        
        job_set = set(t.lower() for t in job_tags)
        desired_set = set(t.lower() for t in desired_tags)
        # 以用户期望为分母，不惩罚职位多出的技能
        return len(job_set & desired_set) / len(desired_set)

    # 4. 远程偏好评分
    def score_remote(self, job_remote, pref_remote):
        if not pref_remote: return 1.0
        return self.REMOTE_MATRIX.get(pref_remote, {}).get(job_remote, 0.3)

    # 综合评分逻辑与动态权重归一化
    def compute_final_score(self, job, preferences, tfidf_score=None,
                            weight_adjustments=None, active_fields=None):
        """
        计算总分：sum(w_i * score_i) / sum(w_i)

        active_fields: None=全自动（按 preferences 激活），或显式 set/list
        限定哪些字段参与（用于消融）。description 字段不再硬编码激活。
        """
        def _on(field):
            return active_fields is None or field in active_fields

        scores = {}
        if _on("description") and tfidf_score is not None:
            scores["description"] = tfidf_score
        if _on("salary") and preferences.get("target_salary"):
            scores["salary"] = self.score_salary(job, preferences["target_salary"])
        if _on("location") and preferences.get("preferred_location"):
            scores["location"] = self.score_location(job["location"], preferences["preferred_location"])
        if _on("remote") and preferences.get("remote_preference"):
            scores["remote"] = self.score_remote(job["remote"], preferences["remote_preference"])
        if _on("tags") and preferences.get("desired_tags"):
            scores["tags"] = self.score_tags(job["tags"], preferences["desired_tags"])
        if _on("category") and preferences.get("preferred_category"):
            target_cat = preferences["preferred_category"]
            cat_scores = self.category_scores_map.get(job.get("job_id"))
            if cat_scores:
                # argmax-aware 软评分：分类器 argmax==target → 1.0（硬奖励）；
                # argmax!=target → 给 target 类的 cosine（让"分错但接近的"也得部分分），
                # 既符合"反硬过滤"立场，又避免直接用 cosine 整体压低分数。
                if max(cat_scores, key=cat_scores.get) == target_cat:
                    scores["category"] = 1.0
                else:
                    scores["category"] = float(cat_scores.get(target_cat, 0.0))
            else:
                # 兜底：回退硬匹配
                scores["category"] = 1.0 if job.get("category") == target_cat else 0.0

        # 应用 LLM 提取的权重调整
        weights = self.DEFAULT_WEIGHTS.copy()
        if weight_adjustments:
            for field, level in weight_adjustments.items():
                if field not in weights:
                    continue
                if level == "high": weights[field] *= 2.0
                elif level == "low": weights[field] *= 0.5

        # 动态权重归一化：仅计算已激活字段的权重和
        active_weights = {k: weights[k] for k in scores.keys()}
        w_sum = sum(active_weights.values())

        if w_sum == 0: return 0.0, scores
        final_score = sum(scores[k] * active_weights[k] for k in scores) / w_sum

        return round(float(final_score), 4), scores