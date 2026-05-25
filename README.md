# ✂️ BarberSQL — Natural Language to SQL Assistant

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green.svg)](https://fastapi.tiangolo.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-blue.svg)](https://www.mysql.com/)
[![Gradio](https://img.shields.io/badge/Gradio-6.14-orange.svg)](https://gradio.app/)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

BarberSQL is a production-grade natural language interface designed specifically for a barber shop booking database, enabling staff to query and modify appointments using intuitive conversational English. This repository stands as a portfolio-worthy demonstration of building safe, robust, and highly observable AI database agents through strict SQL validation, natural language fallback gates, and multi-provider LLM failover.

---

## 🚀 Quick Example

```text
User Types:      "Add appointment for Rahul tomorrow at 5 PM"

Generated SQL:   INSERT INTO appointments (customer_id, appointment_date, appointment_time, status)
                 SELECT id, '2026-05-25', '17:00:00', 'scheduled'
                 FROM customers WHERE name = 'Rahul';

UI Response:     "Appointment booked for Rahul on 2026-05-25 at 17:00:00."
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | FastAPI + Python 3.11 | High-performance REST API, lifespan context routing, and pipeline orchestration |
| **Frontend** | Gradio + Custom CSS | Premium, production-grade SaaS responsive chat UI with structured session analytics |
| **Database** | MySQL 8.0 | Relational booking database storage with fully normalized schema mappings |
| **Primary LLM** | OpenRouter (Free Tier) | Advanced natural-language-to-SQL generation using `meta-llama/llama-3.3-70b-instruct:free` |
| **Fallback LLM** | Groq (Free Tier) | High-speed inference failover layer utilising `llama-3.3-70b-versatile` |
| **NLP Engine** | Rule-based parser + `dateparser` | Robust keyword intent routing and precise temporal relative name/date/time extraction |
| **Safety Engine** | Custom SQL Validator | 8-tiered active security parser that blocks unauthorized or destructive database mutations |

---

## 📋 Prerequisites

Before running the application locally, ensure you have the following:
* **Python 3.11+** installed on your system.
* **MySQL 8.0** server active and accessible.
* **OpenRouter API Key** (Obtain a free account at [openrouter.ai](https://openrouter.ai/)).
* **Groq API Key** (Obtain a free developer account at [console.groq.com](https://console.groq.com/)).

---

## 💻 Quick Start (Local)

1. **Clone the Repository and Navigate to Root**:
   ```bash
   git clone <repo-url>
   cd barbersql
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy the example environment file and fill in your actual credentials and API keys:
   ```bash
   cp .env.example .env
   ```

4. **Initialize MySQL Database Schema**:
   Open MySQL Workbench or your favorite CLI client and run `sql/schema.sql`:
   ```bash
   mysql -u root -p < sql/schema.sql
   ```

5. **Start the FastAPI Backend**:
   ```bash
   uvicorn backend.main:app --reload
   ```
   * The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

6. **Start the Gradio Web Frontend**:
   ```bash
   python frontend/app.py
   ```
   * Access the dashboard interface at [http://localhost:7860](http://localhost:7860).

---

## 🐳 Quick Start (Docker)

Spin up the entire stack (FastAPI Backend, Gradio UI Dashboard, and MySQL Database) with a single command:

```bash
docker compose up --build
```

* **FastAPI Backend REST API**: [http://localhost:8000](http://localhost:8000)
* **Gradio AI Assistant Dashboard**: [http://localhost:7860](http://localhost:7860)

---

## 💡 Example Queries

| Intent | Example Query |
| :--- | :--- |
| **SELECT** | *Show all appointments for today* |
| **SELECT** | *How many appointments this week?* |
| **INSERT** | *Add appointment for Rahul tomorrow at 5 PM* |
| **INSERT** | *Book Priya for a haircut on Friday at 3 PM* |
| **UPDATE** | *Update Ravi's appointment to 7 PM* |
| **UPDATE** | *Reschedule Karthik to next Monday* |
| **DELETE** | *Cancel Anitha's appointment* |
| **DELETE** | *Remove all cancelled bookings* |
| **SELECT** | *List all barbers* |
| **SELECT** | *Show completed appointments this month* |

---

## 📁 Project Structure

```text
barbersql/
├── backend/                       # Backend FastAPI service code
│   ├── config.py                  # Pydantic configuration settings and environment variables
│   ├── database/                  # Database connectivity and execution layers
│   │   ├── connection.py          # MySQL async connection pool manager
│   │   ├── executor.py            # Async connection execution interface
│   │   └── schema_loader.py       # Table metadata schema introspection engine
│   ├── llm/                       # LLM service integrations and prompting templates
│   │   ├── client.py              # LLM dispatcher and fallback orchestrator
│   │   ├── groq_client.py         # Groq REST API async connection handler
│   │   ├── openrouter_client.py   # OpenRouter REST API async connection handler
│   │   └── prompt_builder.py      # Semantic prompt compiler
│   ├── middleware/                # FastAPI Starlette standard middlewares
│   │   ├── error_handler.py       # Global exception filters and API error wrappers
│   │   └── logger.py              # Observability pipeline terminal console logger
│   ├── nlp/                       # Natural Language Processing algorithms
│   │   ├── entity_extractor.py    # Name, date, time and status regex extractor
│   │   └── intent_classifier.py   # Intent mapping and query router
│   ├── response/                  # Natural UX feedback formatter
│   │   └── formatter.py           # Relational tabular response formatters
│   ├── routers/                   # API routing endpoints
│   │   └── query.py               # Main Query pipelines and health-checks
│   └── main.py                    # Application lifespans and route controllers
├── docker/                        # Containerization files
│   └── Dockerfile                 # Multi-staged backend build
├── frontend/                      # Gradio web frontend code
│   ├── static/                    # Layout configurations
│   │   └── style.css              # Custom SaaS design styling and system variables
│   └── app.py                     # Gradio block layouts and session metrics analytics tabs
├── prompts/                       # External structured raw prompts
├── sql/                           # Local database schemas
│   └── schema.sql                 # MySQL barber booking relational schema
├── tests/                         # Pytest test suites
│   ├── test_integration.py        # End-to-end API integration tests
│   ├── test_nlp.py                # NLP parser unit tests
│   └── test_validator.py          # Safety SQL validator unit tests
├── demo.py                        # Observability playground dry-run script
├── docker-compose.yml             # Docker compose container orchestration config
└── requirements.txt               # Locked dependency list
```

---

## 🤖 LLM Model Guide (OpenRouter Free)

| Model | Quality for SQL | Speed | Recommendation |
| :--- | :---: | :---: | :--- |
| `meta-llama/llama-3.3-70b-instruct:free` | ★★★★★ | Medium | **Recommended Default**: High reasoning and exact column layout matches. |
| `deepseek/deepseek-coder` | ★★★★★ | Medium | **SQL Powerhouse**: Extremely precise code syntax parser. |
| `google/gemma-2-9b-it:free` | ★★★☆☆ | Fast | **Decent Mid-weight**: Handles simpler SELECT/INSERT pipelines. |
| `meta-llama/llama-3.1-8b-instruct:free` | ★★★☆☆ | Fastest | **Speed Demon**: Blazing-fast inference time for low latency. |

---

## 🛡️ Safety & Security Features (8 Validation Gates)

To prevent LLM hallucinations from causing database corruption or data loss, every generated SQL statement must pass through **8 sequential safety gates** before execution:

1. **Empty & Length Safeguard**: Enforces a strict maximum length constraint (`MAX_SQL_LENGTH = 2000`) and halts execution for empty queries.
2. **Structural Mutation Blocks**: Employs case-insensitive regex parsing to completely block dangerous operations (`DROP`, `TRUNCATE`, `ALTER`, `CREATE`, `GRANT`, `REVOKE`).
3. **Multi-Statement Defense**: Rejects stacked command injections by blocking queries containing multiple semicolons `;`.
4. **First Word Whitelist**: Ensures queries conform solely to DML intents by validating that the first word of the statement is strictly in the whitelist (`SELECT`, `INSERT`, `UPDATE`, `DELETE`).
5. **Unguarded Mutation Lock**: Blocks any blind `UPDATE` or `DELETE` statements that do not explicitly contain a `WHERE` clause.
6. **Strict Schema Cross-Referencing**: Extracts target tables and verifies their physical existence against the introspection database schema.
7. **Semantic Intent Synchronization**: Validates that the generated SQL execution matches the intent mapped by the NLP classification layer (e.g. preventing an INSERT intent from generating a SELECT SQL).
8. **Entity Column Validation**: Introspects table structures to ensure that every target column queried physically exists, protecting database engines from compilation-time crashes.

---

## 📊 Observable Logger Output Format

All operations are piped through the unified `PipelineLogger`, outputting gorgeous, structured, human-readable terminal prints:

```text
────────────────────────────────────────────────────
 BarberSQL  |  session: a3f8e2b1
────────────────────────────────────────────────────
09:14:22 ✓ [OK        ] Database connected
09:14:22 → [STAGE     ] ▶ ingestion started
09:14:23   [STEP      ] ⏱ Model inference...
09:14:24 ✓ [OK        ] ⏱ Model inference completed in 1.24s
09:14:24 ✓ [RESULT    ] Classification: POSITIVE · confidence=91%
09:14:24 ⇆ [API       ] POST openrouter.ai · 200 · 1.42s
09:14:24 ◉ [DB        ] SELECT · appointments · 12 rows · 0.030s
09:14:24 ✓ [DONE      ] Complete · elapsed=2.1s ok=4 warn=0 err=0
────────────────────────────────────────────────────
```

---

## 🧪 Running Tests

A complete suite of 30 unit and integration tests is included. To execute the tests in verbose mode, make sure your virtual environment is active and run:

```bash
pytest tests/ -v
```

Tests verify:
- **Safety Validator**: Validates all 8 safety gates, DML restrictions, and SQL sanitizations.
- **NLP Engine**: Assures intent classifications, time format mappings, relative dates, and entity extractions.
- **FastAPI Integration**: Confirms end-to-end endpoint logic, response schemas, and router handling under mock settings.

---

## 📅 Roadmap & Phases

* **Phase 1**: Foundational setup including database schema creation, server skeletons, configuration loaders, and third-party API client wrappers.
* **Phase 2**: Core pipeline implementation covering intent classification, entity extraction, safety validator gates, and connection executor pooling.
* **Phase 3**: Premium Gradio user interface engineering loaded with dynamic example handlers, session history tracking, and custom CSS branding.
* **Phase 4**: Production-grade deployment consisting of full Docker container orchestration, complete unit/integration test coverage, and comprehensive developer documentation.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.
