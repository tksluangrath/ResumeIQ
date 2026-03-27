# CLAUDE.md — AI-Powered Resume & Job Match Engine

## 1. Project Summary

This is an AI-powered resume and job matching platform built in Python. It ingests a resume PDF and a job description, semantically scores the match using sentence-transformers and spaCy NER, and generates a structured match report. Later phases add LaTeX resume improvement, LLM-powered suggestions, a FastAPI backend, a React frontend, and Stripe monetization. See `PROJECT_PLAN.md` for the full phase breakdown and `SETUP.md` for installation instructions.

---

## 2. Current Phase

**ACTIVE: Phase 4 — Production & Monetization**

> Update this line at the start of each new phase.

- Phase 1 (Weeks 1–2): CLI matching engine — PDF parsing, NER, semantic scoring, JSON report ✅ DONE
- Phase 1b (End Week 2): LaTeX resume improvement generator ✅ DONE
- Phase 2 (Weeks 3–4): FastAPI backend + Streamlit frontend (MVP) ✅ DONE
- Phase 3 (Weeks 5–6): LLM suggestion layer (Llama → Claude) ✅ DONE
- Phase 4 (Weeks 7–8): React frontend, Stripe, PostgreSQL, public deploy ← YOU ARE HERE
  - Track 1: PostgreSQL + JWT auth ✅ DONE
  - Track 4: Render deployment (render.yaml, Dockerfile, DATABASE_URL coercion, Alembic migration) ✅ DONE
  - Track 2: Stripe billing (next)
  - Track 3: React frontend

---

## 3. Directory Map

```
engine/          ← All NLP/ML logic lives here. No API, no UI, no DB code.
  parser.py      ← PDF → raw text (pdfplumber)
  extractor.py   ← spaCy NER pipeline (skills, titles, education)
  matcher.py     ← Sentence Transformer embeddings + cosine similarity
  scorer.py      ← Weighted scoring engine
  reporter.py    ← JSON report generation
  latex_builder.py ← LaTeX resume template population (Phase 1b)
  optimizer.py   ← Rule-based resume section rewriting (Phase 1b)
  llm/           ← LLM abstraction layer (Phase 3)
    base.py      ← Abstract interface — all LLM calls go through here
    ollama_llm.py
    claude_llm.py
    openai_llm.py

api/             ← FastAPI application (Phase 2+, DO NOT BUILD IN PHASE 1)
ui/              ← Streamlit MVP (Phase 2+, DO NOT BUILD IN PHASE 1)
frontend/        ← React app (Phase 4 only)
scripts/         ← One-off data fetch scripts (USAJobs, SAM.gov)
templates/       ← Jinja2 + LaTeX templates
tests/           ← pytest test files
samples/         ← Test PDFs and job description text files
cli.py           ← CLI entry point
config.py        ← Settings via pydantic-settings + .env
```

---

## 4. Dev Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run the CLI matcher
python cli.py --resume samples/resume.pdf --job samples/job_description.txt

# Run tests
pytest tests/ -v

# Lint and format
ruff check .
black .

# Start API server (Phase 2+)
uvicorn api.main:app --reload --port 8000

# Start Streamlit UI (Phase 2+)
streamlit run ui/streamlit_app.py

# Start Ollama LLM server (Phase 3+)
ollama serve
```

---

## 5. Coding Rules

These apply to all agents and all phases:

- **Type hints everywhere.** All functions must have full Python type annotations.
- **Pydantic for all data shapes.** Any structured data passed between modules uses a Pydantic model, not a raw dict.
- **LLM access only through `engine/llm/base.py`.** Never call Ollama, Claude, or OpenAI directly from routes or UI code.
- **No hardcoded secrets.** All API keys, credentials, and config values come from `.env` via `config.py`. Never hardcode them.
- **`engine/` stays pure.** No FastAPI, Streamlit, database, or Stripe imports inside `engine/`. It must be importable standalone.
- **No premature abstractions.** Don't create helpers or utilities for one-time use. Three similar lines is better than a bad abstraction.
- **No unnecessary comments.** Only comment logic that isn't self-evident. Don't add docstrings to code you didn't change.
- **Fail loudly.** Raise explicit exceptions with clear messages. Don't silently swallow errors or return empty fallbacks.
- **Test at boundaries.** Write tests for the scorer, extractor, and matcher. Don't mock the NLP models — use real sample data in `samples/`.

---

## 6. Phase Guard — API & UI Guardrails

> **FOR ALL AGENTS: Before writing any code in `api/`, `ui/`, or `frontend/`, you MUST stop and display the following warning block. Do not write the code until the user explicitly confirms.**

```
⚠️  PHASE GUARD WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are about to write code outside the current phase boundary.

Current phase: [state the active phase from Section 2]
Requested action: [describe what you're about to write]
Target file/folder: [the file or folder you would create/edit]

This may be intentional (advancing to the next phase) or accidental
(scope creep during the current phase).

Please confirm one of the following before proceeding:
  [A] Yes, proceed — I am intentionally advancing to the next phase
  [B] Yes, proceed — this is a small exception within the current phase
  [C] No, stop — stay within the current phase boundary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The same warning applies if any agent attempts to:
- Add Stripe, PostgreSQL, or auth code before Phase 4
- Add React components before Phase 4
- Import FastAPI inside `engine/`
- Call an LLM API directly before Phase 3

---

## 7. Agent Roster

Each agent has a defined responsibility in this project. Agents should stay in their lane and defer to the appropriate agent when a task crosses into another domain.

### Core Engine Agents (Phase 1–2)
| Agent | Responsibility |
|-------|---------------|
| `python-pro` | Primary implementation agent — all Python code, async patterns, packaging |
| `nlp-engineer` | spaCy pipeline, NER entity rulers, skill extraction logic |
| `ml-engineer` | Sentence Transformer setup, embedding logic, cosine similarity, scoring weights |
| `cli-developer` | `cli.py` entry point, argparse/click setup, output formatting |
| `qa-expert` | All pytest tests in `tests/`, fixture design, sample data strategy |
| `debugger` | Diagnose PDF parsing issues, encoding bugs, model loading errors |
| `performance-engineer` | Embedding inference speed, caching strategy, model quantization options |

### API & Infrastructure Agents (Phase 2–4)
| Agent | Responsibility |
|-------|---------------|
| `api-designer` | FastAPI route design, Pydantic schemas, OpenAPI spec |
| `backend-developer` | File upload handling, async middleware, error responses |
| `postgres-pro` | PostgreSQL schema: users, scans, subscriptions tables |
| `docker-expert` | Dockerfile, docker-compose for local dev |
| `deployment-engineer` | Render/Railway config, environment variable management, deploy pipelines |
| `security-engineer` | JWT auth, input sanitization, secrets management, rate limiting |

### LLM & AI Agents (Phase 3)
| Agent | Responsibility |
|-------|---------------|
| `llm-architect` | Abstract LLM interface design, provider swap pattern, context window management |
| `prompt-engineer` | Prompts for bullet rewrites, gap analysis, summary rewrites — test and iterate |
| `ai-engineer` | Ollama integration, response parsing, streaming support, fallback logic |

### Frontend Agent (Phase 4)
| Agent | Responsibility |
|-------|---------------|
| `react-specialist` | React + Vite frontend, component design, API integration |
| `payment-integration` | Stripe per-scan credits + subscription implementation |

### Research & Strategy Agents (Ongoing)
| Agent | Responsibility |
|-------|---------------|
| `trend-analyst` | Monitor trends in resume tech, job search tools, AI hiring — inform feature priorities |
| `market-researcher` | Competitive landscape: what tools exist, pricing, gaps we can exploit |
| `research-analyst` | Deep-dive research on specific technical or market questions |
| `data-scientist` | Analyze match score distributions, validate scoring weights, suggest model improvements |
| `data-engineer` | USAJobs + SAM.gov API scripts, bulk job fetch pipeline for testing |

### Validation Agent (Ongoing)
| Agent | Responsibility |
|-------|---------------|
| `recruiter` | Reviews resumes from a real recruiter's POV — screens against job descriptions, flags red flags and green flags, gives a hiring recommendation, calibrates the engine's scoring weights against human judgment |

### Product & Project Agents (Ongoing)
| Agent | Responsibility |
|-------|---------------|
| `product-manager` | Feature prioritization, user feedback synthesis, MVP scope decisions |
| `project-manager` | Phase tracking, milestone checklist, timeline risk flagging |
| `documentation-engineer` | Keep SETUP.md, API docs, and inline docs up to date |
| `code-reviewer` | Review completed modules before moving to the next phase |

---

## 8. Key Design Decisions

These are locked-in decisions. Agents should not suggest alternatives unless explicitly asked.

| Decision | Choice | Reason |
|----------|--------|--------|
| Embedding model | `all-MiniLM-L6-v2` | Fast, accurate, runs locally, 384-dim, no API cost |
| NLP model | `en_core_web_lg` | Includes word vectors for better NER accuracy |
| LLM (dev) | Llama via Ollama | Free, private, no cost during development |
| LLM (prod) | Claude API | Higher quality, justifies premium pricing, easy swap |
| PDF parser | `pdfplumber` | Better layout-aware extraction than PyPDF2 |
| Scoring weights | Semantic 40%, Skills 30%, Title 15%, Experience 15% | Tunable via `.env`, not hardcoded |
| Resume output | LaTeX + Jinja2 | Professional PDF quality, fully customizable |
| Frontend (MVP) | Streamlit | Fastest shareable demo, no JS required |
| Frontend (prod) | React + Vite | Polished UX for paying users |
| Database | PostgreSQL | Relational fits user + billing data, Render-hosted |
| Payments | Stripe | Industry standard, subscriptions + per-scan both supported |
| Deploy target | Render or Railway | Git-push deploy, managed Postgres, affordable |

---

## 9. Agent × Skill Parallel Execution

> **CRITICAL RULE FOR ALL AGENTS:** When you are invoked for a task, you MUST check the matrix below and load any paired skills alongside your work. Agents and skills run together — not sequentially. The skill provides best-practice context; the agent does the implementation. Both inputs shape the output simultaneously.

> **ENFORCEMENT — NO GENERAL-PURPOSE FALLBACK:** Claude must NEVER implement code directly as a general-purpose agent when a specialized agent exists in Section 7 for that task. If the task maps to an agent in the roster, that agent MUST be spawned with its paired skills. Implementing FastAPI routes, Streamlit UI, engine logic, or tests directly in the main conversation thread — without spawning the appropriate agent — is a violation of this rule.

> **MANDATORY SUPERVISION:** Every multi-agent task MUST include a `project-manager` agent as supervisor. The `project-manager` is spawned alongside the implementation agents, receives their outputs, and produces a final review summary before work is considered complete. Do not mark any task done until the `project-manager` has signed off. The supervisor does not rewrite code — it flags gaps, conflicts, and missing quality gates, and reports back to the user.

### How to Apply This

When starting any implementation task:
1. **Identify which agent(s)** from Section 7 own this work
2. **Check this matrix** for paired skills — load them simultaneously, not after
3. **Spawn a `project-manager`** alongside implementation agents to supervise and review
4. **Load and apply skill guidance** as a constraint on your implementation — treat skill rules as non-negotiable standards
5. **Produce output that satisfies both** the agent's domain expertise and the skill's best practices
6. **project-manager signs off** before the task is marked complete

If a skill contradicts a project coding rule in Section 5, **Section 5 wins**. Skills are additive, not overriding.

---

### Agent × Skill Matrix

| Agent | Paired Skills | What the Skill Adds |
|-------|--------------|---------------------|
| `python-pro` | `modern-python` | `uv`, `ruff`, type safety, `pathlib`, modern stdlib patterns |
| `nlp-engineer` | `modern-python` + `pdf` | PDF extraction patterns, modern Python NLP tooling |
| `ml-engineer` | `modern-python` | Type-safe ML code, clean notebook patterns |
| `cli-developer` | `modern-python` | CLI tooling conventions, `argparse`/`typer` patterns |
| `qa-expert` | `modern-python` | `pytest` best practices, async test patterns |
| `debugger` | `modern-python` | Trace modern Python errors, toolchain debugging |
| `performance-engineer` | `modern-python` | Profiling patterns, `uv` for fast dep resolution |
| `api-designer` | `fastapi-router-py` | Route design, schema contracts, OpenAPI structure |
| `backend-developer` | `fastapi-router-py` + `modern-python` | Async patterns, file upload, middleware, error handling |
| `security-engineer` | `fastapi-router-py` + `stripe-best-practices` | Auth patterns, webhook verification, secrets handling |
| `payment-integration` | `stripe-best-practices` | Checkout Sessions, webhooks, subscription lifecycle |
| `llm-architect` | `modern-python` | Type-safe LLM abstraction, async streaming patterns |
| `prompt-engineer` | `modern-python` | Clean prompt template patterns |
| `ai-engineer` | `modern-python` | Ollama client integration, response parsing |
| `data-engineer` | `modern-python` | Pipeline tooling, async data fetching |
| `market-researcher` | `competitor-analysis` | Structured competitor teardown framework |
| `research-analyst` | `competitor-analysis` | Market gap analysis, positioning insights |
| `trend-analyst` | `competitor-analysis` | Competitive trends, feature gap identification |
| `product-manager` | `competitor-analysis` | Feature prioritization informed by competitor gaps |
| `code-reviewer` | `modern-python` | Flag non-modern patterns, missing types, ruff violations |
| `documentation-engineer` | `modern-python` | Document modern tooling setup accurately |

---

### Parallel Execution Pattern

When Claude spawns agents for a multi-step task, always check if tasks are independent and can run simultaneously:

```
GOOD — run in parallel (no dependencies):
  [market-researcher + competitor-analysis skill]
  [python-pro + modern-python skill]

GOOD — run in parallel:
  [nlp-engineer + pdf + modern-python skills]  →  engine/extractor.py
  [ml-engineer + modern-python skill]          →  engine/matcher.py
  [qa-expert + modern-python skill]            →  tests/

BAD — must be sequential (B depends on A):
  [python-pro writes scorer.py]  THEN  [qa-expert writes test_scorer.py]
```

When multiple independent agents can work at the same time, launch them in a single message with all tool calls in parallel. Never serialize work that can be parallelized.

---

### Skill Quality Gates

Before any agent completes a task, it must self-check against its paired skills:

- `modern-python` paired agents: Is every function typed? Is `pathlib` used over `os.path`? Are there any bare `dict` returns where a Pydantic model should be used?
- `fastapi-router-py` paired agents: Does every route use a Pydantic response model? Are errors raised as `HTTPException`? Is file validation done at the route level?
- `stripe-best-practices` paired agents: Are webhook signatures verified? Is `customer_id` stored, not card data? Are idempotency keys used?
- `competitor-analysis` paired agents: Does the analysis cover all 6 framework sections? Are at least 3 named competitors analyzed?

---

## 10. Out of Scope — Do Not Build

- No ATS simulation (yet)
- No LinkedIn scraper
- No bulk candidate ranking (B2B feature — future)
- No mobile app
- No browser extension
- No fine-tuned NER model (use spaCy entity rulers first)
- No vector database (plain cosine similarity is sufficient for MVP)
- No Redis caching (optimize only if benchmarks show a real bottleneck)
