"""
User profile for personalized resume optimization.

Stores detailed context about a user's actual experience, projects, and skills
so the optimizer (and Phase 3 LLM layer) can produce tailored, specific content
rather than generic AI-generated text.

Usage:
    profile = UserProfile.from_json("my_profile.json")
    result = optimize(report, resume_data, profile=profile)
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class WorkDetail(BaseModel):
    """Detailed record of a single work experience."""

    company: str
    title: str
    dates: str
    location: str = ""
    # Specific accomplishments — write these with metrics when you have them.
    # e.g. "Reduced dashboard load time by 40% by rewriting SQL aggregation queries"
    accomplishments: list[str] = Field(default_factory=list)
    # Technologies actually used in this role (not just listed on resume)
    technologies: list[str] = Field(default_factory=list)
    team_size: int | None = None
    promoted: bool = False


class ProjectDetail(BaseModel):
    """Detailed record of a project."""

    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    # Specific outcomes / results with numbers when available
    # e.g. "Achieved 92% accuracy on held-out test set", "Deployed to 500 beta users"
    outcomes: list[str] = Field(default_factory=list)
    url: str | None = None


class SkillEntry(BaseModel):
    """A skill with self-assessed proficiency."""

    name: str
    proficiency: str = "intermediate"  # "beginner" | "intermediate" | "expert"
    years: float | None = None         # years of hands-on use


class UserProfile(BaseModel):
    """
    Persistent user profile that drives personalized resume optimization.

    The optimizer uses this to:
    - Only inject skills the user actually has (confirmed_skill_names())
    - Surface specific accomplishments that demonstrate a required skill
    - Generate targeted bullet suggestions grounded in real experience

    In Phase 3, this profile feeds directly into LLM prompts to produce
    voice-preserving rewrites rather than generic AI output.
    """

    full_name: str = ""
    # Roles you're targeting — helps filter which skills to emphasize
    target_roles: list[str] = Field(default_factory=list)
    # 2-3 sentences in your own words about your background and what you bring
    career_summary: str = ""

    work_history: list[WorkDetail] = Field(default_factory=list)
    projects: list[ProjectDetail] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)

    # Writing preferences used by the Phase 3 LLM layer
    preferred_tone: str = "professional"   # "professional" | "technical" | "direct"
    avoid_phrases: list[str] = Field(default_factory=list)

    # ---------------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------------

    def confirmed_skill_names(self) -> list[str]:
        """Return all skill names in the profile (case-preserved)."""
        return [s.name for s in self.skills]

    def has_skill(self, skill: str) -> bool:
        """Case-insensitive check for whether the profile contains a skill."""
        skill_lower = skill.lower()
        return any(s.name.lower() == skill_lower for s in self.skills)

    def find_evidence(self, skill: str) -> list[str]:
        """
        Return work/project entries that demonstrate a skill.

        Returns a list of plain-English context strings, e.g.:
          "[Optum - Data Analyst] Reduced query time by 40% using optimized SQL"
          "[Project: LLM Resume Matcher] Deployed FastAPI endpoint serving 200 req/s"
        """
        skill_lower = skill.lower()
        evidence: list[str] = []

        for work in self.work_history:
            if any(skill_lower in t.lower() for t in work.technologies):
                for acc in work.accomplishments:
                    evidence.append(f"[{work.company} – {work.title}] {acc}")

        for project in self.projects:
            if any(skill_lower in t.lower() for t in project.technologies):
                for outcome in project.outcomes:
                    evidence.append(f"[Project: {project.name}] {outcome}")

        return evidence

    # ---------------------------------------------------------------------------
    # I/O
    # ---------------------------------------------------------------------------

    @classmethod
    def from_json(cls, path: str | Path) -> "UserProfile":
        """Load a UserProfile from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def to_json(self, path: str | Path, indent: int = 2) -> None:
        """Save this UserProfile to a JSON file."""
        Path(path).write_text(
            self.model_dump_json(indent=indent),
            encoding="utf-8",
        )
