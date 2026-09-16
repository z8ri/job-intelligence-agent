import json
import re
from pathlib import Path

class QueryExpander:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.data_path = self.base_dir / "data" / "synonyms.json"
        
        raw_data = self._load_data()
        
        self.TECH_SYNONYMS = self._flatten_synonyms(raw_data)
        self.TECH_HIERARCHY = self._flatten_hierarchy(raw_data)

    def _load_data(self):
        if not self.data_path.exists():
            return {"tech": {}, "titles": {}, "locations": {}}
        with open(self.data_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _flatten_synonyms(self, data):
        flat = {}
        for cat in data.values():
            syns = cat.get("synonyms", {})
            for key, val_list in syns.items():
                flat[key.lower()] = [v.lower() for v in val_list]
                for v in val_list:
                    flat[v.lower()] = [key.lower()] + [x.lower() for x in val_list if x != v]
        return flat

    def _flatten_hierarchy(self, data):
        flat = {}
        for cat in data.values():
            hier = cat.get("hierarchy", {})
            for key, val_list in hier.items():
                flat[key.lower()] = [v.lower() for v in val_list]
        return flat

    def expand_term(self, term):
        t = term.lower().strip()
        results = {t}
        if t in self.TECH_SYNONYMS:
            results.update(self.TECH_SYNONYMS[t])
        if t in self.TECH_HIERARCHY:
            results.update(self.TECH_HIERARCHY[t])
        return list(results)

    def expand_query(self, keywords, tags):
        expanded_kw = set(keywords) if keywords else set()
        expanded_tags = set(tags) if tags else set()

        for term in list(expanded_kw):
            normalized = term.lower().strip()
            if normalized in self.TECH_SYNONYMS:
                expanded_kw.update(self.TECH_SYNONYMS[normalized])

        for tag in list(expanded_tags):
            normalized = tag.lower().strip()
            if normalized in self.TECH_SYNONYMS:
                expanded_tags.update(self.TECH_SYNONYMS[normalized])
            if normalized in self.TECH_HIERARCHY:
                expanded_tags.update(self.TECH_HIERARCHY[normalized])

        return list(expanded_kw), list(expanded_tags)

    def process_preferences(self, pref_json):
        if pref_json.get("description_keywords"):
            new_kw = []
            for kw in pref_json["description_keywords"]:
                new_kw.extend(self.expand_term(kw))
            pref_json["description_keywords"] = list(set(new_kw))

        if pref_json.get("desired_tags"):
            new_tags = []
            for tag in pref_json["desired_tags"]:
                new_tags.extend(self.expand_term(tag))
            pref_json["desired_tags"] = list(set(new_tags))

        return pref_json
