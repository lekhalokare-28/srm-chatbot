import schedule
import time
import subprocess
import sys
import os
from datetime import datetime

# Path to scripts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER  = os.path.join(BASE_DIR, "scraper.py")
VECTORDB = os.path.join(BASE_DIR, "vectordb.py")


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def refresh_knowledge_base():
    log("Starting knowledge base refresh...")

    # Step 1 — Scrape website
    log("Step 1/2 — Scraping SRMIST website...")
    result = subprocess.run([sys.executable, SCRAPER], capture_output=True, text=True)
    if result.returncode == 0:
        log("Scraping complete.")
    else:
        log(f"Scraping failed: {result.stderr}")
        return

    # Step 2 — Rebuild vector store
    log("Step 2/2 — Rebuilding vector store...")
    result = subprocess.run([sys.executable, VECTORDB], capture_output=True, text=True)
    if result.returncode == 0:
        log("Vector store rebuilt successfully.")
    else:
        log(f"Vector store rebuild failed: {result.stderr}")
        return

    log("Knowledge base is up to date!")
    log("-" * 50)


# Schedule jobs
schedule.every(7).days.do(refresh_knowledge_base)       # full refresh weekly
schedule.every(1).days.at("06:00").do(refresh_knowledge_base)  # daily at 6am for events/news

if __name__ == "__main__":
    log("SRM Chatbot Scheduler Started")
    log("Schedule: Daily at 6:00 AM + every 7 days")
    log("-" * 50)

    # Run once immediately on start
    refresh_knowledge_base()

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # check every minute