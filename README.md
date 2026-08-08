# SmartAssist — AI-Powered Customer Support Chatbot

A beginner-friendly Artificial Intelligence internship project based on the supplied project brief.

## Features

- Natural-language customer support chat
- Intent classification using simple NLP/rules
- Knowledge-base retrieval (RAG-style flow)
- Optional OpenAI LLM response generation
- SQLite conversation history
- Human escalation logic
- Feedback API
- Simple HTML/CSS/JavaScript web interface
- FastAPI backend

## Project flow

User Input → Preprocessor → Intent Classifier → Knowledge Retriever → LLM Generator → Response

## Tech stack

- Python 3.11+
- FastAPI
- SQLite
- OpenAI API (optional)
- HTML/CSS/JavaScript
- Markdown knowledge base

## Run locally on Windows

1. Install Python 3.11 or newer.
2. Open Command Prompt/PowerShell in this project folder.
3. Create a virtual environment:

```bash
python -m venv .venv
```

4. Activate it:

```bash
.venv\Scripts\activate
```

5. Install dependencies:

```bash
pip install -r requirements.txt
```

6. Start the server:

```bash
uvicorn app.main:app --reload
```

7. Open:

http://127.0.0.1:8000

## Optional LLM setup

Copy `.env.example` to `.env` and add your API key as an environment variable.

Do not upload your real API key to GitHub.

For a simple demo without an API key, the chatbot still works using the local knowledge base.

## GitHub upload

Create a new GitHub repository named:

SmartAssist-AI-Chatbot

Then run these commands inside the project folder:

```bash
git init
git add .
git commit -m "Initial SmartAssist AI chatbot project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/SmartAssist-AI-Chatbot.git
git push -u origin main
```

Replace YOUR_USERNAME with your GitHub username.

## Viva explanation

### What is the project?
SmartAssist is an AI-powered customer support chatbot that understands common customer questions, finds relevant information from a knowledge base, remembers recent conversation messages, and can generate natural-language answers using an LLM.

### What is NLP?
Natural Language Processing helps a computer understand and process human language.

### What is RAG?
Retrieval-Augmented Generation first retrieves relevant information from a knowledge base and then uses that information to create a better answer.

### Why SQLite?
SQLite is lightweight and is useful for storing conversation history locally.

### Why FastAPI?
FastAPI provides a simple and fast Python backend with API endpoints for the chatbot.

### What happens when a user asks a question?
The backend classifies the intent, retrieves matching knowledge-base articles, checks whether escalation is needed, generates an answer, saves the conversation, and sends the result to the web interface.
