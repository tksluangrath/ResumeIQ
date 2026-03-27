# Setup & Installation Guide

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Recommend `pyenv` for version management |
| pip | Latest | `pip install --upgrade pip` |
| Git | Any | For version control |
| LaTeX | TexLive or MiKTeX | Required for PDF resume generation |
| Ollama | Latest | Required for local LLM (Phase 3) |
| Node.js | 18+ | Required for React frontend (Phase 4 only) |
| PostgreSQL | 15+ | Required for user accounts (Phase 4 only) |

---

## Quick Start (Phase 1 — Matching Engine)

### 1. Clone and create virtual environment

```bash
git clone <your-repo-url>
cd ai_powered_resume_job_match

python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Download spaCy model

```bash
python -m spacy download en_core_web_lg
```

> `en_core_web_lg` includes word vectors — better for NER accuracy.
> Use `en_core_web_sm` if you're on a low-memory machine.

### 4. Copy environment file

```bash
cp .env.example .env
```

Edit `.env` with your values (see [Environment Variables](#environment-variables) below).

### 5. Run the CLI matcher

```bash
python cli.py --resume samples/resume.pdf --job samples/job_description.txt
```

**Expected output:**
```json
{
  "overall_score": 74.3,
  "semantic_similarity": 0.81,
  "skill_match": {
    "matched": ["Python", "FastAPI", "PostgreSQL"],
    "missing": ["Kubernetes", "Terraform"],
    "match_rate": 0.60
  },
  "recommendations": [
    "Add 'Kubernetes' to your skills section",
    "Highlight any cloud deployment experience"
  ]
}
```

---

## Phase 2 — FastAPI + Streamlit

### Start the API server

```bash
uvicorn api.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Start the Streamlit UI

```bash
streamlit run ui/streamlit_app.py
```

UI available at: `http://localhost:8501`

---

## Phase 3 — LLM Setup (Ollama + Llama)

### Install Ollama

```bash
# Mac
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### Pull the Llama model

```bash
ollama pull llama3.2        # 3B — fastest, good for dev
# ollama pull llama3.1:8b  # 8B — better quality, needs 8GB+ RAM
```

### Start Ollama server

```bash
ollama serve
# Runs on http://localhost:11434 by default
```

### Verify LLM is working

```bash
python -c "from engine.llm.ollama_llm import OllamaLLM; print(OllamaLLM().ping())"
```

---

## Phase 4 — PostgreSQL + React

### Start PostgreSQL (local dev)

```bash
# Using Docker (easiest)
docker run --name resume-db \
  -e POSTGRES_USER=resumeuser \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=resumedb \
  -p 5432:5432 -d postgres:15
```

### Run migrations

```bash
alembic upgrade head
```

### Install React frontend dependencies

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values below.

```bash
cp .env.example .env
```

### `.env.example`

```dotenv
# ─── App ───────────────────────────────────────────────
APP_ENV=development                  # development | production
DEBUG=true
SECRET_KEY=change_me_to_a_random_string_32chars

# ─── LLM Provider ──────────────────────────────────────
# Options: ollama | claude | openai
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Claude (Phase 3+ — swap in when ready to monetize)
ANTHROPIC_API_KEY=

# OpenAI (optional alternative)
OPENAI_API_KEY=

# ─── Database (Phase 4) ─────────────────────────────────
DATABASE_URL=postgresql://resumeuser:yourpassword@localhost:5432/resumedb

# ─── Stripe (Phase 4) ───────────────────────────────────
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Price IDs (create in Stripe Dashboard)
STRIPE_PRICE_STARTER=price_...       # $9/month
STRIPE_PRICE_PRO=price_...           # $19/month
STRIPE_PRICE_PER_SCAN=price_...      # $1.99 one-time

# ─── External APIs ──────────────────────────────────────
# USAJobs API (register at https://developer.usajobs.gov/)
USAJOBS_API_KEY=your_key_here
USAJOBS_USER_AGENT=YourName/YourEmail@domain.com

# SAM.gov API (register at https://sam.gov/profile/developer)
SAMGOV_API_KEY=your_key_here

# ─── File Storage ───────────────────────────────────────
UPLOAD_DIR=./uploads                 # Local dev
MAX_UPLOAD_SIZE_MB=10

# ─── NLP Settings ───────────────────────────────────────
SPACY_MODEL=en_core_web_lg           # en_core_web_sm for low memory
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2

# ─── Scoring Weights (must sum to 1.0) ──────────────────
WEIGHT_SEMANTIC=0.40
WEIGHT_SKILLS=0.30
WEIGHT_TITLE=0.15
WEIGHT_EXPERIENCE=0.15
```

---

## `requirements.txt`

```
# API
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9      # file uploads
pydantic>=2.0.0
pydantic-settings>=2.0.0

# NLP
spacy>=3.7.0
sentence-transformers>=2.7.0
scikit-learn>=1.4.0

# PDF Parsing
pdfplumber>=0.11.0

# LaTeX / Template
Jinja2>=3.1.0

# LLM
ollama>=0.1.9
anthropic>=0.25.0            # Claude API (Phase 3+)
openai>=1.30.0               # OpenAI fallback

# Database (Phase 4)
sqlalchemy>=2.0.0
alembic>=1.13.0
asyncpg>=0.29.0              # async postgres driver
psycopg2-binary>=2.9.0

# Payments (Phase 4)
stripe>=9.0.0

# Auth (Phase 4)
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# HTTP / Scraping
httpx>=0.27.0
beautifulsoup4>=4.12.0
requests>=2.31.0

# Frontend (MVP)
streamlit>=1.33.0

