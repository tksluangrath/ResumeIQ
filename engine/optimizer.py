"""
Rule-based resume optimizer (Phase 1b).

Takes a MatchReport and the parsed ResumeData and returns an optimized
ResumeData with missing skills injected and weak bullets flagged.

No LLM is used here — that upgrade happens in Phase 3 via engine/llm/.
"""

from __future__ import annotations

import re
from copy import deepcopy

from engine.latex_builder import (
    ExperienceEntry,
    ProjectEntry,
    ResumeData,
    TechnicalSkills,
)
from engine.profile import UserProfile
from engine.scorer import MatchReport


# ---------------------------------------------------------------------------
# Skill → category mapping
# Used to insert missing skills into the right section of Technical Skills
# ---------------------------------------------------------------------------

_SKILL_CATEGORY_MAP: dict[str, str] = {
    # Programming & ML
    "Python": "Programming & Machine Learning",
    "R": "Programming & Machine Learning",
    "SQL": "Programming & Machine Learning",
    "PostgreSQL": "Programming & Machine Learning",
    "MySQL": "Programming & Machine Learning",
    "scikit-learn": "Programming & Machine Learning",
    "XGBoost": "Programming & Machine Learning",
    "pandas": "Programming & Machine Learning",
    "NumPy": "Programming & Machine Learning",
    "Matplotlib": "Programming & Machine Learning",
    "Seaborn": "Programming & Machine Learning",
    "Machine Learning": "Programming & Machine Learning",
    "Statistical analysis": "Programming & Machine Learning",
    # Data Science & AI
    "Deep Learning": "Data Science & AI",
    "LLMs": "Data Science & AI",
    "LangChain": "Data Science & AI",
    "TensorFlow": "Data Science & AI",
    "PyTorch": "Data Science & AI",
    "Statistical modeling": "Data Science & AI",
    "Feature engineering": "Data Science & AI",
    "Time series analysis": "Data Science & AI",
    "Anomaly detection": "Data Science & AI",
    "RAG": "Data Science & AI",
    "NLP": "Data Science & AI",
    "FastAPI": "Data Science & AI",
    "Flask": "Data Science & AI",
    "REST API": "Data Science & AI",
    # Tools & Platforms
    "Git": "Tools & Platforms",
    "Docker": "Tools & Platforms",
    "Kubernetes": "Tools & Platforms",
    "AWS": "Tools & Platforms",
    "GCP": "Tools & Platforms",
    "Azure": "Tools & Platforms",
    "Streamlit": "Tools & Platforms",
    "Jupyter Notebooks": "Tools & Platforms",
    "Tableau": "Tools & Platforms",
    "Excel": "Tools & Platforms",
    "ChromaDB": "Tools & Platforms",
    "SQLite": "Tools & Platforms",
    "Redis": "Tools & Platforms",
    "MongoDB": "Tools & Platforms",
    "Elasticsearch": "Tools & Platforms",
    "Spark": "Tools & Platforms",
    "Kafka": "Tools & Platforms",
    "Airflow": "Tools & Platforms",
    "Terraform": "Tools & Platforms",
    "Linux": "Tools & Platforms",
    "GraphQL": "Tools & Platforms",
    "React": "Tools & Platforms",
    "TypeScript": "Tools & Platforms",
    "JavaScript": "Tools & Platforms",
    "Node.js": "Tools & Platforms",
}

_DEFAULT_CATEGORY = "Tools & Platforms"


# ---------------------------------------------------------------------------
# Weakness detection heuristics
# ---------------------------------------------------------------------------

_WEAK_PATTERNS = [
    r"^worked on\b",
    r"^helped (with|to)\b",
    r"^assisted\b",
    r"^responsible for\b",
    r"^involved in\b",
    r"^participated in\b",
    r"^contributed to\b",
]

_STRONG_VERBS = [
    "Developed", "Built", "Designed", "Implemented", "Led", "Engineered",
    "Architected", "Created", "Delivered", "Optimized", "Reduced", "Increased",
    "Automated", "Deployed", "Improved", "Analyzed", "Managed", "Launched",
]


def _is_weak_bullet(bullet: str) -> bool:
    text = bullet.strip().lower()
    return any(re.match(p, text) for p in _WEAK_PATTERNS)


def _lacks_metric(bullet: str) -> bool:
    """Returns True if the bullet has no quantified result."""
    return not re.search(r"\d+[\%\+xX]?|\$[\d,]+|[\d,]+ [a-z]+", bullet)


# ---------------------------------------------------------------------------
# Core optimizer
# ---------------------------------------------------------------------------

class OptimizationResult:
    """Container for the optimizer's output."""

    def __init__(
        self,
        resume: ResumeData,
        injected_skills: list[str],
        weak_bullets: list[dict[str, str]],
        notes: list[str],
    ) -> None:
        self.resume = resume
        self.injected_skills = injected_skills   # skills that were added
        self.weak_bullets = weak_bullets         # [{"section": ..., "bullet": ...}]
        self.notes = notes                       # human-readable change log


