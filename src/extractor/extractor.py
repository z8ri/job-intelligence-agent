import json
import re
import spacy
from pathlib import Path
from bs4 import BeautifulSoup


try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class JobExtractor:
    def __init__(self, user_email="jwang@jhu.edu"):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.base_dir / "data"
        
        self.metro_areas = self._load_metro_dictionary()
        self.states_map = {info["state"].lower() for info in self.metro_areas.values() if "state" in info}
        
        self.location_aliases = {"sf": "San Francisco", "nyc": "New York City", "la": "Los Angeles", "dc": "Washington DC"}
        self.common_tags = ["Python", "Java", "Go", "Rust", "React", "AWS", "Docker", "Kubernetes", "AI", "ML", "TypeScript"]
        
        self.title_keywords = ["engineer", "developer", "manager", "architect", "lead", "intern", "executive", "scientist"]
        self.title_patterns = [
            r"looking for a ([\w\s]+engineer)",
            r"hiring a ([\w\s]+developer)",
            r"seeking a ([\w\s]+engineer)",
            r"join our team as (?:a|an) ([\w\s]+)"
        ]

    def _load_metro_dictionary(self):
        dict_path = self.data_dir / "metro_areas.json"
        return json.load(open(dict_path, "r", encoding="utf-8")) if dict_path.exists() else {}

    def _extract_location_and_mode(self, text):
        text_lower = text.lower()
        physical_loc = "Unknown"
        
        for alias, standard in self.location_aliases.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                physical_loc = standard
                break
        
       
        if physical_loc == "Unknown":
            for metro_name, info in self.metro_areas.items():
                for city in info.get("cities", []):
                    if re.search(r'\b' + re.escape(city.lower()) + r'\b', text_lower):
                        physical_loc = metro_name.title()
                        break
                if physical_loc != "Unknown": break

        if physical_loc == "Unknown":
            for state in self.states_map:
                if len(state) == 2:
                    if re.search(r'\b' + re.escape(state.upper()) + r'\b', text):
                        physical_loc = state.upper()
                        break
                else:
                    if re.search(r'\b' + re.escape(state) + r'\b', text_lower):
                        physical_loc = state.upper()
                        break

        is_remote = "remote" in text_lower
        is_hybrid = "hybrid" in text_lower
        is_onsite = any(kw in text_lower for kw in ["onsite", "on-site", "in-office"])

        if is_remote and (is_onsite or physical_loc != "Unknown"):
            return f"Remote or {physical_loc}" if physical_loc != "Unknown" else "Remote or Onsite", "remote_or_onsite"
        if is_hybrid:
            return physical_loc if physical_loc != "Unknown" else "Hybrid", "hybrid"
        if is_remote:
            return "Remote", "remote"
        return physical_loc, "onsite"

    def _smart_assign(self, parts, full_text):
        location, remote = self._extract_location_and_mode(full_text)
        company = parts[0][:50] if parts else "Unknown"
        title = "Unknown"
        
        if len(parts) > 1:
            for p in parts[1:]:
                p_clean = p.strip()
                if len(p_clean.split()) > 10: continue
                if any(k in p_clean.lower() for k in self.title_keywords):
                    title = p_clean
                    break
        
        if title == "Unknown" or len(title.split()) > 8:
            snippet = full_text[:300].lower()
            for pattern in self.title_patterns:
                match = re.search(pattern, snippet)
                if match:
                    title = match.group(1).strip().title()
                    break
                    
        return company, title, location, remote

    def process_file(self, input_filename):
        input_path = self.data_dir / input_filename
        output_path = self.data_dir / "structured_jobs.json"
        
        if not input_path.exists():
            print(f"找不到文件: {input_path}")
            return

        with open(input_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        processed_list = []
        for i, raw in enumerate(raw_data):
            soup = BeautifulSoup(raw['html'], 'html.parser')
            full_text = soup.get_text(separator=' ').strip()
            
            first_line = full_text.split('\n')[0]
            parts = [p.strip() for p in re.split(r'[|;—\-]', first_line) if len(p.strip()) > 1]
            
            company, title, location, remote = self._smart_assign(parts, full_text)
            
            pattern = r'\$(\d{1,3}(?:,\d{3})*)(?:\s?k)?(?:\s?-\s?\$?(\d{1,3}(?:,\d{3})*)(?:\s?k)?)?'
            sal_match = re.search(pattern, full_text, re.IGNORECASE)
            s_min, s_max = None, None
            if sal_match:
                v1 = int(sal_match.group(1).replace(',', ''))
                s_min = v1 * 1000 if 'k' in sal_match.group(0).lower() or v1 < 1000 else v1
                if sal_match.group(2):
                    v2 = int(sal_match.group(2).replace(',', ''))
                    s_max = v2 * 1000 if 'k' in sal_match.group(0).lower() or v2 < 1000 else v2

            processed_list.append({
                "job_id": f"hn_{i}",  
                "source": "hackernews",
                "company": company,
                "title": title,
                "location": location,
                "remote": remote,
                "salary_min": s_min,
                "salary_max": s_max,
                "publish_time": raw['timestamp'],
                "tags": list(set([t for t in self.common_tags if t.lower() in full_text.lower()])),
                "description": full_text
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_list, f, indent=2, ensure_ascii=False)
        
        print(f"处理完成。共生成 {len(processed_list)} 条顺序编号的职位信息。")
        print(f"输出路径: {output_path}")

if __name__ == "__main__":
    extractor = JobExtractor()
    extractor.process_file("jobhtml.json")
