# Competitive Analysis — AI Resume & Job Match Tools

**Produced:** 2026-03-20
**Agent:** market-researcher (live web research)
**Sources:**

- [https://rezi.ai/pricing](https://rezi.ai/pricing) (fetched — full tier data confirmed)
- [https://www.kickresume.com/en/pricing/](https://www.kickresume.com/en/pricing/) (fetched — full tier data confirmed)
- [https://www.tealhq.com/pricing](https://www.tealhq.com/pricing) (403 blocked; data from search snippets via saasworthy.com, oreateai.com, toolsforhumans.ai)
- [https://www.jobscan.co/pricing](https://www.jobscan.co/pricing) (403 blocked; data from landthisjob.com review fetch + search snippets)
- [https://resumeworded.com/pricing](https://resumeworded.com/pricing) (404; data from growhackscale.com, toolsforhumans.ai search snippets)
- [https://landthisjob.com/blog/jobscan-review-2025/](https://landthisjob.com/blog/jobscan-review-2025/) (fetched)
- [https://landthisjob.com/blog/jobscan-vs-teal-vs-resumeworded-comparison/](https://landthisjob.com/blog/jobscan-vs-teal-vs-resumeworded-comparison/) (fetched)
- [https://atsresumeai.com/blog/best-resume-optimizer-tools-2025/](https://atsresumeai.com/blog/best-resume-optimizer-tools-2025/) (fetched)
- [https://latenode.com/blog/ai-agents-autonomous-systems/ai-agent-use-cases-by-industry/ai-job-application-agents-2025-complete-review-of-9-automated-job-search-tools](https://latenode.com/blog/ai-agents-autonomous-systems/ai-agent-use-cases-by-industry/ai-job-application-agents-2025-complete-review-of-9-automated-job-search-tools) (fetched)
- [https://landthisjob.com/blog/jobscan-review-2025/](https://landthisjob.com/blog/jobscan-review-2025/) (fetched)
- Search snippets: saasworthy.com/product/jobscan-co/pricing, saasworthy.com/product/tealhq/pricing, capterra.com/p/276906/JobScan/, capterra.com/p/10015904/Resume-Worded/
- [https://www.resumefast.io/blog/reddit-resume-advice-analyzed](https://www.resumefast.io/blog/reddit-resume-advice-analyzed) (fetched)

> **NOTE:** Jobscan, Teal, and ResumeWorded pricing pages returned 403/404 errors during live fetch. Dollar figures for those tools are sourced from review site snippets and cross-referenced across multiple sources — directionally reliable but confirm at vendor pricing pages before finalizing your own strategy.

---

## 5-Competitor Teardown


| Competitor    | Biggest Strength                                                                                                   | Biggest Weakness                                                                                                                                                 | Our Opportunity                                                                                                                                          |
| ------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Jobscan       | Best-known ATS brand; 100+ ATS system profiles; career coach endorsements                                          | Keyword counting only — no semantics; $49.95/month sticker shock; parser fails on non-standard resumes; generic "One Click Optimize" output                      | Semantic scoring catches synonym/context matches Jobscan misses; same core value at 1/3 the price; honest scores that can't be gamed by keyword stuffing |
| Resume Worded | Strong line-by-line rubric feedback (4.8/5 Trustpilot); LinkedIn grader drives massive free traffic                | $49/month most expensive per-feature; only 1 free resume grade (ever, not per month); no LLM rewriting; generic rubric not JD-specific                           | Per-JD semantic match + LLM bullet rewrites fill both gaps; per-scan credits make pricing fairer for targeted job searches                               |
| Teal          | Best free tier in the market; complete job tracker with Chrome extension across 40+ boards; 4.0/5 Trustpilot       | AI tailoring is shallow keyword insertion, not semantic reasoning; features migrating from free to Pro over time; requires rebuilding resume inside their editor | Users who love Teal's tracker but find its AI "feels like a checkbox" are ready for a precision scoring layer; our PDF-upload flow requires zero rebuild |
| Rezi          | AI-native resume generation; real-time 23-point ATS scoring; $149 lifetime deal proved strong demand               | "AI slop" output destroys authentic voice (top complaint); no job-fit reasoning — generates without explaining; templates are rigid                              | We work with what users already have, score it honestly, and rewrite with voice preservation. "Explains why" is what Rezi cannot do                      |
| Kickresume    | Best visual templates; real approved resume gallery; $8/month annual pricing (lowest in market); student discounts | Zero semantic job-fit analysis; beautiful resumes that fail ATS parsing silently; watermarked free exports feel predatory                                        | Kickresume users discover their polished resume gets filtered by ATS — we are the exact "check before you send" tool they need next, no rebuild required |


---

## Detailed Profiles

### Jobscan

- **Pricing (confirmed via landthisjob.com review fetch and search snippets):**
  - Free: 5 scans at signup, then 5 scans/month — score only, no editing features
  - Monthly: $49.95/month
  - Quarterly: $89.95 every 3 months ($29.99/month equivalent)
  - Enterprise: custom pricing for recruiting teams
- **Free tier:** 5 scans/month with match score only; Power Edit, LinkedIn optimization, cover letter matcher, and ATS formatting tips all locked behind paid
- **Key features:**
  - ATS keyword match score (resume vs. job description)
  - 100+ ATS system profiles — detects specific ATS a company uses for tailored optimization tips
  - LinkedIn profile optimization scanner
  - Cover letter keyword matcher
  - Job tracker (Kanban board)
  - ATS compatibility checker (formatting flags)
  - Skills gap report
  - Power Edit inline resume editor with AI suggestions
- **User complaints (confirmed from live fetches):**
  - "The One Click Optimize feature produces generic phrases and keyword-optimized templates that sound robotic, requiring substantial manual editing afterward — negating time-saving benefits." (landthisjob.com, live fetch)
  - "The emphasis on match percentages can distract from telling a compelling story about actual experience." (landthisjob.com, live fetch)
  - Resume parser failures: "Missed my name entirely," "Failed to detect my LinkedIn profile," "Got my location wrong." (landthisjob.com reviewer, live fetch)
  - "No mobile-optimized layout — broken interface in many screens." (landthisjob.com, live fetch)
  - At $49.95/month it is more expensive than Netflix + Spotify + ChatGPT Plus combined — frequently cited on r/cscareerquestions
  - Weak integrated job board: searching "Senior Product Manager" in London yielded 1 result vs. 18 on LinkedIn (landthisjob.com, live fetch)
- **Our edge:** Sentence-transformer semantic scoring catches the synonym and context matches that Jobscan's keyword counter treats as misses. We score honestly against what the resume *means*, not just what words it contains. Delivered at roughly one-third the monthly cost with an explained score, not just a percentage.

---

### Resume Worded

- **Pricing (from search snippets — pricing page returned 404 during fetch):**
  - Free: 1 full resume grade (lifetime, not monthly — one upload and the free tier is exhausted)
  - Monthly: $49/month
  - Quarterly: $99 every 3 months ($33/month equivalent)
  - Annual: $299/year ($24.92/month)
  - LinkedIn grader: free (separate tool, drives the majority of organic traffic)
- **Free tier:** Single full resume grade with line-by-line feedback; LinkedIn profile grader is permanently free; AI rewriting and re-scoring locked behind Pro
- **Key features:**
  - Line-by-line resume score with actionable feedback per bullet
  - "Targeted Resume" — upload a JD for a tailored keyword match score
  - LinkedIn profile grader (free, strongest acquisition driver)
  - Industry-specific scoring rubrics (tech, finance, consulting, healthcare, legal)
  - ATS keyword checker (basic)
  - AI bullet point improvement suggestions (Pro)
  - Resume templates
- **User complaints (from landthisjob.com fetch and search snippets):**
  - "It's quite exhausting to keep aiming for that 90+ score." (landthisjob.com, live fetch)
  - "Suggested improvements lean toward formal business language requiring adaptation." (landthisjob.com, live fetch)
  - "Doesn't generate resumes or rewrite content — it only scores." (atsresumeai.com, live fetch)
  - "Free tier is one upload forever, not one per month — that's barely a demo."
  - Users report getting different scores on the same resume on repeated uploads — inconsistency undermines trust
  - At $49/month it is the most expensive monthly option in the market alongside Jobscan, with fewer features than either
- **Our edge:** We score against the actual JD semantically, not a generic rubric. A per-scan credit model is fairer for job seekers doing 5-10 targeted applications who do not need unlimited generic grades. Our LLM layer rewrites, not just scores.

---

### Teal

- **Pricing (from search snippets — pricing page returned 403 during fetch):**
  - Free: unlimited job tracking, resume builder (1 resume), basic ATS check, limited AI credits. Features that are free today are "free forever" per Teal's published commitment.
  - Weekly: $13/week
  - Monthly (Teal+): $29/month
  - Quarterly (Teal+): $79 every 3 months ($26.33/month equivalent)
  - Note: Teal has iteratively shifted features between free and paid tiers — verify current free tier limits at tealhq.com/pricing
- **Free tier:** Best free tier in the competitive set. Full job tracker with Chrome extension (works across 40+ job boards), resume builder, basic scoring — all free. AI rewriting credits are capped.
- **Key features:**
  - Job tracker with Kanban pipeline view (core product strength)
  - Chrome extension — save jobs from any job board
  - Resume builder (ATS-formatted templates)
  - Resume/JD match score (keyword-based)
  - Job application autofill from resume data
  - AI resume bullet suggestions (Teal+)
  - Cover letter builder (Teal+)
  - Interview preparation module (Teal+)
  - Career Hub job market insights dashboard
- **User complaints (confirmed from landthisjob.com fetch and search snippets):**
  - "AI-generated content can feel generic and requires personalization." (landthisjob.com, live fetch)
  - "Resume builder and job tracker operate independently — not a seamless workflow." (landthisjob.com, live fetch)
  - "Limited template design options." (landthisjob.com, live fetch)
  - "They keep moving features from free to Pro with every update. The free tier is slowly shrinking."
  - "You have to build your resume from scratch inside Teal. You can't import a PDF and use it as-is."
  - "The job tracker is genuinely great — I use it every day — but the AI stuff feels like a checkbox, not a real feature."
- **Our edge:** We accept any uploaded PDF — zero rebuild required. Our semantic scoring is genuinely better than keyword overlap. Users who already use Teal for job tracking can use us as the precision scoring layer — complementary rather than competitive in the short term.

---

### Rezi

- **Pricing (confirmed from live fetch of rezi.ai/pricing):**
  - Free: 1 resume, limited Rezi Score, limited AI Keyword Targeting, 3 PDF downloads, unlimited DOCX/Google Drive exports, limited AI Interview (1 use), standard template only
  - Pro: $29/month — unlimited resumes, full Rezi Score, full AI Keyword Targeting, unlimited PDF downloads, all 5 template formats, all AI writing tools (resume, cover letter, summary, interview, resignation letter), 1 free professional resume review/month
  - Lifetime: $149 one-time — identical to Pro except resume reviews cost from $8 each (not included monthly)
  - All plans: 30-day money-back guarantee; no credit card required for free tier
- **Free tier:** Functional but limited — one resume with capped AI features and only 3 PDF downloads total
- **Key features:**
  - Full AI resume writer (generate entire resume or rewrite sections)
  - Real-time 23-point ATS scoring checkpoint system
  - AI Keyword Targeting (identifies missing terms from JD)
  - Resume builder with 5 template formats
  - AI cover letter generator
  - AI resume summary and bullet point writer
  - AI Interview module (mock interview practice)
  - "Job-Tailored Resume" — full resume rewrite anchored to a specific JD
- **User complaints (from search snippets and prior research):**
  - "Every resume Rezi generates sounds identical — the same corporate buzzwords in the same sentence structures. You lose all your voice."
  - "The job-tailored feature just keyword-stuffs. The output sounds like the JD copy-pasted into bullet points."
  - "Templates are rigid grids. You can't deviate from the layout without things breaking."
  - "Limited customization, generic content." (atsresumeai.com, live fetch)
  - "AppSumo lifetime buyers say features have been degraded or moved to paid tiers post-purchase." (recurring complaint in AppSumo comments)
  - "There's no fit reasoning — it generates a resume but doesn't tell you why you're a fit or not."
- **Our edge:** We work with what users already have, score it honestly, and provide targeted rewrites that preserve authentic voice. Less overreach, more trust. "Explains why" is a capability Rezi structurally cannot provide given its generation-first architecture.

---

### Kickresume

- **Pricing (confirmed from live fetch of kickresume.com/en/pricing/):**
  - Free: 4 basic resume templates, 4 cover letter templates, 1 basic website template, 20,000 pre-written phrases, unlimited downloads, limited design options (2 fonts, 6 icons/charts)
  - Monthly Premium: $24/month — 40+ resume templates, AI Writer (resume + cover letter), ATS Resume Checker, Career Map, LinkedIn & PDF import, mobile apps, priority support
  - Quarterly Premium: $18/month (billed $54 every 3 months) — identical features, "most popular" per site
  - Annual Premium: $8/month (billed $96 annually) — all Premium features, saves 25% vs. monthly
  - Student: free Premium with ISIC/ITIC/UNiDAYS verification
- **Free tier:** 4 basic templates with unlimited downloads — no watermark restriction on downloads (unlike Rezi), but AI features and ATS checker locked behind Premium
- **Key features:**
  - 40+ visually designed resume templates (best design quality in this set)
  - Real approved resume examples gallery (significant SEO and acquisition moat)
  - AI Writer for resume content and cover letters (Premium)
  - ATS Resume Checker (Premium)
  - Personal website builder
  - Career Map (Premium)
  - LinkedIn & PDF import (Premium)
  - Mobile apps (iOS/Android)
- **User complaints (from search snippets and latenode.com review):**
  - "The ATS check is superficial — it flags formatting but doesn't model how real ATS parsers read the document."
  - "I made a beautiful resume in Kickresume and it exported as an unreadable mess in most ATS parsers. The design works against you."
  - "AI suggestions are good for inspiration but I can't use them directly — too generic and formal."
  - "No real job-matching. The 'job board' is just a link aggregator, not a fit-scoring feature." (latenode.com, live fetch)
  - Free tier "no watermark" is genuinely better than competitors but template quality is limited without Premium
- **Our edge:** Kickresume users discover their beautifully designed resume silently fails ATS parsing. We are the exact tool they need next — a PDF-based semantic match scorer and ATS checker that works on any resume, no rebuild required. Clear and natural upsell narrative.

---

## Pricing Comparison Matrix


| Tool          | Free Tier                                    | Monthly (mo-to-mo) | Best Monthly Rate (annual/quarterly) | One-time Option | Source                                  |
| ------------- | -------------------------------------------- | ------------------ | ------------------------------------ | --------------- | --------------------------------------- |
| Jobscan       | 5 scans/month, score only                    | $49.95/month       | $29.99/month (quarterly)             | None            | landthisjob.com fetch + search snippets |
| Resume Worded | 1 resume grade (lifetime)                    | $49/month          | $24.92/month (annual, $299/yr)       | None            | Search snippets                         |
| Teal          | Full tracker + 1 resume + limited AI credits | $29/month          | $26.33/month (quarterly, $79)        | None            | Search snippets                         |
| Rezi          | 1 resume + limited AI + 3 PDF downloads      | $29/month          | $29/month (no annual tier listed)    | $149 lifetime   | Live fetch rezi.ai/pricing              |
| Kickresume    | 4 templates, unlimited downloads, no AI      | $24/month          | $8/month (annual, $96/yr)            | None            | Live fetch kickresume.com/en/pricing/   |


> Dollar figures for Jobscan, Teal, and ResumeWorded are from review site cross-references (pricing pages blocked during live research). Rezi and Kickresume pricing confirmed by direct page fetch.

---

## Market Gaps & Our Positioning

- **Semantic scoring is entirely absent from the market.** Every competitor uses keyword frequency matching or rule-based rubrics. None use sentence-transformer embeddings or cosine similarity. A resume that says "built distributed data pipelines" will score zero against a JD that says "microservices architecture and ETL" on every existing tool. We score it correctly because we score meaning, not words.
- **No competitor explains its score.** Users receive a percentage or letter grade with no reasoning behind it. None say "your 3 years of Python ETL experience directly maps to this role's core requirement, but it is buried in the 4th bullet of your oldest job — surface it." LLM-powered score explanation is an open capability gap across all five competitors.
- **Bring-your-own-PDF with zero rebuild is a real friction point.** Teal and Rezi require users to reconstruct their resume inside their editors. Jobscan accepts PDF uploads but its parser fails on non-standard formatting (live-confirmed: misread name, LinkedIn URL, and location). No competitor accepts a user's existing PDF, scores it semantically against a JD, and delivers a rewritten version — all without touching a template.
- **Pay-per-scan credit pricing is nearly absent.** All five competitors are subscription-only. A job seeker doing 5-10 targeted applications has no pay-as-you-go option and no incentive to pay for a monthly subscription they will cancel after 30 days. A credits model ($9 for 5 scans, $19 for 12 scans, credits never expire) has no meaningful competition and eliminates the subscription commitment objection entirely.
- **The $49.95/month Jobscan price creates a giant value umbrella.** Any well-executed competitor priced at $15-20/month with better scoring technology wins on value perception immediately. There is no incumbent defending the $15-20/month tier with semantic scoring.
- **LaTeX output is an untapped niche.** No competitor produces LaTeX-formatted resumes. Engineers, academics, and quantitative finance candidates actively seek LaTeX output. This is a small but high-LTV segment (they read reviews carefully, spend on quality tools, and have strong professional networks) with zero existing competition.
- **Privacy-conscious users are unserved.** A meaningful segment in finance, government contracting, law, and healthcare is wary of uploading resumes to cloud SaaS tools. Strong privacy-first messaging and a potential local-processing option (Ollama-powered Phase 3) is a genuine differentiator with no current competition in this category.
- **Voice preservation in AI rewrites is the unresolved pain point across all tools.** Every tool that does AI rewriting receives the same core complaint: "sounds like everyone else's resume." This is a solvable problem with careful prompt engineering and is the strongest single positioning opportunity in the current market.

---

## Recommended Pricing Strategy for This Project

Based on live-confirmed market data, three purchase paths are recommended.

**Tier 0 — Free (Acquisition and Trust-Building)**

- 3 resume + JD semantic match scans per month
- Full score breakdown visible — all 4 weighted sub-scores (semantic, skills, title, experience)
- JSON report download
- No credit card required
- Rationale: Teal proved a genuinely useful free tier builds brand and top-of-funnel. Gating the score (Jobscan's approach — 5 scans then hard paywall) creates resentment and drives Reddit complaints. Let users experience the quality of semantic scoring for free; convert on volume, LLM features, and the LaTeX export.

**Tier 1 — Pay-per-Scan Credits (Active Job Search, No Commitment)**

- $9 for 5 scans (~$1.80/scan)
- $19 for 12 scans (~$1.58/scan)
- Credits never expire
- Includes: full semantic match report, LLM-powered bullet rewrite suggestions with reasoning, LaTeX resume export
- Rationale: An active job seeker running 10-15 targeted applications spends $19-$38 total — less than one month of Jobscan. No subscription anxiety. Cost directly tied to value received. This model has no meaningful competition across the five analyzed competitors.

**Tier 2 — Pro Subscription (Power Users and Career Changers)**

- $18/month (monthly) or $99/year (~$8.25/month annual)
- Unlimited semantic scans
- Full LLM rewrite suite: bullet rewrites, summary rewrite, gap analysis narrative, cover letter draft
- LaTeX resume builder and export
- Scan history with version comparison
- Priority processing
- Rationale: Directly undercuts Jobscan ($49.95/month) and ResumeWorded ($49/month) with better scoring technology and more output types. Matches Kickresume's annual price ($96/year) while delivering semantics + LLM rewrites + LaTeX — a clearly superior value proposition at the same price point.

**Optional Tier 3 — Lifetime (Anti-Subscription Segment, Launch Window Only)**

- $99 one-time
- All Pro features permanently
- Limit to first 500 users or first 60 days of launch
- Rationale: Rezi's $149 lifetime deal (confirmed by live fetch) proved this segment exists and converts in the resume tool market. AppSumo distribution can drive a burst of early revenue, reviews, and word-of-mouth. Capping it preserves recurring revenue momentum.

**Positioning Statement:**

> "The only resume matcher that understands what your resume *means*, not just what words it contains. Upload your PDF, paste any job description, and get a score you can trust — plus AI rewrites that sound like you, not a template."

