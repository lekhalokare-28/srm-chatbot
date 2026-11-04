import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import time
import os
import re
from datetime import datetime, timedelta
from collections import deque

# ── Config ──────────────────────────────────────────────
BASE_URL     = "https://www.srmist.edu.in"
MAX_PAGES    = 150
DELAY        = 1.5
MAX_CONTENT  = 8000
RECENT_DAYS  = 180

MAJOR_WIN_KEYWORDS = [
    "international", "global", "world", "worldwide",
    "gold medal", "silver medal", "bronze medal",
    "world rank", "qs ranking", "times higher education",
    "national championship", "national winner", "national rank",
    "first in india", "top in india", "best in india",
    "smart india hackathon", "sih winner",
    "championship", "won", "winner", "victory",
    "record", "milestone", "patent", "innovation award",
    "best university", "accreditation", "naac", "nba", "nirf",
    "ranked", "top 10", "top 5", "top 3", "number 1",
]

SEED_URLS = [
    "https://www.srmist.edu.in/",
    "https://www.srmist.edu.in/achievements/",
    "https://www.srmist.edu.in/news/",
    "https://www.srmist.edu.in/admissions/",
    "https://www.srmist.edu.in/admission-india/engineering/",
    "https://www.srmist.edu.in/hostel/",
    "https://www.srmist.edu.in/transport/",
    "https://www.srmist.edu.in/placements/",
    "https://www.srmist.edu.in/scholarships/",
    "https://www.srmist.edu.in/events/",
    "https://www.srmist.edu.in/research/",
    "https://www.srmist.edu.in/faculty/",
    "https://www.srmist.edu.in/programs/",
    "https://www.srmist.edu.in/innovation-incubation-center/student-clubs/",
    "https://www.srmist.edu.in/departments/",
    "https://www.srmist.edu.in/department/department-of-computing-technologies/",
    "https://www.srmist.edu.in/department/department-of-electronics-communication/",
    "https://www.srmist.edu.in/department/department-of-mechanical-engineering/",
    "https://www.srmist.edu.in/department/department-of-civil-engineering/",
    "https://www.srmist.edu.in/department/electrical-and-electronics-engineering/",
    "https://www.srmist.edu.in/department/department-of-biomedical-engineering/",
    "https://www.srmist.edu.in/department/department-of-biotechnology/",
    "https://www.srmist.edu.in/department/department-of-chemical-engineering/",
    "https://www.srmist.edu.in/department/department-of-mechatronics/",
    "https://www.srmist.edu.in/department/department-of-aerospace-engineering/",
    "https://www.srmist.edu.in/department/department-of-data-science-and-business-systems/",
    "https://www.srmist.edu.in/department/department-of-mathematics/",
    "https://www.srmist.edu.in/department/department-of-physics/",
    "https://www.srmist.edu.in/department/department-of-chemistry/",
    "https://www.srmist.edu.in/department/department-of-computer-applications/",
]

SKIP_PATTERNS = [
    "/wp-content/", "/wp-admin/", "/.well-known/",
    "/feed/", "/rss/", "/sitemap", "/cdn-cgi/",
    "/login", "/logout", "/register",
    "#", "mailto:", "tel:", "javascript:",
    ".pdf", ".jpg", ".jpeg", ".png", ".gif",
    ".zip", ".doc", ".docx", ".ppt", ".pptx",
    "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "linkedin.com", "whatsapp",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",
}


def make_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    retry = Retry(total=2, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def is_valid_url(url):
    try:
        parsed = urlparse(url)
        if "srmist.edu.in" not in parsed.netloc:
            return False
        if any(skip in url.lower() for skip in SKIP_PATTERNS):
            return False
        return True
    except:
        return False


def is_major_win(text, title=""):
    combined = (title + " " + text).lower()
    return any(kw in combined for kw in MAJOR_WIN_KEYWORDS)


def extract_date(soup, text):
    for meta in soup.find_all("meta"):
        prop = meta.get("property", "") + meta.get("name", "")
        if "date" in prop.lower():
            content = meta.get("content", "")
            try:
                return datetime.fromisoformat(content[:10])
            except:
                pass
    match = re.search(
        r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',
        text, re.IGNORECASE)
    if match:
        try:
            return datetime.strptime(match.group(0), "%d %B %Y")
        except:
            pass
    return None


def is_news_url(url):
    return any(k in url.lower() for k in ["/news/", "/achievement", "/award", "/event"])


def should_keep(url, soup, text, title):
    if not is_news_url(url):
        return True
    if is_major_win(text, title):
        return True
    date = extract_date(soup, text)
    if date:
        return date >= datetime.now() - timedelta(days=RECENT_DAYS)
    return True


def extract_links(soup, current_url):
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        full = urljoin(current_url, href).split("#")[0].rstrip("/")
        if full and is_valid_url(full):
            links.append(full)
    return list(set(links))


def scrape_page(session, url):
    try:
        r = session.get(url, timeout=15, allow_redirects=True)
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type", ""):
            return None, []

        soup = BeautifulSoup(r.text, "html.parser")
        links = extract_links(soup, url)

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg", "form"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""
        lines = [l.strip() for l in soup.get_text(separator="\n", strip=True).splitlines() if l.strip() and len(l.strip()) > 2]
        text = "\n".join(lines)

        if len(text) < 100:
            return None, links
        if not should_keep(url, soup, text, title):
            return None, links

        label = urlparse(url).path.strip("/").replace("/", "_").replace("-", "_") or "home"

        return {
            "label": label,
            "title": title,
            "url": url,
            "scraped_at": datetime.now().isoformat(),
            "content": text[:MAX_CONTENT],
            "is_major_win": is_major_win(text, title),
            "status": "success"
        }, links

    except:
        return None, []


def run_scraper():
    session = make_session()
    visited, queue, all_data = set(), deque(), []

    try:
        session.get(BASE_URL, timeout=15)
        time.sleep(2)
    except:
        pass

    for url in SEED_URLS:
        clean = url.rstrip("/")
        if clean not in visited:
            queue.appendleft(clean)

    pages = 0
    while queue and pages < MAX_PAGES:
        url = queue.popleft().rstrip("/")
        if url in visited:
            continue
        visited.add(url)

        data, links = scrape_page(session, url)
        if data:
            all_data.append(data)
            pages += 1
            for link in links:
                link = link.rstrip("/")
                if link not in visited:
                    queue.append(link)

        time.sleep(DELAY)

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "knowledge_base.json")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    major_wins = sum(1 for d in all_data if d.get("is_major_win"))
    print(f"Scraped {pages} pages | {major_wins} major wins found | Saved to {output}")


if __name__ == "__main__":
    run_scraper()