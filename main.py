from pathlib import Path
import os
import re
import sqlite3
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "knowledge_base"
DB_PATH = BASE_DIR / "data" / "smartassist.db"

app = FastAPI(title="SmartAssist AI Chatbot")

# ---------- Database ----------
def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            rating INTEGER,
            comment TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    con.close()

init_db()

def save_message(session_id: str, role: str, message: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO messages(session_id, role, message) VALUES (?, ?, ?)",
        (session_id, role, message)
    )
    con.commit()
    con.close()

def get_history(session_id: str, limit: int = 8):
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT role, message FROM messages WHERE session_id=? "
        "ORDER BY id DESC LIMIT ?", (session_id, limit)
    ).fetchall()
    con.close()
    return list(reversed(rows))

# ---------- Knowledge Base / RAG ----------
def load_articles():
    articles = []
    for path in sorted(KB_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = path.stem.replace("_", " ").title()
        articles.append({"title": title, "text": text})
    return articles

ARTICLES = load_articles()

def retrieve(query: str, k: int = 3):
    """Small dependency-free retrieval layer using word overlap.
    It is intentionally simple so the project is easy to run.
    You can upgrade this function to ChromaDB + sentence-transformers later.
    """
    q_words = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
    scored = []
    for item in ARTICLES:
        words = set(re.findall(r"[a-zA-Z0-9]+", item["text"].lower()))
        score = len(q_words & words) / max(len(q_words), 1)
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in scored[:k] if score > 0]

# ---------- Intent ----------
def classify_intent(text: str):
    t = text.lower()
    if any(x in t for x in ["hello", "hi", "hey", "good morning", "good evening"]):
        return "greeting"
    if any(x in t for x in ["refund", "return", "money back"]):
        return "refund"
    if any(x in t for x in ["password", "login", "sign in", "account locked"]):
        return "account"
    if any(x in t for x in ["technical", "bug", "error", "not working", "crash"]):
        return "technical"
    if any(x in t for x in ["complaint", "angry", "bad service", "frustrated"]):
        return "complaint"
    if any(x in t for x in ["human", "agent", "representative", "support person"]):
        return "escalation"
    return "faq"

def needs_escalation(text: str, intent: str, retrieved_count: int):
    t = text.lower()
    frustration = any(x in t for x in [
        "very angry", "extremely frustrated", "worst service",
        "nobody is helping", "speak to a human", "human agent"
    ])
    return intent == "escalation" or frustration or retrieved_count == 0

# ---------- LLM ----------
def generate_llm_answer(question: str, context: str, history):
    api_key = os.getenv("OPENAI_API_KEY")
    if OpenAI is None or not api_key:
        return None

    client = OpenAI(api_key=api_key)
    messages = [{
        "role": "system",
        "content": (
            "You are SmartAssist, a polite customer support assistant. "
            "Use the supplied knowledge base context when relevant. "
            "Do not invent company policies. If the context is insufficient, "
            "say so and recommend human support."
        )
    }]
    for role, msg in history:
        messages.append({"role": "user" if role == "user" else "assistant", "content": msg})
    messages.append({
        "role": "user",
        "content": f"Knowledge base:\n{context}\n\nCustomer question: {question}"
    })
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message.content

# ---------- API ----------
class ChatRequest(BaseModel):
    session_id: str = "demo"
    message: str

class FeedbackRequest(BaseModel):
    session_id: str
    rating: int
    comment: str = ""

@app.get("/")
def home():
    return FileResponse(FRONTEND_PATH)

@app.get("/history/{session_id}")
def history(session_id: str):
    return {"session_id": session_id, "messages": get_history(session_id)}

@app.post("/chat")
def chat(req: ChatRequest):
    question = req.message.strip()
    if not question:
        return {"answer": "Please enter a message.", "intent": "unknown", "escalate": False}

    intent = classify_intent(question)
    docs = retrieve(question)
    context = "\n\n".join(f"[{d['title']}]\n{d['text']}" for d in docs)
    history_rows = get_history(req.session_id)
    escalate = needs_escalation(question, intent, len(docs))

    save_message(req.session_id, "user", question)

    if intent == "greeting":
        answer = "Hello! 👋 I’m SmartAssist. How can I help you today?"
    elif escalate:
        answer = (
            "I understand this needs extra help. I can flag this conversation "
            "for a human support agent. Please keep your session ID handy: "
            f"{req.session_id}"
        )
    else:
        answer = generate_llm_answer(question, context, history_rows)
        if not answer:
            if docs:
                answer = (
                    f"Based on our help articles, here is the closest guidance:\n\n"
                    f"{docs[0]['text']}\n\n"
                    "If this does not solve the issue, you can ask for a human agent."
                )
            else:
                answer = (
                    "I couldn't find a matching help article. "
                    "Please provide a little more detail or ask for a human agent."
                )

    save_message(req.session_id, "assistant", answer)
    return {
        "answer": answer,
        "intent": intent,
        "sources": [d["title"] for d in docs],
        "escalate": escalate
    }

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    rating = max(1, min(5, req.rating))
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO feedback(session_id, rating, comment) VALUES (?, ?, ?)",
        (req.session_id, rating, req.comment)
    )
    con.commit()
    con.close()
    return {"status": "saved"}

FRONTEND_PATH = BASE_DIR / "frontend" / "index.html"
