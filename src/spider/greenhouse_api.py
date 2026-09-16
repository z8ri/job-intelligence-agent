import requests
import json
import re
import time
from pathlib import Path
from bs4 import BeautifulSoup

class GreenhouseSpider:
    def __init__(self, user_email="contact@example.com"):
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.output_file = self.data_dir / "structured_jobs.json"

        self.user_agent = f"JobIR-Bot/1.0 (research crawler; contact: {user_email})"

        self.company_slugs = ["openai", "github", "airbnb", "discord", "figma"]
        
        self.common_tags = [
            "Python", "Java", "Go", "Rust", "React", "AWS", "Docker", 
            "Kubernetes", "AI", "ML", "PostgreSQL", "TypeScript", "C++"
        ]

    def _extract_salary(self, text):
        pattern = r'\$(\d{1,3}(?:,\d{3})*)(?:\s?k)?(?:\s?-\s?\$?(\d{1,3}(?:,\d{3})*)(?:\s?k)?)?'
        match = re.search(pattern, text, re.IGNORECASE)
        s_min, s_max = None, None
        if match:
            v1 = int(match.group(1).replace(',', ''))
            s_min = v1 * 1000 if 'k' in match.group(0).lower() or v1 < 1000 else v1
            if match.group(2):
                v2 = int(match.group(2).replace(',', ''))
                s_max = v2 * 1000 if 'k' in match.group(0).lower() or v2 < 1000 else v2
        return s_min, s_max

    def _extract_remote(self, text, location_name):
        combined = (location_name + " " + text).lower()
        if "hybrid" in combined:
            return "hybrid"
        if "remote" in combined:
            return "remote"
        return "onsite"

    def fetch_jobs(self):
        all_new_jobs = []

        for slug in self.company_slugs:
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
            print(f"正在从 Greenhouse 获取 {slug.upper()} 的职位...")

            response = self._get_with_retry(api_url)
            if response is None:
                continue

            try:
                data = response.json()
                jobs = data.get("jobs", [])

                for job in jobs:
                    soup = BeautifulSoup(job.get("content", ""), 'html.parser')
                    description = soup.get_text(separator=' ').strip()

                    s_min, s_max = self._extract_salary(description)
                    location = job.get("location", {}).get("name", "Unknown")

                    structured_job = {
                        "job_id": f"gh_{job['id']}",
                        "source": "greenhouse",
                        "company": slug.upper(),
                        "title": job.get("title"),
                        "location": location,
                        "remote": self._extract_remote(description, location),
                        "salary_min": s_min,
                        "salary_max": s_max,
                        "publish_time": job.get("updated_at"),
                        "tags": [t for t in self.common_tags if t.lower() in description.lower() or t.lower() in job.get("title", "").lower()],
                        "description": description
                    }
                    all_new_jobs.append(structured_job)

            except (ValueError, KeyError) as e:
                print(f"解析 {slug} 响应时出错: {e}")

            time.sleep(1.5)

        self._append_to_json(all_new_jobs)

    def _get_with_retry(self, url, max_retries=3):
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=15)
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (429, 500, 502, 503, 504):
                    backoff = 2 ** attempt
                    print(f"  HTTP {resp.status_code}，{backoff}s 后重试 ({attempt+1}/{max_retries})")
                    time.sleep(backoff)
                    continue
                print(f"  HTTP {resp.status_code}，跳过 {url}")
                return None
            except requests.RequestException as e:
                backoff = 2 ** attempt
                print(f"  网络错误: {e}，{backoff}s 后重试 ({attempt+1}/{max_retries})")
                time.sleep(backoff)
        print(f"  {max_retries} 次重试后仍失败")
        return None

    def _append_to_json(self, new_jobs):
        existing_data = []
        if self.output_file.exists():
            with open(self.output_file, "r", encoding="utf-8") as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []

        combined_data = existing_data + new_jobs
        
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=4, ensure_ascii=False)
        
        print(f"成功获取 {len(new_jobs)} 条通用科技公司职位，已追加至 {self.output_file}。")

if __name__ == "__main__":
    spider = GreenhouseSpider()
    spider.fetch_jobs()
