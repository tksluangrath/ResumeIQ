from pydantic import BaseModel

from config import get_settings
from engine.extractor import ResumeEntities

SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "postgres": "postgresql",
    "psql": "postgresql",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "dl": "deep learning",
    "ai": "machine learning",
    "amazon web services": "aws",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "microsoft azure": "azure",
    "node": "node.js",
    "nodejs": "node.js",
    "react.js": "react",
    "reactjs": "react",
    "vue": "vue.js",
    "angularjs": "angular",
    "nextjs": "next.js",
    "nlp": "natural language processing",
    "tf": "tensorflow",
    "torch": "pytorch",
}


def _normalize_skill(skill: str) -> str:
    lower = skill.strip().lower()
    return SKILL_ALIASES.get(lower, lower)


LEVEL_KEYWORDS: list[str] = [
    "junior",
    "senior",
    "lead",
    "staff",
    "principal",
    "mid",
    "entry",
    "associate",
]

# Keyword signals for role archetype detection (adapted from career-ops _shared.md)
ARCHETYPES: dict[str, list[str]] = {
    "llmops": [
        "observability", "evals", "evaluation", "pipelines", "monitoring",
        "reliability", "llmops", "mlops", "tracing", "guardrails",
    ],
    "agentic": [
        "agent", "agentic", "hitl", "human-in-the-loop", "orchestration",
        "multi-agent", "workflow automation", "autonomous",
    ],
    "ai_pm": [
        "prd", "roadmap", "product discovery", "product manager",
        "product management", "stakeholder", "discovery",
    ],
    "solutions_architect": [
        "solutions architect", "systems design", "enterprise integration",
        "architecture", "technical design", "integration patterns",
    ],
    "forward_deployed": [
        "forward deployed", "client-facing", "field engineer",
        "customer deployment", "prototype", "fast delivery",
    ],
    "transformation": [
        "change management", "adoption", "enablement", "transformation",
        "organizational", "program management",
    ],
}


class SkillMatchResult(BaseModel):
    matched: list[str]
    missing: list[str]
    match_rate: float


class GapClassification(BaseModel):
    hard_blockers: list[str]   # missing skills that appear ≥2x in the JD
    nice_to_haves: list[str]   # missing skills mentioned once or fewer


class ScoreBreakdown(BaseModel):
    semantic_similarity: float
    skill_match: SkillMatchResult
    title_relevance: float
    experience_match: str


class MatchReport(BaseModel):
    overall_score: float
    breakdown: ScoreBreakdown
    gap_classification: GapClassification
    apply_recommendation: str   # "strong_match" | "good_match" | "borderline" | "skip"
    ats_keywords: list[str]     # top 15 missing keywords ranked by JD frequency
    role_archetype: str         # detected role category
    recommendations: list[str]