def optimize(
    report: MatchReport,
    resume: ResumeData,
    profile: UserProfile | None = None,
) -> OptimizationResult:
    """
    Apply rule-based optimizations to a resume based on a match report.

    Rules applied:
      1. Inject missing skills into the Technical Skills section.
         If a UserProfile is provided, only inject skills the user has confirmed.
         Unconfirmed missing skills are flagged as suggestions instead.
      2. Flag weak bullet points (passive language, no metrics).
         If a UserProfile is provided, surface relevant accomplishments as hints.
      3. Add a note for each change so the user understands what changed.

    Args:
        report:  MatchReport from scorer.py (contains missing skills).
        resume:  Parsed ResumeData from latex_builder.parse_tex_to_resume_data().
        profile: Optional UserProfile for personalized suggestions.

    Returns:
        OptimizationResult with the modified ResumeData and a change log.
    """
    optimized = deepcopy(resume)
    injected: list[str] = []
    weak_bullets: list[dict[str, str]] = []
    notes: list[str] = []

    # --- Rule 1: Inject missing skills ---
    missing = report.breakdown.skill_match.missing
    if missing and profile is not None:
        # With a profile: only inject skills the user actually has.
        confirmed = [s for s in missing if profile.has_skill(s)]
        unconfirmed = [s for s in missing if not profile.has_skill(s)]

        if confirmed:
            optimized.skills, newly_added = _inject_skills(optimized.skills, confirmed)
            injected.extend(newly_added)
            notes.append(
                f"Added {len(newly_added)} confirmed skill(s) from your profile: "
                + ", ".join(newly_added)
            )
        if unconfirmed:
            notes.append(
                f"Suggested skill(s) required by this JD but not in your profile "
                f"(add them if you have experience): {', '.join(unconfirmed)}"
            )
    elif missing:
        # No profile: inject everything that's missing (original behaviour)
        optimized.skills, newly_added = _inject_skills(optimized.skills, missing)
        injected.extend(newly_added)
        if newly_added:
            notes.append(
                f"Added {len(newly_added)} missing skill(s) to Technical Skills: "
                + ", ".join(newly_added)
            )

    # --- Rule 2: Flag weak bullets across experience ---
    for job in optimized.experience:
        for bullet in job.bullets:
            entry: dict[str, str] = {"section": "Experience", "company": job.company, "bullet": bullet}
            if _is_weak_bullet(bullet):
                weak_bullets.append(entry)
            elif _lacks_metric(bullet):
                hint = ""
                if profile:
                    evidence = profile.find_evidence(job.company)
                    if evidence:
                        hint = f" Hint from your profile: {evidence[0]}"
                weak_bullets.append({**entry, "bullet": f"[no metric] {bullet}{hint}"})

    # --- Rule 3: Flag weak bullets in projects ---
    for project in optimized.projects:
        for bullet in project.bullets:
            if _is_weak_bullet(bullet):
                entry = {"section": "Projects", "project": project.name, "bullet": bullet}
                if profile:
                    evidence = profile.find_evidence(project.name)
                    if evidence:
                        entry["hint"] = evidence[0]
                weak_bullets.append(entry)

    if weak_bullets:
        notes.append(
            f"Flagged {len(weak_bullets)} bullet(s) that may benefit from stronger action verbs "
            f"or quantified results. Suggested verbs: {', '.join(_STRONG_VERBS[:6])}."
        )

    # --- Rule 4: Score context note ---
    notes.append(
        f"Overall match score before optimization: {report.overall_score:.1f}/100. "
        f"Skill match rate: {report.breakdown.skill_match.match_rate:.0%}."
    )

    if profile and profile.target_roles:
        roles = ", ".join(profile.target_roles)
        notes.append(f"Profile target roles: {roles}. Tailor your summary to speak directly to these.")

    return OptimizationResult(
        resume=optimized,
        injected_skills=injected,
        weak_bullets=weak_bullets,
        notes=notes,
    )


def _inject_skills(skills: TechnicalSkills, missing: list[str]) -> tuple[TechnicalSkills, list[str]]:
    """
    Add missing skills to the appropriate category in TechnicalSkills.

    Returns updated TechnicalSkills and the list of skills actually added
    (skips skills that are already present).
    """
    categories = dict(skills.categories)  # mutable copy
    added: list[str] = []

    # Build a flat lowercase set of existing skills for dedup check
    existing_lower = {
        s.strip().lower()
        for items in categories.values()
        for s in items.split(",")
    }

    for skill in missing:
        if skill.strip().lower() in existing_lower:
            continue  # already there

        category = _SKILL_CATEGORY_MAP.get(skill, _DEFAULT_CATEGORY)

        # Only inject into existing categories — never create new sections.
        # If the target category isn't present, fall back to the last category.
        if category not in categories:
            category = next(reversed(categories))

        categories[category] = categories[category].rstrip(", ") + f", {skill}"
        existing_lower.add(skill.strip().lower())
        added.append(skill)

    return TechnicalSkills(categories=categories), added