# Dev / Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
python-dotenv>=1.0.0
black>=24.0.0
ruff>=0.4.0
```

---

## Project Directory Structure

```
ai_powered_resume_job_match/
│
├── engine/                      # Core ML/NLP logic
│   ├── __init__.py
│   ├── parser.py                # PDF text extraction
│   ├── extractor.py             # spaCy NER pipeline
│   ├── matcher.py               # Sentence Transformer + cosine similarity
│   ├── scorer.py                # Weighted scoring engine
│   ├── reporter.py              # JSON report generator
│   ├── latex_builder.py         # LaTeX resume generator
│   ├── optimizer.py             # Rule-based resume optimizer
│   └── llm/
│       ├── base.py              # Abstract LLM interface
│       ├── ollama_llm.py        # Llama via Ollama
│       ├── claude_llm.py        # Claude API
│       └── openai_llm.py        # OpenAI
│
├── api/                         # FastAPI application
│   ├── main.py
│   ├── models.py                # Pydantic schemas
│   ├── dependencies.py          # Auth, DB session
│   └── routes/
│       ├── match.py             # POST /match
│       ├── improve.py           # POST /improve
│       ├── suggest.py           # POST /suggest (Phase 3)
│       ├── history.py           # GET /history (Phase 4)
│       └── billing.py           # Stripe routes (Phase 4)
│
├── ui/
│   └── streamlit_app.py         # Streamlit MVP frontend
│
├── frontend/                    # React app (Phase 4)
│   ├── src/
│   └── package.json
│
├── templates/
│   └── resume_base.tex.j2       # LaTeX resume template
│
├── scripts/
│   ├── fetch_usajobs.py         # Pull jobs from USAJobs API
│   └── fetch_samgov.py          # Pull from SAM.gov
│
├── samples/                     # Test data
│   ├── resume.pdf
│   └── job_description.txt
│
├── tests/
│   ├── test_matching.py
│   ├── test_extractor.py
│   └── test_api.py
│
├── uploads/                     # Runtime PDF uploads (gitignored)
├── output/                      # Generated LaTeX/PDFs (gitignored)
│
├── cli.py                       # CLI entry point
├── config.py                    # Settings via pydantic-settings
├── .env                         # Your local secrets (gitignored)
├── .env.example                 # Template committed to repo
├── requirements.txt
├── PROJECT_PLAN.md
└── SETUP.md
```

---

## Usage Examples

### CLI — Score a resume against a job description

```bash
python cli.py \
  --resume samples/resume.pdf \
  --job samples/job_description.txt \
  --output output/report.json
```

### CLI — Generate improved LaTeX resume

```bash
python cli.py \
  --resume samples/resume.pdf \
  --job samples/job_description.txt \
  --improve \
  --output output/improved_resume.pdf
```

### API — POST /match

**Request:**
```bash
curl -X POST http://localhost:8000/match \
  -F "resume_pdf=@samples/resume.pdf" \
  -F "job_description=We are looking for a Python backend engineer with FastAPI experience..."
```

**Response:**
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
    "Add 'Kubernetes' to skills section — mentioned 4 times in JD",
    "Highlight cloud deployment experience (AWS/GCP)",
    "Quantify API performance metrics in your bullet points"
  ]
}
```

### API — POST /improve

**Request:**
```bash
curl -X POST http://localhost:8000/improve \
  -F "resume_pdf=@samples/resume.pdf" \
  -F "job_description=We are looking for a Python backend engineer..." \
  --output output/improved_resume.pdf
```

### API — POST /suggest (Phase 3, LLM)

**Request:**
```bash
curl -X POST http://localhost:8000/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "match_report": { ... },
    "resume_sections": { "experience": "...", "skills": "..." },
    "job_description": "..."
  }'
```

**Response:**
```json
{
  "bullet_rewrites": [
    {
      "original": "Built backend services for internal tools",
      "improved": "Engineered high-throughput FastAPI microservices handling 10K+ daily requests for internal tooling, reducing latency by 40%"
    }
  ],
  "skill_gaps": [
    {
      "skill": "Kubernetes",
      "importance": "high",
      "learning_resources": [
        { "title": "Kubernetes Basics", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/" },
        { "title": "KodeKloud CKA Course", "url": "https://kodekloud.com/courses/cka-certification-course-certified-kubernetes-administrator/" }
      ]
    }
  ],
  "summary_rewrite": "Results-driven backend engineer with 5+ years building production FastAPI services..."
}
```

### Fetch 50 jobs from USAJobs (bulk testing)

```bash
python scripts/fetch_usajobs.py \
  --keyword "data scientist" \
  --location "Remote" \
  --count 50 \
  --output data/usajobs_data_scientist.json
```

---

## LaTeX Requirement

Resume PDF generation requires a LaTeX installation.

**Mac:**
```bash
brew install --cask mactex-no-gui     # ~4GB, full TexLive
# or for minimal install:
brew install basictex                  # ~100MB, add packages as needed
```

**Ubuntu/Debian:**
```bash
sudo apt-get install texlive-latex-base texlive-fonts-recommended
```

**Windows:**
Download MiKTeX from https://miktex.org/download

**Verify install:**
```bash
pdflatex --version
```

---

## Common Issues

| Problem | Fix |
|---------|-----|
| `spacy.errors.E050: Can't find model 'en_core_web_lg'` | Run `python -m spacy download en_core_web_lg` |
| `pdflatex: command not found` | Install TexLive (see above) |
| Ollama connection refused | Run `ollama serve` in a separate terminal |
| `CUDA out of memory` on sentence-transformers | Model runs on CPU by default — no GPU needed |
| Port 8000 already in use | `uvicorn api.main:app --port 8001` |
| Streamlit blank page | Hard-refresh browser, check terminal for errors |
| Stripe webhook 400 error | Run `stripe listen --forward-to localhost:8000/billing/webhook` |

---

*Keep this document updated as the stack evolves.*
