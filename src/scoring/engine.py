import math
import json
import numpy as np
from pathlib import Path

class ScoringEngine:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.metro_areas = self._load_data("metro_areas.json")
        # Per-job cosine vectors over the 7 categories, used for soft category scoring;
        # falls back to hard matching when missing
        self.category_scores_map = self._load_data("category_scores.json")

        # Default weight configuration
        self.DEFAULT_WEIGHTS = {
            "description": 0.35,
            "salary":      0.20,
            "location":    0.15,
            "remote":      0.10,
            "tags":        0.10,
            "category":    0.10
        }
        
        # Remote-preference match matrix
        self.REMOTE_MATRIX = {
            "remote":      { "remote": 1.0, "hybrid": 0.4, "onsite": 0.1, "unknown": 0.3, "remote_or_onsite": 1.0 },
            "hybrid":      { "remote": 0.6, "hybrid": 1.0, "onsite": 0.5, "unknown": 0.4, "remote_or_onsite": 0.8 },
            "onsite":      { "remote": 0.2, "hybrid": 0.6, "onsite": 1.0, "unknown": 0.4, "remote_or_onsite": 1.0 },
            "remote_or_onsite": { "remote": 1.0, "hybrid": 0.8, "onsite": 1.0, "unknown": 0.5, "remote_or_onsite": 1.0 }
        }

        # Full names of the 50 US states -> state code, used by score_location to
        # recognize state-level preferences such as "jobs in Texas". The bare
        # "new york" / "washington" are deliberately excluded to avoid clashing with
        # the NYC metro city "new york" and the DC metro city "washington"; users
        # must say "new york state" / "washington state" to express state-level intent.
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

    # 1. Salary score: asymmetric Gaussian decay + "highest paying" sentinel mode
    def score_salary(self, job, target_salary):
        """
        Normal mode: score = exp(-(delta / sigma)^2), with sigma=50000 above target and sigma=20000 below.

        Sentinel mode (target_salary >= 500000): when the user says something like
        "highest paying", the LLM extracts a very high target. In that case switch to
        a linear ramp (higher salary -> higher score, capped at 1.0 at 500k), and
        penalize jobs with missing salary to 0.0 instead of the neutral 0.5 so that
        n/a jobs cannot float to the top of a high-salary query.
        """
        if not target_salary: return 1.0
        s_min = job.get("salary_min") or None  # treat 0 as missing
        s_max = job.get("salary_max") or None

        # "highest paying" semantics: a sentinel target_salary >= 500k enters "higher is better" mode
        is_highest_paying = target_salary >= 500000

        if s_min is None and s_max is None:
            # Normal mode: missing salary -> neutral 0.5; sentinel mode: missing -> 0 (cannot rank high pay without data)
            return 0.0 if is_highest_paying else 0.5

        if s_min is not None and s_max is not None:
            effective = max(s_min, min(target_salary, s_max))
        else:
            effective = s_min if s_min is not None else s_max

        if is_highest_paying:
            # Linear ramp capped at 500k; preserves the monotonic "higher pay -> higher score" semantics
            return min(effective / 500000, 1.0)

        delta = effective - target_salary
        sigma = 50000 if delta >= 0 else 20000
        return math.exp(-((delta / sigma) ** 2))

    # 2. Location score: tiered proximity scoring (with finer-grained remote tiers)
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

        # State-level preferences (full state names like "Texas" / "California") take
        # a separate branch: the user means "any city in that state is fine", so
        # score 1.0 instead of falling through to the city-level fallback of 0.1
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

            # Multi-word cities (e.g. "new orleans" / "san francisco") get split into
            # several tokens and would be missed by a plain set intersection, so add a
            # substring fallback (only for cities containing a space, so short aliases
            # like "la" do not falsely match "atlanta")
            multi_word_in_state = {c for c in in_state_cities if " " in c}
            multi_word_neighbor = {c for c in neighbor_state_cities if " " in c}

            in_state_hit = (
                target_state in geo_tokens  # e.g. "austin, tx" contains the state code
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

        # Pure remote
        if is_remote and not geo_part:
            return 0.9

        # Pure work-mode combinations like 'Remote or Onsite' / 'Remote or Hybrid': equivalent to "any mode" -> 0.9
        if is_remote and has_or and geo_tokens and \
           geo_tokens.issubset({"onsite", "hybrid", "office", "in-office"}):
            return 0.9

        # 'Remote or X' form: the user can choose remote or X, so at least 0.9; if X is in the preferred metro, 0.85
        if is_remote and has_or:
            for metro, info in self.metro_areas.items():
                cities = set(c.lower() for c in info.get("cities", []))
                if pref_loc in cities and (geo_part in cities or geo_tokens & cities):
                    return 0.85
            return 0.9

        # US-wide remote: token-level matching (so 'us' is not falsely matched as a substring of 'austin'/'houston')
        us_markers = {"us", "usa", "u.s.", "u.s.a.", "america"}
        if is_remote and (us_markers & geo_tokens or "united states" in geo_part):
            return 0.85

        # 'X - Remote' or a plain location (no ' or ')
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

    # 3. Tag score: modified Jaccard coefficient
    def score_tags(self, job_tags, desired_tags):
        if not desired_tags: return 1.0
        if not job_tags: return 0.0

        job_set = set(t.lower() for t in job_tags)
        desired_set = set(t.lower() for t in desired_tags)
        # Use the user's desired tags as the denominator; extra skills on the job are not penalized
        return len(job_set & desired_set) / len(desired_set)

    # 4. Remote-preference score
    def score_remote(self, job_remote, pref_remote):
        if not pref_remote: return 1.0
        return self.REMOTE_MATRIX.get(pref_remote, {}).get(job_remote, 0.3)

    # Combined scoring with dynamic weight normalization
    def compute_final_score(self, job, preferences, tfidf_score=None,
                            weight_adjustments=None, active_fields=None):
        """
        Compute the final score: sum(w_i * score_i) / sum(w_i)

        active_fields: None = fully automatic (fields activated based on preferences),
        or an explicit set/list restricting which fields participate (for ablation).
        The description field is no longer hard-coded as active.
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
                # argmax-aware soft scoring: classifier argmax == target -> 1.0 (hard reward);
                # argmax != target -> the cosine for the target class (so "misclassified
                # but close" jobs still get partial credit). This stays consistent with
                # the no-hard-filter stance while avoiding the overall score depression
                # that using raw cosine directly would cause.
                if max(cat_scores, key=cat_scores.get) == target_cat:
                    scores["category"] = 1.0
                else:
                    scores["category"] = float(cat_scores.get(target_cat, 0.0))
            else:
                # Fallback: hard match
                scores["category"] = 1.0 if job.get("category") == target_cat else 0.0

        # Apply the LLM-extracted weight adjustments
        weights = self.DEFAULT_WEIGHTS.copy()
        if weight_adjustments:
            for field, level in weight_adjustments.items():
                if field not in weights:
                    continue
                if level == "high": weights[field] *= 2.0
                elif level == "low": weights[field] *= 0.5

        # Dynamic weight normalization: sum only the weights of active fields
        active_weights = {k: weights[k] for k in scores.keys()}
        w_sum = sum(active_weights.values())

        if w_sum == 0: return 0.0, scores
        final_score = sum(scores[k] * active_weights[k] for k in scores) / w_sum

        return round(float(final_score), 4), scores