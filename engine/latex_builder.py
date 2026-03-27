"""
LaTeX resume builder.

Populates templates/resume_base.tex.j2 with structured resume data,
compiles to PDF via pdflatex, and returns the output path.

Uses custom Jinja2 delimiters (<< >>, <% %>) to avoid clashing with
LaTeX braces and percent signs.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ContactInfo(BaseModel):
    name: str
    location: str
    phone: str
    email: str
    linkedin: str | None = None   # just the handle, e.g. "terranceluangrath"
    github: str | None = None     # full domain path, e.g. "tksluangrath.github.io"


class EducationEntry(BaseModel):
    institution: str
    location: str
    degree: str
    dates: str
    coursework: list[str] = []


class ExperienceEntry(BaseModel):
    title: str
    dates: str
    company: str
    location: str
    bullets: list[str]


class ProjectEntry(BaseModel):
    name: str
    technologies: str
    url: str | None = None
    date: str
    bullets: list[str]


class TechnicalSkills(BaseModel):
    # Ordered dict: category label → comma-separated items
    # e.g. {"Programming & Machine Learning": "Python, SQL, ..."}
    categories: dict[str, str]


class ResumeData(BaseModel):
    contact: ContactInfo
    education: list[EducationEntry]
    experience: list[ExperienceEntry]
    projects: list[ProjectEntry]
    skills: TechnicalSkills


# ---------------------------------------------------------------------------
# LaTeX character escaping
# ---------------------------------------------------------------------------

_LATEX_ESCAPE = [
    ("\\", r"\textbackslash{}"),   # must be first
    ("&",  r"\&"),
    ("%",  r"\%"),
    ("$",  r"\$"),
    ("#",  r"\#"),
    ("_",  r"\_"),
    ("{",  r"\{"),
    ("}",  r"\}"),
    ("~",  r"\textasciitilde{}"),
    ("^",  r"\textasciicircum{}"),
]


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in user-supplied strings."""
    # Replace backslash with a null-byte placeholder first so the subsequent
    # { } escapes don't corrupt the \textbackslash{} we're about to insert.
    _PLACEHOLDER = "\x00BSLASH\x00"
    result = text.replace("\\", _PLACEHOLDER)
    for char, replacement in _LATEX_ESCAPE[1:]:  # skip backslash entry
        result = result.replace(char, replacement)
    return result.replace(_PLACEHOLDER, r"\textbackslash{}")


def unescape_latex(text: str) -> str:
    """Reverse common LaTeX escapes back to plain text.

    Called when extracting data FROM .tex source files so that ResumeData
    holds plain strings. escape_latex() is then applied exactly once when
    rendering back to LaTeX via _escape_data().
    """
    # Named commands first (before bare \{ \} to avoid orphaned braces)
    result = text
    result = result.replace(r"\textbackslash{}", "\\")
    result = result.replace(r"\textasciitilde{}", "~")
    result = result.replace(r"\textasciicircum{}", "^")
    # Single-character escapes
    result = result.replace(r"\&", "&")
    result = result.replace(r"\%", "%")
    result = result.replace(r"\$", "$")
    result = result.replace(r"\#", "#")
    result = result.replace(r"\_", "_")
    result = result.replace(r"\{", "{")
    result = result.replace(r"\}", "}")
    return result


def _escape_data(data: ResumeData) -> ResumeData:
    """Return a new ResumeData with all string fields LaTeX-escaped."""

    def esc(s: str) -> str:
        return escape_latex(s)

    def esc_list(lst: list[str]) -> list[str]:
        return [esc(item) for item in lst]

    return ResumeData(
        contact=ContactInfo(
            name=esc(data.contact.name),
            location=esc(data.contact.location),
            phone=esc(data.contact.phone),
            email=data.contact.email,          # emails go in \href, keep raw
            linkedin=data.contact.linkedin,    # goes in \href, keep raw
            github=data.contact.github,        # goes in \href, keep raw
        ),
        education=[
            EducationEntry(
                institution=esc(e.institution),
                location=esc(e.location),
                degree=esc(e.degree),
                dates=esc(e.dates),
                coursework=esc_list(e.coursework),
            )
            for e in data.education
        ],
        experience=[
            ExperienceEntry(
                title=esc(j.title),
                dates=esc(j.dates),
                company=esc(j.company),
                location=esc(j.location),
                bullets=esc_list(j.bullets),
            )
            for j in data.experience
        ],
        projects=[
            ProjectEntry(
                name=esc(p.name),
                technologies=esc(p.technologies),
                url=p.url,                     # goes in \href, keep raw
                date=esc(p.date),
                bullets=esc_list(p.bullets),
            )
            for p in data.projects
        ],
        skills=TechnicalSkills(
            categories={esc(k): esc(v) for k, v in data.skills.categories.items()}
        ),
    )


