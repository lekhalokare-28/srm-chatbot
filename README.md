# SRM AI Chatbot 🎓

An intelligent AI assistant for SRMIST Kattankulathur that answers any question about the college — departments, courses, admissions, hostel, transport, placements, campus life, and more.

---

## Folder Structure

```
SRM-Chatbot/
├── scraper.py            ← scrapes SRM website
├── main.py               ← FastAPI backend
├── session.py            ← conversation memory
├── vectordb.py           ← ChromaDB knowledge base
├── scheduler.py          ← auto-updates knowledge base
├── start.py              ← Docker startup script
├── frontend/
│   └── index.html        ← chat UI
├── data/                 ← auto-created by scraper
├── Dockerfile            ← Docker image definition
├── docker-compose.yml    ← runs all 3 services together
├── .dockerignore
├── .env                  ← your API key goes here
├── requirements.txt      ← Python dependencies
└── README.md
```

---

## Option A — Docker Deployment (Recommended for production)

This is the easiest way for the IT team to deploy. One command runs everything.

### Prerequisites
- Docker installed (docker.com/get-started)
- Docker Compose installed

### Steps

**1. Add your Groq API key to `.env`:**
```
GROQ_API_KEY=your_groq_api_key_here
```

**2. Build and start everything:**
```bash
docker-compose up --build
```

That's it. Docker will:
- Build the container
- Run the scraper and build the knowledge base (first launch only)
- Start the backend on port 8000
- Start the frontend on port 3000
- Start the scheduler for automatic updates

**3. Open the chatbot:**
```
http://localhost:3000
```

**To run in background (production):**
```bash
docker-compose up --build -d
```

**To stop:**
```bash
docker-compose down
```

**To update the knowledge base manually:**
```bash
docker-compose restart scheduler
```

---

## Option B — Manual Setup (For local development)

### Step 1 — Get your free Groq API key
1. Go to https://console.groq.com
2. Sign up (free, no credit card)
3. Click API Keys → Create API Key
4. Copy the key

### Step 2 — Add key to .env
```
GROQ_API_KEY=your_key_here
```

### Step 3 — Create virtual environment and install dependencies
```bash
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
pip install groq schedule
```

### Step 4 — Run the scraper
```bash
python3 scraper.py
```

### Step 5 — Build vector store
```bash
python3 vectordb.py
```

### Step 6 — Start backend (Terminal 1)
```bash
python3 main.py
```

### Step 7 — Start frontend (Terminal 2)
```bash
python3 -m http.server 3000
```

### Step 8 — Open chatbot
```
http://localhost:3000
```

### Step 9 — Start scheduler (Terminal 3, optional)
```bash
python3 scheduler.py
```

---

## Embedding into SRM Website

Once deployed on SRM's server, add this one line to any page on srmist.edu.in:

```html
<script>
  (function() {
    var iframe = document.createElement('iframe');
    iframe.src = 'https://your-server-url:3000';
    iframe.style.cssText = 'position:fixed;bottom:20px;right:20px;width:420px;height:680px;border:none;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.2);z-index:9999';
    document.body.appendChild(iframe);
  })();
</script>
```

---

## Cost Breakdown

| Component | Cost |
|---|---|
| Groq API (up to 14,400 req/day) | Free |
| Hosting on SRM's own server | Free |
| External hosting (Railway/Render) | $5-10/month |
| **Total (on SRM servers)** | **$0/month** |

---

## Testing the Chatbot

| Query | Tests |
|---|---|
| "Tell me about the CSE department" | Department info + source links |
| "What about the hostel?" (after above) | Context memory |
| "What courses are in robotics?" | Course fetch + citations |
| "When does admission start?" | Admission info |
| "What departments are available?" | Clickable department cards |
| "How is campus life at SRM?" | Rich descriptive answer |

---

## How It Works

1. **Scraper** reads every public page on srmist.edu.in and saves content
2. **ChromaDB** stores content as searchable vector embeddings
3. **FastAPI backend** receives questions, searches knowledge base, sends to Groq
4. **Groq (Llama 3.1)** generates natural, cited answers
5. **Session memory** tracks department context across the conversation
6. **Scheduler** re-scrapes the website daily to stay current

---

Built with: Python · FastAPI · ChromaDB · Groq (Llama 3.1) · Nginx · Docker