class MatchScorer:
    def __init__(self) -> None:
        settings = get_settings()
        self._weight_semantic: float = settings.WEIGHT_SEMANTIC
        self._weight_skills: float = settings.WEIGHT_SKILLS
        self._weight_title: float = settings.WEIGHT_TITLE
        self._weight_experience: float = settings.WEIGHT_EXPERIENCE

    def score(
        self,
        resume_entities: ResumeEntities,
        jd_entities: ResumeEntities,
        semantic_sim: float,
        jd_text: str = "",
    ) -> MatchReport:
        skill_result = self._compute_skill_match(
            resume_entities.skills, jd_entities.skills
        )
        title_relevance = self._compute_title_relevance(
            resume_entities.job_titles, jd_entities.job_titles
        )
        experience_match = self._compute_experience_match(
            resume_entities.job_titles, jd_entities.job_titles
        )

        skill_score = skill_result.match_rate
        title_score = title_relevance
        experience_score = _experience_level_score(experience_match)

        overall = (
            self._weight_semantic * semantic_sim
            + self._weight_skills * skill_score
            + self._weight_title * title_score
            + self._weight_experience * experience_score
        ) * 100

        overall = round(max(0.0, min(100.0, overall)), 2)

        gap_classification = _classify_gaps(skill_result.missing, jd_text)
        ats_keywords = _extract_ats_keywords(skill_result.missing, jd_text)
        role_archetype = _detect_archetype(jd_text)
        apply_recommendation = _apply_recommendation(overall)

        recommendations = self._generate_recommendations(
            skill_result, title_relevance, experience_match, resume_entities, jd_entities
        )

        breakdown = ScoreBreakdown(
            semantic_similarity=round(semantic_sim, 4),
            skill_match=skill_result,
            title_relevance=round(title_relevance, 4),
            experience_match=experience_match,
        )

        return MatchReport(
            overall_score=overall,
            breakdown=breakdown,
            gap_classification=gap_classification,
            apply_recommendation=apply_recommendation,
            ats_keywords=ats_keywords,
            role_archetype=role_archetype,
            recommendations=recommendations,
        )

    def _compute_skill_match(
        self, resume_skills: list[str], jd_skills: list[str]
    ) -> SkillMatchResult:
        if not jd_skills:
            return SkillMatchResult(matched=[], missing=[], match_rate=0.0)

        resume_lower = {_normalize_skill(s) for s in resume_skills}
        jd_lower = {_normalize_skill(s): s for s in jd_skills}

        matched: list[str] = []
        missing: list[str] = []

        for skill_lower, skill_original in jd_lower.items():
            if skill_lower in resume_lower:
                matched.append(skill_original)
            else:
                missing.append(skill_original)

        match_rate = len(matched) / len(jd_skills) if jd_skills else 0.0

        return SkillMatchResult(
            matched=matched,
            missing=missing,
            match_rate=round(match_rate, 4),
        )

    def _compute_title_relevance(
        self, resume_titles: list[str], jd_titles: list[str]
    ) -> float:
        if not resume_titles or not jd_titles:
            return 0.0

        resume_words: set[str] = set()
        for title in resume_titles:
            resume_words.update(title.lower().split())

        jd_words: set[str] = set()
        for title in jd_titles:
            jd_words.update(title.lower().split())

        if not jd_words:
            return 0.0

        overlap = resume_words & jd_words
        return len(overlap) / len(jd_words)

    def _compute_experience_match(
        self, resume_titles: list[str], jd_titles: list[str]
    ) -> str:
        resume_level = _detect_level(resume_titles)
        jd_level = _detect_level(jd_titles)

        if resume_level == "unknown" and jd_level == "unknown":
            return "level_not_detected"
        if resume_level == jd_level:
            return f"{jd_level}_match"
        if jd_level == "unknown":
            return f"{resume_level}_detected_no_jd_requirement"
        if resume_level == "unknown":
            return f"{jd_level}_required_level_not_detected_in_resume"
        return f"{jd_level}_required_{resume_level}_detected"


    def _generate_recommendations(
        self,
        skill_result: SkillMatchResult,
        title_relevance: float,
        experience_match: str,
        resume_entities: ResumeEntities,
        jd_entities: ResumeEntities,
    ) -> list[str]:
        recs: list[str] = []

        if skill_result.matched and skill_result.missing:
            matched_display = ", ".join(f"'{s}'" for s in skill_result.matched[:3])
            suffix = f" (+{len(skill_result.matched) - 3} more)" if len(skill_result.matched) > 3 else ""
            recs.append(f"Strong skill alignment: {matched_display}{suffix} match the job requirements.")

        top_missing = skill_result.missing[:5]
        for skill in top_missing:
            recs.append(f"Add '{skill}' — it appears in the job description but is not detected on your resume.")

        if title_relevance < 0.3 and jd_entities.job_titles:
            sample_title = jd_entities.job_titles[0] if jd_entities.job_titles else "the target role"
            recs.append(
                f"Align your job titles more closely with '{sample_title}' to improve title relevance."
            )

        if "required" in experience_match and "not_detected" in experience_match:
            level = experience_match.split("_")[0]
            recs.append(
                f"The job requires {level}-level experience. Ensure your resume highlights relevant seniority indicators."
            )
        elif "_detected_" in experience_match and "_required_" in experience_match:
            parts = experience_match.split("_required_")
            if len(parts) == 2:
                required_level = parts[0]
                detected_level = parts[1].replace("_detected", "")
                recs.append(
                    f"Job requires {required_level} level but your resume shows {detected_level} experience. "
                    "Emphasize leadership and ownership in your bullet points."
                )

        if len(skill_result.missing) > 5:
            remaining_count = len(skill_result.missing) - 5
            recs.append(
                f"You are missing {remaining_count} additional skills from the job description. "
                "Review the full missing skills list and add relevant experience."
            )

        return recs[:6]


def _detect_level(titles: list[str]) -> str:
    combined = " ".join(titles).lower()
    if any(kw in combined for kw in ("principal", "staff")):
        return "principal"
    if "lead" in combined:
        return "lead"
    if "senior" in combined or " sr " in combined or combined.startswith("sr ") or "sr." in combined:
        return "senior"
    if "junior" in combined or " jr " in combined or combined.startswith("jr "):
        return "junior"
    if "mid" in combined or "associate" in combined:
        return "mid"
    if "entry" in combined or "intern" in combined:
        return "entry"
    return "unknown"


def _experience_level_score(experience_match: str) -> float:
    if experience_match.endswith("_match"):
        return 1.0
    if "not_detected" in experience_match:
        return 0.5
    if "level_not_detected" in experience_match:
        return 0.5
    if "required" in experience_match and "detected" in experience_match:
        return 0.4
    return 0.6


def _detect_archetype(jd_text: str) -> str:
    if not jd_text:
        return "general"
    text_lower = jd_text.lower()
    scores: dict[str, int] = {
        archetype: sum(1 for kw in keywords if kw in text_lower)
        for archetype, keywords in ARCHETYPES.items()
    }
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "general"


def _classify_gaps(missing_skills: list[str], jd_text: str) -> GapClassification:
    if not jd_text:
        return GapClassification(hard_blockers=[], nice_to_haves=list(missing_skills))
    text_lower = jd_text.lower()
    hard_blockers: list[str] = []
    nice_to_haves: list[str] = []
    for skill in missing_skills:
        if text_lower.count(skill.lower()) >= 2:
            hard_blockers.append(skill)
        else:
            nice_to_haves.append(skill)
    return GapClassification(hard_blockers=hard_blockers, nice_to_haves=nice_to_haves)


def _extract_ats_keywords(missing_skills: list[str], jd_text: str, limit: int = 15) -> list[str]:
    if not jd_text:
        return missing_skills[:limit]
    text_lower = jd_text.lower()
    ranked = sorted(
        missing_skills,
        key=lambda s: text_lower.count(s.lower()),
        reverse=True,
    )
    return ranked[:limit]


def _apply_recommendation(score: float) -> str:
    if score >= 75:
        return "strong_match"
    if score >= 60:
        return "good_match"
    if score >= 45:
        return "borderline"
    return "skip"
