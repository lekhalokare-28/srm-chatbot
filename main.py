from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from groq import Groq
import os
import re
from dotenv import load_dotenv

from session import create_session, get_session, update_session, rewrite_query
from vectordb import search

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are an AI assistant for SRM Institute of Science
and Technology (SRMIST), Kattankulathur campus.

Your knowledge is LIMITED to information available in the provided
SRMIST website context.

Your job is to answer the student's question accurately, briefly,
and directly.

Rules:

1. Answer ONLY what the student asked.
2. Use ONLY the information provided in the SRMIST website context.
3. Do not add unrelated information from other retrieved documents.
4. Do not make up facts, links, names, numbers, dates, or details.
5. Keep simple answers to 1-3 sentences.
6. Use bullet points only when listing multiple items.
7. Give longer answers only when the student specifically asks for
   detailed information.
8. Do not repeat information.
9. Do not mention achievements, departments, clubs, facilities, or
   other topics unless they are relevant to the question.
10. If the requested information is not present in the provided
    context, say that the information could not be found on the
    SRMIST website.
11. Do not generate or modify source URLs. Official source links
    will be provided separately by the application.
12. For follow-up questions, use the conversation history to
    understand what the student is referring to.
"""


app = FastAPI(title="SRM Chatbot API")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODELS
# ============================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    department_context: Optional[str] = None
    rewritten_query: Optional[str] = None


# ============================================================
# GREETING HANDLER
# ============================================================

def is_greeting(message: str) -> bool:
    """
    Detect simple greetings so they do not trigger RAG.
    """

    cleaned = message.lower().strip()

    # Remove punctuation
    cleaned = re.sub(r"[!?.,]+$", "", cleaned)

    greetings = {
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "heyy",
        "helo",
        "good morning",
        "good afternoon",
        "good evening",
    }

    return cleaned in greetings


def get_greeting_response(message: str) -> str:
    """
    Return a short response for greetings.
    """

    cleaned = message.lower().strip()

    if "good morning" in cleaned:
        return "Good morning! ☀️ How can I help you with SRMIST?"

    if "good afternoon" in cleaned:
        return "Good afternoon! 😊 How can I help you with SRMIST?"

    if "good evening" in cleaned:
        return "Good evening! 🌙 How can I help you with SRMIST?"

    return "Hi! 👋 How can I help you with SRMIST?"


# ============================================================
# SOURCE HANDLER
# ============================================================

def format_sources(kb_results):
    """
    Extract official source URLs from retrieved documents.

    The URL comes directly from the scraped data instead of
    allowing the LLM to invent or modify it.
    """

    sources = []

    for result in kb_results:
        source_url = result.get("source_url")

        if not source_url:
            continue

        if source_url in [source["url"] for source in sources]:
            continue

        # Use source title if your vectordb provides it.
        title = (
            result.get("source_title")
            or result.get("title")
            or "Official SRMIST Source"
        )

        sources.append({
            "title": title,
            "url": source_url
        })

    return sources


def append_sources(reply: str, sources):
    """
    Add official source links to the response.

    We keep this outside the LLM so that the URLs always come
    directly from the scraped SRMIST website.
    """

    if not sources:
        return reply

    source_text = "\n\n📎 **Official Source:**"

    # Limit the number of displayed sources.
    # This prevents dumping many unrelated links.
    for source in sources[:2]:
        source_text += f"\n- [{source['title']}]({source['url']})"

    return reply.strip() + source_text


# ============================================================
# CHAT ENDPOINT
# ============================================================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    original_query = request.message.strip()

    if not original_query:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    # --------------------------------------------------------
    # SESSION
    # --------------------------------------------------------

    session_id = request.session_id or create_session()

    session = get_session(session_id)

    if not session:
        session_id = create_session()
        session = get_session(session_id)

    # --------------------------------------------------------
    # GREETING CHECK
    # --------------------------------------------------------
    # IMPORTANT:
    # Greetings should NOT go through RAG.
    # --------------------------------------------------------

    if is_greeting(original_query):

        reply = get_greeting_response(original_query)

        update_session(
            session_id,
            original_query,
            reply
        )

        return ChatResponse(
            reply=reply,
            session_id=session_id,
            department_context=session.get("department"),
            rewritten_query=None
        )

    # --------------------------------------------------------
    # QUERY REWRITING
    # --------------------------------------------------------

    enriched_query = rewrite_query(
        original_query,
        session
    )

    # --------------------------------------------------------
    # VECTOR SEARCH
    # --------------------------------------------------------
    # Reduced from 5 to 3 to avoid unnecessary context.
    # --------------------------------------------------------

    kb_results = search(
        enriched_query,
        n_results=3
    )

    # --------------------------------------------------------
    # HANDLE NO RESULTS
    # --------------------------------------------------------

    if not kb_results:

        reply = (
            "I couldn't find that information on the "
            "SRMIST website."
        )

        update_session(
            session_id,
            original_query,
            reply
        )

        return ChatResponse(
            reply=reply,
            session_id=session_id,
            department_context=session.get("department"),
            rewritten_query=(
                enriched_query
                if enriched_query != original_query
                else None
            )
        )

    # --------------------------------------------------------
    # BUILD CONTEXT
    # --------------------------------------------------------

    context_parts = []

    for i, result in enumerate(kb_results, start=1):

        content = result.get("content", "").strip()

        if not content:
            continue

        context_parts.append(
            f"""--- Retrieved Information {i} ---

{content}
"""
        )

    context_text = "\n".join(context_parts)

    # --------------------------------------------------------
    # SOURCE INFORMATION
    # --------------------------------------------------------

    sources = format_sources(kb_results)

    # --------------------------------------------------------
    # AUGMENTED USER MESSAGE
    # --------------------------------------------------------

    augmented_message = f"""Student question:
{original_query}

Relevant information retrieved from the official SRMIST website:

{context_text}

IMPORTANT:
- Answer only the student's question.
- Ignore retrieved information that is unrelated to the question.
- Do not provide a summary of all retrieved information.
- Do not invent information that is not present in the context.
- Keep the answer concise and direct.
"""

    # --------------------------------------------------------
    # BUILD GROQ MESSAGE HISTORY
    # --------------------------------------------------------

    all_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    # Last 10 conversation messages
    for msg in session["messages"][-10:]:

        role = (
            "assistant"
            if msg["role"] == "assistant"
            else "user"
        )

        all_messages.append({
            "role": role,
            "content": msg["content"]
        })

    # Current question
    all_messages.append({
        "role": "user",
        "content": augmented_message
    })

    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=all_messages,
            max_tokens=500,
            temperature=0.3,
        )

        reply = response.choices[0].message.content.strip()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Groq API error: {str(e)}"
        )

    # --------------------------------------------------------
    # ADD OFFICIAL SOURCES
    # --------------------------------------------------------

    reply = append_sources(
        reply,
        sources
    )

    # --------------------------------------------------------
    # UPDATE SESSION
    # --------------------------------------------------------

    update_session(
        session_id,
        original_query,
        reply
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        department_context=session.get("department"),
        rewritten_query=(
            enriched_query
            if enriched_query != original_query
            else None
        )
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "message": "SRM Chatbot is running"
    }


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )