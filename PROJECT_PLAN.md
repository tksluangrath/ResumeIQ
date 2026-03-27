# AI-Powered Resume & Job Match Engine — Project Plan

**Target Completion:** 6–8 Weeks
**Date Started:** 2026-03-19
**Goal:** Build a full-stack ML product that matches resumes to job descriptions, improves them with LLM assistance, and monetizes via Stripe — demonstrating end-to-end ML engineering skill.

---

## Table of Contents

1. [Project Scope](#1-project-scope)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Flow](#3-data-flow)
4. [Tech Stack & Justification](#4-tech-stack--justification)
5. [MVP Feature List](#5-mvp-feature-list)
6. [Phase Build Plan](#6-phase-build-plan)
7. [External Data Sources](#7-external-data-sources)
8. [Monetization Model](#8-monetization-model)
9. [Future Improvements](#9-future-improvements)

---

## 1. Project Scope

### What It Is
An end-to-end resume intelligence platform that:
- Ingests a resume (PDF) and a job description (text or URL)
- Semantically scores the match using sentence embeddings
- Extracts structured entities (skills, titles, companies, education) via NLP
- Generates a structured match report
- Produces an improved resume (LaTeX) tailored to the job
- Offers LLM-powered rewrite suggestions, gap analysis, and learning resources
- Charges users per scan or via subscription (Stripe)

### What It Is NOT (in MVP)
- Not a job board or aggregator
- Not a recruiter tool (no bulk processing)
- Not a full ATS replacement

### Success Criteria
- Week 2: CLI tool scores a resume vs. job description and returns a JSON report
- Week 4: Web UI where users can upload a PDF and paste a job description and get a score
- Week 6: LLM suggestions visible in UI, Llama running locally
- Week 8: Stripe payments live, deployed on Render/Railway, publicly shareable

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                           │
│   Streamlit (MVP) ──► React SPA (Production)                   │
│   Upload PDF | Paste Job URL/Description | View Report          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / REST
┌────────────────────────────▼────────────────────────────────────┐
│                          API LAYER                              │
│   FastAPI                                                       │
│   /match    /improve    /suggest    /history    /billing        │
└──────┬──────────────┬──────────────┬────────────────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼────────────────────────────┐
│  NLP ENGINE │ │ LLM ENGINE │ │         DATA LAYER              │
│  spaCy NER  │ │ Llama (local│ │  PostgreSQL (users, history)    │
│  Sentence   │ │ → Claude/  │ │  File storage (PDFs)            │
│  Transformers│ │   OpenAI)  │ │  Redis (caching, optional)      │
└──────┬──────┘ └─────┬──────┘ └─────────────────────────────────┘
       │              │
┌──────▼──────────────▼──────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                        │
│  USAJobs API | SAM.gov API | Stripe | PDF Parser (pdfplumber)  │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow

### Match Flow (Core Engine)
```
Resume PDF
    │
    ▼
[pdfplumber] ──► Raw text
    │
    ▼
[spaCy NER] ──► Extracted entities:
                  skills, job titles, companies,
                  education, certifications, dates
    │
    ▼
[sentence-transformers] ──► Resume embedding vector (384-dim)

Job Description (text or URL)
    │
    ▼
[Scraper / USAJobs API] ──► Raw JD text
    │
    ▼
[spaCy NER] ──► JD entities (required skills, title, experience)
    │
    ▼
[sentence-transformers] ──► JD embedding vector
    │
    ▼
[Cosine Similarity] ──► Semantic match score (0.0 – 1.0)
    │
    ▼
[Scoring Engine] ──► Weighted breakdown:
                       - Semantic similarity (40%)
                       - Skill keyword overlap (30%)
                       - Title relevance (15%)
                       - Experience level match (15%)
    │
    ▼
[Report Generator] ──► Structured JSON match report
                        + matched/missing skills
                        + score breakdown
                        + recommendations
```

### Improve Flow (LaTeX Resume)
```
Match Report + Original Resume Text
    │
    ▼
[Template Engine (Jinja2)] ──► LaTeX resume template
    │
    ▼
[LaTeX compiler (pdflatex)] ──► Improved resume PDF
                                 tailored to job description
```

### LLM Suggestion Flow
```
Match Report + Missing Skills + Weak Sections
    │
    ▼
[Prompt Builder] ──► Structured prompt
    │
    ▼
[Llama (local) / Claude / OpenAI] ──► Suggestions:
                                        - Rewrite bullet points
                                        - Key phrase insertions
                                        - Skill gap breakdown
                                        - Learning resource links
    │
    ▼
[Response Parser] ──► Structured suggestion JSON
```

---

## 4. Tech Stack & Justification

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend API** | FastAPI | Async-native, auto-generates OpenAPI docs, fast iteration, production-grade |
| **Semantic Matching** | `sentence-transformers` (`all-MiniLM-L6-v2`) | Fast, accurate, runs locally, no API cost, 384-dim embeddings, perfect for semantic similarity |
| **NER / NLP** | `spaCy` + custom NER | Best-in-class production NLP, custom training possible, entity rulers for skills |
| **PDF Parsing** | `pdfplumber` | Better than PyPDF2 for layout-aware text extraction |
| **Resume Generation** | Jinja2 + LaTeX | Professional PDF output, highly customizable templates |
| **LLM (Phase 3)** | Llama via `ollama` (local) | Free, private, no API cost — perfect for development and initial paid tier |
| **LLM (Production)** | Claude API / OpenAI | Higher quality, justifies premium pricing, easy swap via abstraction layer |
| **Frontend (MVP)** | Streamlit | Fastest path to shareable demo, no JS required |
| **Frontend (Production)** | React + Vite | Polished UX, component reuse, wide ecosystem |
| **Database** | PostgreSQL | Relational for user accounts + scan history, Render/Railway hosted |
| **Payments** | Stripe | Industry standard, excellent developer API, supports subscriptions + one-time |
| **Deployment** | Render or Railway | Git-push deploy, managed Postgres, affordable |
| **Job Data** | USAJobs API, SAM.gov | Real federal job listings, free, structured JSON |
| **Similarity Math** | `scikit-learn` cosine similarity | Lightweight, no additional deps |
| **Env Management** | `python-dotenv` | Simple `.env` loading |
| **Testing** | `pytest` | Standard Python testing |

---

## 5. MVP Feature List

### Must Have (Weeks 1–4)
- [ ] PDF resume upload and text extraction
- [ ] Job description input (paste text or URL)
- [ ] Semantic similarity score (0–100)
- [ ] Skill match breakdown (matched vs. missing)
- [ ] Structured JSON match report
- [ ] LaTeX resume generation tailored to job
- [ ] FastAPI endpoints: `/match`, `/improve`
- [ ] Streamlit UI: upload, paste, view score + report

### Nice to Have (Weeks 5–6)
- [ ] LLM-powered bullet point rewrites
- [ ] Skill gap breakdown with learning links
- [ ] Key phrase optimization suggestions
- [ ] USAJobs/SAM.gov job search integration

### Post-MVP (Week 7+)
- [ ] Stripe payments (per-scan + subscription)
- [ ] User accounts + scan history
- [ ] React frontend
- [ ] Bulk job matching (upload 1 resume, match to 50 jobs)
- [ ] Public deployment

---

## 6. Phase Build Plan

### Phase 1 — Core Matching Engine (Weeks 1–2)

**Goal:** CLI tool that takes a resume PDF + job description and returns a scored JSON report.

**Deliverables:**
- `engine/parser.py` — PDF text extraction via pdfplumber
- `engine/extractor.py` — spaCy NER pipeline (skills, titles, education)
- `engine/matcher.py` — Sentence Transformer embeddings + cosine similarity
- `engine/scorer.py` — Weighted scoring (semantic + keyword + title + experience)
- `engine/reporter.py` — Structured JSON report generation
- `cli.py` — CLI entry point: `python cli.py --resume resume.pdf --job job.txt`
- `tests/test_matching.py` — Unit tests for scorer + extractor

**Sample Output (JSON):**
```json
{
  "overall_score": 74.3,
  "semantic_similarity": 0.81,
  "skill_match": {
    "matched": ["Python", "FastAPI", "PostgreSQL", "REST APIs"],
    "missing": ["Kubernetes", "AWS Lambda", "Terraform"],
    "match_rate": 0.57
  },
  "title_relevance": 0.88,
  "experience_match": "senior_required_mid_detected",
  "recommendations": [
    "Add 'Kubernetes' to skills section",
    "Highlight cloud deployment experience",
    "Quantify API performance metrics"
  ]
}
```

---

### Phase 1b — LaTeX Resume Improvement (End of Week 2)

**Goal:** Generate an improved resume PDF as LaTeX, tailored to the job description.

**Deliverables:**
- `engine/latex_builder.py` — Jinja2 template population
- `templates/resume_base.tex.j2` — LaTeX resume template
- `engine/optimizer.py` — Rule-based section rewriting (pre-LLM)
- Output: `output/improved_resume.pdf`

**How It Works:**
1. Parse original resume into structured sections (Summary, Experience, Skills, Education)
2. Cross-reference missing skills from match report
3. Suggest skill insertions and reordered bullet points
4. Inject into LaTeX template
5. Compile to PDF via `subprocess` + `pdflatex`

---

### Phase 2 — API + Minimal UI (Weeks 3–4)

**Goal:** FastAPI backend + Streamlit frontend. Users can use the tool via browser.

**Deliverables:**
- `api/main.py` — FastAPI app
- `api/routes/match.py` — POST `/match` endpoint
- `api/routes/improve.py` — POST `/improve` endpoint
- `api/models.py` — Pydantic request/response models
- `ui/streamlit_app.py` — Upload PDF, paste JD, view score + download improved resume
- `docker-compose.yml` — Local dev setup

**API Endpoints:**
```
POST /match
  Body: { resume_pdf: File, job_description: str }
  Returns: MatchReport JSON

POST /improve
  Body: { resume_pdf: File, job_description: str }
  Returns: { latex: str, pdf_url: str, suggestions: [] }

GET /health
  Returns: { status: "ok" }
```

**Feedback Checkpoint:** Share Streamlit demo with 5–10 people. Collect feedback before Phase 3.

---

### Phase 3 — LLM Intelligence Layer (Weeks 5–6)

**Goal:** Add AI-powered suggestions using Llama locally, abstracted for easy swap to Claude/OpenAI.

**Deliverables:**
- `engine/llm/base.py` — Abstract LLM interface
- `engine/llm/ollama_llm.py` — Llama via `ollama` Python client
- `engine/llm/claude_llm.py` — Claude API implementation (ready but toggled off)
- `engine/llm/openai_llm.py` — OpenAI implementation (ready but toggled off)
- `engine/suggester.py` — Prompt builder + response parser
- `api/routes/suggest.py` — POST `/suggest` endpoint
- UI updates: display LLM suggestions alongside score

**LLM Features:**
- Rewrite weak resume bullet points to match job language
- Insert missing keywords naturally into existing content
- Skill gap analysis: "You're missing X. Here's how to learn it: [link]"
- Summary/objective rewrite tailored to specific role

**LLM Swap Strategy:**
```python
# config.py
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # ollama | claude | openai

def get_llm():
    if LLM_PROVIDER == "claude":
        return ClaudeLLM()
    elif LLM_PROVIDER == "openai":
        return OpenAILLM()
    return OllamaLLM()
```

---

### Phase 4 — Production & Monetization (Weeks 7–8)

**Goal:** Public-facing product with payments, user accounts, and polished UI.

**Deliverables:**
- React frontend (Vite + TypeScript)
- PostgreSQL schema: users, scans, subscriptions
- Stripe integration: per-scan credits + monthly subscription
- User auth: JWT via FastAPI
- Deploy: Render (API + DB) or Railway
- Launch: Post on LinkedIn, Reddit (r/cscareerquestions, r/datascience), HN Show HN

**Stripe Plans:**
```
Free Tier:    3 scans/month, basic score only
Starter:      $9/mo — 20 scans + LaTeX resume
Pro:          $19/mo — unlimited scans + LLM suggestions
Pay-per-scan: $1.99/scan — no subscription required
```

---

## 7. External Data Sources

### USAJobs API
- **URL:** `https://data.usajobs.gov/api/search`
- **Auth:** API key via header (`Authorization-Key`)
- **Use:** Pull live federal job listings by keyword, location, pay grade
- **Rate limit:** Generous for personal projects
- **Sample script:** `scripts/fetch_usajobs.py`

### SAM.gov API
- **URL:** `https://api.sam.gov/opportunities/v2/search`
- **Auth:** API key (free registration)
- **Use:** Pull government contract opportunities — useful for contractor resumes
- **Sample script:** `scripts/fetch_samgov.py`

### Bulk Job Fetch Strategy
```python
# scripts/fetch_usajobs.py
# Pull 50 job descriptions matching a keyword, save as JSON
# Use for: batch testing the matcher against real job listings
```

---

## 8. Monetization Model

### Revenue Streams

| Stream | Price | Target User |
|--------|-------|-------------|
| Pay-per-scan | $1.99/scan | Casual job seeker |
| Starter subscription | $9/month | Active job seeker (1–3 month runway) |
| Pro subscription | $19/month | Power user, career changer |
| API access (future) | $49/month | HR tools, career coaches |

### Why Users Pay
- **Phase 1–2 (free):** Basic score — builds trust, generates feedback
- **Phase 3 (paid gate):** LLM suggestions are the value driver. The Llama → Claude upgrade is what justifies the price. Users see a before/after resume improvement and pay for it.
- **Phase 4 (retention):** Scan history, tracked improvement over time, multiple resume versions

### Cost Structure (at scale)
- Llama (local): $0 — runs on your machine or a $20/mo VPS
- Claude API: ~$0.003/1K tokens → ~$0.03/suggestion request — very low
- Render/Railway: ~$25–50/month for production
- Stripe fees: 2.9% + $0.30/transaction

### Break-Even
~30 paying users at $19/month covers hosting and API costs.

---

## 9. Future Improvements

- **Browser extension** — Analyze job postings on LinkedIn/Indeed in one click
- **ATS simulation** — Score resume against common ATS parsers, not just semantic match
- **Multi-resume management** — Store and version-control multiple resume variants
- **Interview prep** — Generate likely interview questions from job description
- **Salary benchmarking** — Pull salary data from BLS/Glassdoor for skill set
- **Referral tracking** — "Apply" button with UTM tracking to measure conversion
- **Team/bulk mode** — HR teams upload candidate resumes, ranked against a JD
- **Resume anonymization** — Remove PII for bias-blind screening (B2B feature)
- **LinkedIn import** — Scrape or API-import LinkedIn profile as resume source
- **Fine-tuned NER** — Train custom spaCy NER on domain-specific job boards
- **Vector database** — Migrate embeddings to Pinecone/pgvector for fast bulk matching
- **Mobile app** — React Native wrapper around the web app
- **GitHub Actions CI** — Automated testing, linting, and deployment pipeline
- **A/B testing** — Test different resume templates for application success rate

---

*This document is a living plan. Update it as scope, priorities, or technology choices change.*