# ---------------------------------------------------------------------------
# Jinja2 environment
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _make_jinja_env() -> Environment:
    """Create a Jinja2 environment with LaTeX-safe delimiters."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        # Custom delimiters so LaTeX braces and % don't conflict
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_latex(data: ResumeData) -> str:
    """Render resume data to a LaTeX string without compiling."""
    escaped = _escape_data(data)
    env = _make_jinja_env()
    template = env.get_template("resume_base.tex.j2")
    return template.render(
        contact=escaped.contact,
        education=escaped.education,
        experience=escaped.experience,
        projects=escaped.projects,
        skills=escaped.skills,
    )


def build_pdf(
    data: ResumeData,
    output_path: str | Path,
    keep_tex: bool = False,
) -> Path:
    """
    Compile resume data to a PDF.

    Args:
        data:        Structured resume content.
        output_path: Where to save the final .pdf file.
        keep_tex:    If True, also save the intermediate .tex file alongside the PDF.

    Returns:
        Path to the compiled PDF.

    Raises:
        RuntimeError: If pdflatex is not found or compilation fails.
        FileNotFoundError: If the template file is missing.
    """
    if not shutil.which("pdflatex"):
        raise RuntimeError(
            "pdflatex not found. Install TeX Live (Mac: `brew install --cask mactex-no-gui`) "
            "or BasicTeX (`brew install basictex`)."
        )

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    latex_source = render_latex(data)

    # Compile in a temp directory to keep aux/log files isolated
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tex_file = tmp / "resume.tex"
        tex_file.write_text(latex_source, encoding="utf-8")

        # Run pdflatex twice — second pass resolves internal references
        cmd = ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, str(tex_file)]
        for _ in range(2):
            result = subprocess.run(cmd, capture_output=True, text=True)

        pdf_tmp = tmp / "resume.pdf"
        if not pdf_tmp.exists():
            log = (tmp / "resume.log").read_text(encoding="utf-8", errors="replace") if (tmp / "resume.log").exists() else result.stderr
            raise RuntimeError(
                f"pdflatex compilation failed.\n\nLast 50 lines of log:\n"
                + "\n".join(log.splitlines()[-50:])
            )

        # Move PDF to final destination
        shutil.copy2(pdf_tmp, output_path)

        # Optionally save .tex alongside PDF
        if keep_tex:
            tex_dest = output_path.with_suffix(".tex")
            shutil.copy2(tex_file, tex_dest)

    return output_path


# ---------------------------------------------------------------------------
# Parse original resume.tex → ResumeData
# ---------------------------------------------------------------------------

def parse_tex_to_resume_data(tex_path: str | Path) -> ResumeData:
    """
    Parse Terrance's existing resume_template.tex into a ResumeData object.

    This is a targeted parser for the Jake Gutierrez template structure.
    It handles the specific commands: \\resumeSubheading, \\resumeProjectHeading,
    \\resumeItem, and the skills itemize block.
    """
    tex = Path(tex_path).read_text(encoding="utf-8")

    # --- Contact ---
    contact = _parse_contact(tex)

    # --- Education ---
    edu_section = _extract_section(tex, "Education")
    education = _parse_education(edu_section)

    # --- Experience ---
    exp_section = _extract_section(tex, "Experience")
    experience = _parse_experience(exp_section)

    # --- Projects ---
    proj_section = _extract_section(tex, "Projects")
    projects = _parse_projects(proj_section)

    # --- Skills ---
    skills_section = _extract_section(tex, "Technical Skills")
    skills = _parse_skills(skills_section)

    return ResumeData(
        contact=contact,
        education=education,
        experience=experience,
        projects=projects,
        skills=skills,
    )


def _extract_section(tex: str, section_name: str) -> str:
    """Extract content between \\section{Name} and the next \\section{...}."""
    pattern = rf"\\section\{{{re.escape(section_name)}\}}(.*?)(?=\\section\{{|\\end\{{document\}})"
    match = re.search(pattern, tex, re.DOTALL)
    return match.group(1).strip() if match else ""


def _parse_contact(tex: str) -> ContactInfo:
    """Extract contact block from the \\begin{center}...\\end{center} header."""
    center = re.search(r"\\begin\{center\}(.*?)\\end\{center\}", tex, re.DOTALL)
    block = center.group(1) if center else tex

    name_m = re.search(r"\\scshape\s+(.+?)}", block)
    name = name_m.group(1).strip() if name_m else ""

    location_m = re.search(r"\\small\s+([^$]+?)\s+\$\|", block)
    location = location_m.group(1).strip() if location_m else ""

    phone_m = re.search(r"\|\s*([\d\-]+)\s*\$\|", block)
    phone = phone_m.group(1).strip() if phone_m else ""

    email_m = re.search(r"mailto:([^\}]+)", block)
    email = email_m.group(1).strip() if email_m else ""

    linkedin_m = re.search(r"linkedin\.com/in/([^\}]+)", block)
    linkedin = linkedin_m.group(1).strip() if linkedin_m else None

    github_m = re.search(r"https?://([^\}]*github[^\}]*)", block)
    github = github_m.group(1).strip() if github_m else None

    return ContactInfo(
        name=name, location=location, phone=phone,
        email=email, linkedin=linkedin, github=github,
    )


def _parse_bullets(block: str) -> list[str]:
    """Extract \\resumeItem{...} bullets from a block."""
    return [
        unescape_latex(m.strip())
        for m in re.findall(r"\\resumeItem\{((?:[^{}]|\{[^{}]*\})*)\}", block)
    ]


def _parse_education(section: str) -> list[EducationEntry]:
    entries = []
    pattern = r"\\resumeSubheading\s*\{([^}]*)\}\{([^}]*)\}\s*\{([^}]*)\}\{([^}]*)\}(.*?)(?=\\resumeSubheading|\\resumeSubHeadingListEnd)"
    for m in re.finditer(pattern, section, re.DOTALL):
        institution, location, degree, dates, rest = m.groups()
        coursework = _parse_bullets(rest)
        entries.append(EducationEntry(
            institution=unescape_latex(institution.strip()),
            location=unescape_latex(location.strip()),
            degree=unescape_latex(degree.strip()),
            dates=unescape_latex(dates.strip()),
            coursework=coursework,
        ))
    return entries


def _parse_experience(section: str) -> list[ExperienceEntry]:
    entries = []
    pattern = r"\\resumeSubheading\s*\{([^}]*)\}\{([^}]*)\}\s*\{([^}]*)\}\{([^}]*)\}(.*?)(?=\\resumeSubheading|\\resumeSubHeadingListEnd)"
    for m in re.finditer(pattern, section, re.DOTALL):
        title, dates, company, location, rest = m.groups()
        entries.append(ExperienceEntry(
            title=unescape_latex(title.strip()),
            dates=unescape_latex(dates.strip()),
            company=unescape_latex(company.strip()),
            location=unescape_latex(location.strip()),
            bullets=_parse_bullets(rest),
        ))
    return entries


def _extract_balanced_braces(text: str, start: int) -> tuple[str, int]:
    """Return (content_inside_braces, index_after_closing_brace).

    Handles arbitrary nesting depth. Starts at the opening '{' at `start`.
    """
    assert text[start] == "{", f"Expected '{{' at pos {start}, got {text[start]!r}"
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
    raise ValueError(f"Unbalanced braces starting at position {start}")


def _parse_projects(section: str) -> list[ProjectEntry]:
    entries = []
    # Find each \resumeProjectHeading using a brace-balanced extractor so that
    # nested commands like \href{url}{\underline{text}} are handled correctly.
    pattern = r"\\resumeProjectHeading\s*"
    for m in re.finditer(pattern, section):
        pos = m.end()
        if pos >= len(section) or section[pos] != "{":
            continue

        try:
            heading_raw, pos = _extract_balanced_braces(section, pos)
            # Skip whitespace between the two argument groups
            while pos < len(section) and section[pos] in " \t\n":
                pos += 1
            if pos >= len(section) or section[pos] != "{":
                continue
            date, pos = _extract_balanced_braces(section, pos)
        except (ValueError, AssertionError):
            continue

        # Everything after the heading until the next \resumeProjectHeading
        # or \resumeSubHeadingListEnd is the bullet block.
        next_m = re.search(r"\\resumeProjectHeading|\\resumeSubHeadingListEnd", section[pos:])
        rest = section[pos : pos + next_m.start()] if next_m else section[pos:]

        # Extract project name from \textbf{...}
        name_m = re.search(r"\\textbf\{([^}]+)\}", heading_raw)
        name = name_m.group(1).strip() if name_m else heading_raw.strip()

        # Extract technologies from \emph{...}
        tech_m = re.search(r"\\emph\{([^}]+)\}", heading_raw)
        technologies = tech_m.group(1).strip() if tech_m else ""

        # Extract URL — first argument of \href{url}{...}
        url_m = re.search(r"\\href\{([^}]+)\}", heading_raw)
        url = url_m.group(1).strip() if url_m else None

        entries.append(ProjectEntry(
            name=name,
            technologies=technologies,
            url=url,
            date=date.strip(),
            bullets=_parse_bullets(rest),
        ))
    return entries


def _parse_skills(section: str) -> TechnicalSkills:
    categories: dict[str, str] = {}
    # Match \textbf{Category}{: items}
    for m in re.finditer(r"\\textbf\{([^}]+)\}\{:\s*([^}\\]+)\}", section):
        key = unescape_latex(m.group(1).strip())
        value = unescape_latex(m.group(2).strip().rstrip("\\").strip())
        categories[key] = value
    return TechnicalSkills(categories=categories)
