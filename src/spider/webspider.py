import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.robotparser import RobotFileParser

class HNJobSpider:
    def __init__(self, thread_ids, user_email="contact@example.com"):
        self.thread_ids = thread_ids
        self.base_url = "https://news.ycombinator.com/"
        self.user_agent = f"JobIR-Bot/1.0 (research crawler; contact: {user_email})"
        
        self.job_results = []
        
        self.data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.rp = RobotFileParser()
        self.rp.set_url(f"{self.base_url}robots.txt")
        try:
            self.rp.read()
        except:
            pass

    def scrape(self):
        for t_id in self.thread_ids:
            start_url = f"{self.base_url}item?id={t_id}"
            print(f"\nCollecting jobs from thread ID: {t_id}")
            self._process_page(start_url)
            time.sleep(5)
            
        self._save()

    def _process_page(self, url):
        print(f"Scanning page: {url}")
        if not self.rp.can_fetch(self.user_agent, url):
            print(f"  Disallowed by robots.txt, skipping: {url}")
            return

        resp = self._get_with_retry(url)
        if resp is None:
            return

        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.find_all('tr', class_='athing comtr')
        page_count = 0

        for row in rows:
            indent_img = row.find('img', src='s.gif')
            if not indent_img or int(indent_img.get('width', 0)) != 0:
                continue

            commtext = row.find('div', class_='commtext')
            age_span = row.find('span', class_='age')
            raw_time_str = age_span.get('title') if age_span else "Unknown"

            if raw_time_str != "Unknown" and " " in raw_time_str:
                post_time = raw_time_str.split(" ")[0]
            else:
                post_time = raw_time_str

            if commtext:
                job_entry = {
                    "url": url,
                    "html": str(commtext),
                    "timestamp": post_time
                }
                self.job_results.append(job_entry)
                page_count += 1

        print(f"  Extracted {page_count} distinct jobs from this page.")

        more_tag = soup.select_one('a.morelink')
        if more_tag:
            next_page = self.base_url + more_tag['href']
            time.sleep(1.5)
            self._process_page(next_page)

    def _get_with_retry(self, url, max_retries=3):
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=15)
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (429, 500, 502, 503, 504):
                    backoff = 2 ** attempt
                    print(f"  HTTP {resp.status_code}, retrying in {backoff}s ({attempt+1}/{max_retries})")
                    time.sleep(backoff)
                    continue
                print(f"  HTTP {resp.status_code}, skipping")
                return None
            except requests.RequestException as e:
                backoff = 2 ** attempt
                print(f"  Network error: {e}, retrying in {backoff}s ({attempt+1}/{max_retries})")
                time.sleep(backoff)
        print(f"  Still failing after {max_retries} retries")
        return None

    def _save(self):
        filename = f"jobhtml.json"
        save_path = self.data_dir / filename
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.job_results, f, indent=2, ensure_ascii=False)
        print(f"\nCrawl finished.")
        print(f"Total distinct jobs: {len(self.job_results)}")
        print(f"Saved to: {save_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="HackerNews 'Who is Hiring' monthly-thread crawler"
    )
    parser.add_argument(
        "--months", type=int, default=6,
        help="crawl the most recent N monthly Who is Hiring threads (default 6, max 6)",
    )
    args = parser.parse_args()

    # Most recent thread first; HN item ids increase monotonically, so the list is descending
    MONTHLY_THREAD_IDS = [
        "47601859", "47219668", "46857488",
        "46466074", "46108941", "45800465",
    ]
    n = max(1, min(args.months, len(MONTHLY_THREAD_IDS)))
    if n != args.months:
        print(f"--months {args.months} is outside the available thread range, falling back to {n}")

    selected = MONTHLY_THREAD_IDS[:n]
    spider = HNJobSpider(thread_ids=selected)
    spider.scrape()
