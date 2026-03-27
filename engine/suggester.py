from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict

from engine.llm.base import BaseLLM
from engine.optimizer import _WEAK_PATTERNS, _lacks_metric
from engine.profile import UserProfile
from engine.scorer import MatchReport


class BulletRewrite(BaseModel):
    model_config = ConfigDict(frozen=True)

    original: str
    rewritten: str
    section: str
    context: str


class SuggestionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    bullet_rewrites: list[BulletRewrite]
    skill_gaps: list[str]
    injected_keywords: list[str]
    career_summary: str
    provider: str


def _parse_json_list(text: str) -> list[str]:
    stripped = text.strip()

    # Strip markdown code fences before attempting JSON parse
    stripped = re.sub(r"^```[a-z]*\n?", "", stripped, flags=re.MULTILINE)
    stripped = stripped.replace("```", "").strip()

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, str) and item.strip()]
    except (json.JSONDecodeError, TypeError):
        pass

    lines = stripped.splitlines()
    results: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^[\s\-\*\d\.\)]+", "", line).strip()
        if cleaned:
            results.append(cleaned)
    return results


def _detect_weak_bullets(resume_text: str) -> list[dict[str, str]]:
    bullets: list[dict[str, str]] = []
    for line in resume_text.splitlines():
        line = line.strip()
        if not line:
            continue
        text_lower = line.lower()
        is_weak = any(re.match(p, text_lower) for p in _WEAK_PATTERNS)
        if is_weak or _lacks_metric(line):
            bullets.append({"section": "Experience", "context": "", "bullet": line})
        if len(bullets) >= 5:
            break
    return bullets


def suggest(
    resume_text: str,
    job_description: str,
    report: MatchReport,
    llm: BaseLLM,
    profile: UserProfile | None = None,
    weak_bullets: list[dict[str, str]] | None = None,
) -> SuggestionResult:
    if weak_bullets is None:
        weak_bullets = _detect_weak_bullets(resume_text)

    rewrites = _rewrite_bullets(weak_bullets, llm, profile)
    skill_gaps = _analyze_skill_gaps(report, job_description, llm)
    injected_keywords = _suggest_keywords(report, job_description, llm)
    career_summary = _generate_career_summary(resume_text, report, llm, profile)

    return SuggestionResult(
        bullet_rewrites=rewrites,
        skill_gaps=skill_gaps,
        injected_keywords=injected_keywords,
        career_summary=career_summary,
        provider=llm.provider_name,
    )


def _rewrite_bullets(
    weak_bullets: list[dict[str, str]],
    llm: BaseLLM,
    profile: UserProfile | None,
) -> list[BulletRewrite]:
    rewrites: list[BulletRewrite] = []

    for entry in weak_bullets[:5]:
        section = entry.get("section", "Experience")
        context = entry.get("context", "")
        bullet = entry["bullet"]

        evidence = profile.find_evidence(context)[:3] if profile else []
        tone = profile.preferred_tone if profile else "professional"
        avoid = profile.avoid_phrases if profile else []

        prompt = (
            "You are an expert resume writer helping a job seeker improve their resume bullets.\n\n"
            "Context:\n"
            f"- Section: {section}\n"
            f"- Company/Project: {context}\n"
            f"- Target tone: {tone}\n"
            f"- Avoid these phrases: {avoid}\n"
            f"- Evidence from profile: {evidence}\n\n"
            "Bullet to improve:\n"
            f"{bullet}\n\n"
            "Rewrite this bullet using a strong action verb, specific details, and a quantified result where possible.\n"
            "Write one sentence only. Do not wrap your response in markdown code fences."
        )

        rewritten = llm.complete(prompt)
        rewrites.append(
            BulletRewrite(
                original=bullet,
                rewritten=rewritten,
                section=section,
                context=context,
            )
        )

    return rewrites


def _analyze_skill_gaps(
    report: MatchReport,
    job_description: str,
    llm: BaseLLM,
) -> list[str]:
    prompt = (
        "You are a career coach analyzing skill gaps between a resume and job description.\n\n"
        f"Missing skills from job description: {report.breakdown.skill_match.missing}\n"
        f"Candidate's current skills: {report.breakdown.skill_match.matched}\n"
        f"Job description excerpt: {job_description[:500]}\n\n"
        "List up to 5 specific, actionable skill gaps as a JSON array of strings.\n"
        "Each string should be one sentence explaining what the candidate is missing and why it matters for this role.\n"
        'Example: ["The role requires PostgreSQL experience but the resume only shows MySQL — consider highlighting any relational DB transferability.", ...]\n'
        "Do not wrap your response in markdown code fences."
    )

    response = llm.complete(prompt)
    return _parse_json_list(response)


def _suggest_keywords(
    report: MatchReport,
    job_description: str,
    llm: BaseLLM,
) -> list[str]:
    prompt = (
        "You are an ATS optimization expert helping improve resume keyword coverage.\n\n"
        f"Job description: {job_description[:2000]}\n"
        f"Skills already in resume: {report.breakdown.skill_match.matched}\n"
        f"Missing skills: {report.breakdown.skill_match.missing[:10]}\n\n"
        "Return up to 10 ATS-relevant keywords or phrases from the job description that the candidate should weave into their resume.\n"
        "Return as a JSON array of strings. Prefer exact phrases from the job description.\n"
        "Do not wrap your response in markdown code fences."
    )

    response = llm.complete(prompt)
    return _parse_json_list(response)


def _generate_career_summary(
    resume_text: str,
    report: MatchReport,
    llm: BaseLLM,
    profile: UserProfile | None,
) -> str:
    current_summary = (
        profile.career_summary
        if profile and profile.career_summary
        else resume_text[:300]
    )
    target_roles = profile.target_roles if profile else []
    tone = profile.preferred_tone if profile else "professional"

    prompt = (
        "You are an expert resume writer crafting a professional career summary.\n\n"
        f"Current summary or background: {current_summary}\n"
        f"Target roles: {target_roles}\n"
        f"Tone: {tone}\n"
        f"Top matched skills for this role: {report.breakdown.skill_match.matched[:8]}\n"
        f"Key missing skills to address: {report.breakdown.skill_match.missing[:3]}\n\n"
        "Write a 2-3 sentence professional career summary that positions the candidate for this role.\n"
        "Focus on their strengths and briefly acknowledge growth areas.\n"
        'Write in first-person-implied style (no "I"). Do not wrap your response in markdown code fences.'
    )

    return llm.complete(prompt)
