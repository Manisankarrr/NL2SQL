# BarberSQL Setup Guide

## 1. OpenRouter Free API (Primary LLM)
What it is: A single API gateway giving access to 100+ models, many completely free.

**Step 1:** Go to https://openrouter.ai → Sign In → create account (no credit card required)
**Step 2:** Top-right menu → API Keys → Create Key → copy (starts with `sk-or-`)
**Step 3:** Set in `.env`:
```env
OPENROUTER_API_KEY=sk-or-xxxx
LLM_PROVIDER=openrouter
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

**Free models table** (models with `:free` suffix have no cost per token):

| Model ID | Best for | Notes |
| :--- | :--- | :--- |
| `meta-llama/llama-3.3-70b-instruct:free` | SQL generation + reasoning | Start here |
| `deepseek/deepseek-coder` | Pure SQL | Excellent for structured queries |
| `google/gemma-2-9b-it:free` | Fast responses | Good for simple SELECTs |
| `meta-llama/llama-3.1-8b-instruct:free` | Speed | Lower accuracy on complex SQL |

*Rate limits on free tier:* ~20 requests/minute on free models — more than enough for development.
Monitor usage: https://openrouter.ai/activity

## 2. Groq Free API (Automatic Fallback)
What it is: An ultra-fast inference API with a generous free tier.

**Step 1:** Go to https://console.groq.com → Sign up free
**Step 2:** API Keys → Create new API key → copy (starts with `gsk_`)
**Step 3:** Set in `.env`: `GROQ_API_KEY=gsk_xxxx`

The system uses Groq automatically if OpenRouter fails — no extra config needed.

**Groq free models table:**

| Model | Speed | Quality | Notes |
| :--- | :--- | :--- | :--- |
| `llama-3.3-70b-versatile` | Fast | ★★★★★ | Default fallback |
| `llama-3.1-8b-instant` | Instant | ★★★☆☆ | When speed is critical |
| `mixtral-8x7b-32768` | Fast | ★★★★☆ | Good balance |

## 3. MySQL Local Setup

### Understanding the connection
MySQL Workbench is a GUI for your local MySQL server.
Your FastAPI backend and MySQL Workbench connect to the exact same server (`localhost:3306`) with the same credentials.
They share the same database — changes made by FastAPI are immediately visible in Workbench and vice versa.

```text
  MySQL Workbench ──┐
                    ├── MySQL Server (localhost:3306) ← same engine
  FastAPI backend ──┘
```

**Via MySQL Workbench (recommended for beginners):**
1. Open MySQL Workbench → connect to Local instance
2. File → Open SQL Script → select `sql/schema.sql`
3. Click Execute (lightning bolt icon or Ctrl+Shift+Enter)
4. Refresh Schemas panel → `barbershop` database appears with 4 tables

**Via command line:**
```bash
mysql -u root -p < sql/schema.sql
mysql -u root -p barbershopsql -e "SELECT COUNT(*) FROM appointments;"
```

**.env values that match Workbench:**
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=<same password as your Workbench connection>
DB_NAME=barbershop
```

## 4. Complete `.env` Reference

```env
# Database Configuration
DB_HOST=localhost            # Hostname of the MySQL server (use 'mysql' if running via Docker Compose)
DB_PORT=3306                 # Port for MySQL connection
DB_USER=root                 # MySQL username
DB_PASSWORD=your_password    # MySQL password
DB_NAME=barbershop           # Target database name

# Primary LLM (OpenRouter)
LLM_PROVIDER=openrouter      # Defines the primary LLM provider
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free # Model to use on OpenRouter
OPENROUTER_API_KEY=sk-or-xxxx # API key for OpenRouter

# Fallback LLM (Groq)
GROQ_API_KEY=gsk_xxxx        # API key for Groq fallback mechanism

# Application Environment
APP_ENV=development          # Set to 'production' to disable automatic reloads
```

## 5. Running the Project

Open two terminal windows to start both services.

**Terminal 1 (Backend):**
```bash
uvicorn backend.main:app --reload
# Visit http://localhost:8000/docs to confirm API is running
```

**Terminal 2 (Frontend):**
```bash
python frontend/app.py
# Visit http://localhost:7860 for the chat interface
```

## 6. Verification Commands

Run these to quickly test individual components:

**Test DB:**
```bash
python -c "import asyncio; from backend.database.connection import create_pool; asyncio.run(create_pool()); print('DB OK')"
```

**Test OpenRouter:**
```bash
curl -s -H "Authorization: Bearer YOUR_KEY" https://openrouter.ai/api/v1/models | python3 -m json.tool | head -20
```

**Test Groq:**
```bash
python -c "from groq import Groq; c=Groq(api_key='YOUR_KEY'); print('Groq OK')"
```

**Test API:**
```bash
curl -X POST http://localhost:8000/api/query -H "Content-Type: application/json" -d '{"user_input":"show all appointments"}'
```

**Test Frontend:**
```bash
open http://localhost:7860
```
