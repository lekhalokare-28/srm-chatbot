"""
Startup script — runs scraper + vector store build on first launch,
then starts the FastAPI backend.
"""
import os
import subprocess
import sys
import uvicorn

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "knowledge_base.json")
BASE = os.path.dirname(os.path.abspath(__file__))

def run(script):
    print(f"\n>>> Running {script}...")
    result = subprocess.run([sys.executable, os.path.join(BASE, script)],
                            capture_output=False)
    return result.returncode == 0

if __name__ == "__main__":
    # Only scrape if knowledge base doesn't exist yet
    if not os.path.exists(DATA_PATH):
        print("First launch — building knowledge base...")
        if not run("scraper.py"):
            print("Scraper failed. Exiting.")
            sys.exit(1)
        if not run("vectordb.py"):
            print("Vector store build failed. Exiting.")
            sys.exit(1)
        print("\nKnowledge base ready!")
    else:
        print("Knowledge base found — skipping scrape.")

    # Start FastAPI backend
    print("\nStarting SRM Chatbot backend...\n")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
