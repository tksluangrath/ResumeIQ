from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path

# Ensure the project root is on sys.path so `engine` is importable
# regardless of where Streamlit is launched from.
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards

from engine.profile import ProjectDetail, SkillEntry, UserProfile, WorkDetail
from engine.scorer import ScoreBreakdown, _experience_level_score

_MIN_JD_LENGTH: int = 50

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ResumeIQ",
    page_icon=":page_facing_up:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state — profile lists
# ---------------------------------------------------------------------------

# profile lists store dicts with keys matching WorkDetail / ProjectDetail / SkillEntry fields
if "profile_skills" not in st.session_state:
    st.session_state.profile_skills = []
if "profile_work" not in st.session_state:
    st.session_state.profile_work = []
if "profile_projects" not in st.session_state:
    st.session_state.profile_projects = []
if "saved_profile_json" not in st.session_state:
    st.session_state.saved_profile_json = ""

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Settings", divider="blue")
    api_url = st.text_input("API base URL", value="http://localhost:8000")
    st.space(1)
    if st.button("Check API Health", use_container_width=True):
        try:
            resp = requests.get(f"{api_url}/health", timeout=5)
            if resp.ok:
                data = resp.json()
                st.success(f"Online · v{data.get('version', '?')} · {data.get('env', '?')}")
            else:
                st.error(f"API returned {resp.status_code}")
        except requests.exceptions.RequestException as exc:
            st.error(f"Cannot reach API: {exc}")

    st.space(2)
    if st.session_state.saved_profile_json:
        st.success("Profile saved")
    else:
        st.info("No profile saved yet")
    st.caption("Phase 2 MVP · FastAPI + Streamlit")

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------

st.title("AI-Powered Resume & Job Match Engine", anchor=False)
st.caption("Score your resume against any job description — then get an improved LaTeX draft.")
st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_match, tab_improve, tab_suggest, tab_profile = st.tabs([
    "Match Resume",
    "Improve Resume",
    "AI Suggestions",
    "My Profile",
])


# ── Shared helpers ──────────────────────────────────────────────────────────

def _score_color(score: float) -> str:
    if score >= 80:
        return "#21c354"
    if score >= 65:
        return "#9AD8E1"
    if score >= 40:
        return "#f5a623"
    return "#e05c5c"


def _render_score_section(
    overall: float,
    breakdown: ScoreBreakdown | dict,
    recommendations: list[str],
    processing_ms: int,
) -> None:
    if hasattr(breakdown, "model_dump"):
        breakdown = breakdown.model_dump()

    skill_match: dict = breakdown.get("skill_match") or {}

    sub_scores: list[tuple[str, float]] = [
        ("Semantic",   breakdown.get("semantic_similarity", 0.0)),
        ("Skills",     skill_match.get("match_rate", 0.0)),
        ("Title",      breakdown.get("title_relevance", 0.0)),
        ("Experience", _experience_level_score(breakdown.get("experience_match", "level_not_detected"))),
    ]

    cols = st.columns(5)
    with cols[0]:
        st.metric("Overall Match", f"{overall:.1f}%")
    for i, (label, raw) in enumerate(sub_scores, start=1):
        pct = raw * 100 if raw <= 1.0 else raw
        with cols[i]:
            st.metric(label, f"{pct:.1f}%")
    style_metric_cards(
        background_color="#0e1117",
        border_size_px=1,
        border_color="#333",
        border_radius_px=8,
        border_left_color=_score_color(overall),
        box_shadow=True,
    )
    st.space(1)
    st.progress(overall / 100, text=f"Match score: {overall:.1f}%")
    st.caption(f"Processed in {processing_ms} ms")

    matched_skills: list[str] = skill_match.get("matched") or []
    missing_skills: list[str] = skill_match.get("missing") or []

    if matched_skills or missing_skills:
        st.space(1)
        col_m, col_x = st.columns(2)
        with col_m:
            with st.expander(f"Matched skills ({len(matched_skills)})", expanded=False):
                if matched_skills:
                    st.markdown(" ".join(f"`{s}`" for s in sorted(matched_skills)))
                else:
                    st.info("No skills matched.")
        with col_x:
            with st.expander(f"Missing skills ({len(missing_skills)})", expanded=False):
                if missing_skills:
                    st.markdown(" ".join(f"`{s}`" for s in sorted(missing_skills)))
                else:
                    st.success("No missing skills — great match!")

    if recommendations:
        st.space(1)
        st.subheader("Recommendations", divider="orange", anchor=False)
        for rec in recommendations:
            st.markdown(f"- {rec}")


# ── Tab 1: Match ─────────────────────────────────────────────────────────────

with tab_match:
    st.space(1)
    st.subheader("Match Your Resume", divider="green", anchor=False)
    st.caption("Upload a PDF and paste the job description to get an instant match score.")
    st.space(1)

    col_upload, col_jd = st.columns([1, 2])
    with col_upload:
        st.markdown("**Resume PDF**")
        resume_file = st.file_uploader(
            "Upload resume", type=["pdf"], key="match_resume", label_visibility="collapsed"
        )
        if resume_file:
            st.success(resume_file.name)
    with col_jd:
        st.markdown("**Job Description**")
        job_desc = st.text_area(
            "Job description",
            height=220,
            placeholder="Paste the full job description here (50–10,000 characters)…",
            key="match_jd",
            label_visibility="collapsed",
        )

    st.space(1)
    if st.button("Analyze Match", type="primary", key="match_btn"):
        if resume_file is None:
            st.error("Please upload a resume PDF.")
        elif len(job_desc.strip()) < _MIN_JD_LENGTH:
            st.error(f"Job description must be at least {_MIN_JD_LENGTH} characters.")
        else:
            with st.spinner("Scoring your resume…"):
                try:
                    resp = requests.post(
                        f"{api_url}/match",
                        files={"resume": (resume_file.name, BytesIO(resume_file.getvalue()), "application/pdf")},
                        data={"job_description": job_desc},
                        timeout=60,
                    )
                except requests.exceptions.RequestException as exc:
                    st.error(f"Cannot reach API: {exc}")
                    st.stop()
            if resp.ok:
                st.divider()
                st.subheader("Match Results", divider="green", anchor=False)
                result = resp.json()
                _render_score_section(
                    result["overall_score"],
                    result["breakdown"],
                    result["recommendations"],
                    result["processing_time_ms"],
                )
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except (ValueError, Exception):
                    detail = resp.text
                st.error(f"API error {resp.status_code}: {detail}")


# ── Tab 2: Improve ────────────────────────────────────────────────────────────

with tab_improve:
    st.space(1)
    st.subheader("Improve Your Resume", divider="violet", anchor=False)
    st.caption("Upload your PDF + LaTeX source to score the match, flag weak bullets, and inject missing skills.")

    if st.session_state.saved_profile_json:
        st.success("Profile loaded — the optimizer will use your saved profile.")
    else:
        st.info("No profile saved. Fill out the My Profile tab for personalized suggestions.")

    st.space(1)
    col_left, col_right = st.columns([1, 2])
    with col_left:
        st.markdown("**Resume PDF**")
        imp_resume = st.file_uploader(
            "Resume PDF", type=["pdf"], key="imp_resume", label_visibility="collapsed"
        )
        if imp_resume:
            st.success(imp_resume.name)
        st.space(1)
        st.markdown("**Resume LaTeX (.tex)**")
        imp_tex = st.file_uploader(
            "Resume .tex", type=["tex"], key="imp_tex", label_visibility="collapsed"
        )
        if imp_tex:
            st.success(imp_tex.name)
    with col_right:
        st.markdown("**Job Description**")
        imp_jd = st.text_area(
            "Job description",
            height=340,
            placeholder="Paste the full job description here…",
            key="imp_jd",
            label_visibility="collapsed",
        )

    st.space(1)
    if st.button("Improve Resume", type="primary", key="imp_btn"):
        errors: list[str] = []
        if imp_resume is None:
            errors.append("Please upload a resume PDF.")
        if imp_tex is None:
            errors.append("Please upload a .tex file.")
        if len(imp_jd.strip()) < _MIN_JD_LENGTH:
            errors.append(f"Job description must be at least {_MIN_JD_LENGTH} characters.")
        if errors:
            for err in errors:
                st.error(err)
        else:
            with st.spinner("Analyzing and improving your resume…"):
                files = {
                    "resume_pdf": (imp_resume.name, BytesIO(imp_resume.getvalue()), "application/pdf"),  # type: ignore[union-attr]
                    "resume_tex": (imp_tex.name, BytesIO(imp_tex.getvalue()), "application/octet-stream"),  # type: ignore[union-attr]
                }
                data: dict[str, str] = {"job_description": imp_jd}
                if st.session_state.saved_profile_json:
                    data["profile_json"] = st.session_state.saved_profile_json
                try:
                    resp = requests.post(
                        f"{api_url}/improve", files=files, data=data, timeout=120
                    )
                except requests.exceptions.RequestException as exc:
                    st.error(f"Cannot reach API: {exc}")
                    st.stop()

            if resp.ok:
                result = resp.json()
                st.divider()
                st.subheader("Match Results", divider="green", anchor=False)
                _render_score_section(
                    result["overall_score"],
                    result["breakdown"],
                    result["recommendations"],
                    result["processing_time_ms"],
                )
                st.divider()
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("Injected Skills", divider="green", anchor=False)
                    st.caption("Skills added to close the gap with the job description.")
                    if result.get("injected_skills"):
                        for skill in result["injected_skills"]:
                            st.markdown(f"- `{skill}`")
                    else:
                        st.info("No missing skills were injected.")
                    if result.get("notes"):
                        st.space(1)
                        st.subheader("Optimizer Notes", divider="orange", anchor=False)
                        for note in result["notes"]:
                            st.markdown(f"- {note}")
                with col_b:
                    st.subheader("Weak Bullets", divider="red", anchor=False)
                    st.caption("Bullet points flagged for rewriting.")
                    if result.get("weak_bullets"):
                        for wb in result["weak_bullets"]:
                            context = wb.get("company") or wb.get("project") or "—"
                            hint = wb.get("hint", "")
                            with st.expander(f"[{wb['section']}]  {context}"):
                                st.code(wb["bullet"], language="text")
                                if hint:
                                    st.caption(f"Hint: {hint}")
                    else:
                        st.success("No weak bullets detected.")
                if result.get("latex_source"):
                    st.divider()
                    st.subheader("Improved LaTeX Source", divider="violet", anchor=False)
                    st.caption("Download and compile with pdflatex or Overleaf.")
                    with st.expander("Preview LaTeX source"):
                        st.code(result["latex_source"], language="latex")
                    st.download_button(
                        label="Download improved_resume.tex",
                        data=result["latex_source"],
                        file_name="improved_resume.tex",
                        mime="text/plain",
                        use_container_width=True,
                    )
            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except (ValueError, Exception):
                    detail = resp.text
                st.error(f"API error {resp.status_code}: {detail}")


# ── Tab 3: AI Suggestions ─────────────────────────────────────────────────────

with tab_suggest:
    st.space(1)
    st.subheader("AI Suggestions", divider="orange", anchor=False)
    st.caption(
        "Upload your resume PDF and paste the job description. "
        "The AI will rewrite weak bullets, identify skill gaps, "
        "suggest ATS keywords, and generate a tailored career summary."
    )

    if st.session_state.saved_profile_json:
        st.success("Profile loaded — AI suggestions will be personalized to your background.")
    else:
        st.info("No profile saved. Fill out the My Profile tab for more personalized suggestions.")

    st.space(1)
    col_sug_left, col_sug_right = st.columns([1, 2])
    with col_sug_left:
        st.markdown("**Resume PDF**")
        sug_resume = st.file_uploader(
            "Resume PDF", type=["pdf"], key="sug_resume", label_visibility="collapsed"
        )
        if sug_resume:
            st.success(sug_resume.name)
    with col_sug_right:
        st.markdown("**Job Description**")
        sug_jd = st.text_area(
            "Job description",
            height=220,
            placeholder="Paste the full job description here (50–10,000 characters)…",
            key="sug_jd",
            label_visibility="collapsed",
        )

    st.space(1)
    if st.button("Get AI Suggestions", type="primary", key="sug_btn"):
        if sug_resume is None:
            st.error("Please upload a resume PDF.")
        elif len(sug_jd.strip()) < _MIN_JD_LENGTH:
            st.error(f"Job description must be at least {_MIN_JD_LENGTH} characters.")
        else:
            with st.spinner("Generating AI suggestions — this may take up to 60 seconds…"):
                files = {
                    "resume_pdf": (sug_resume.name, BytesIO(sug_resume.getvalue()), "application/pdf"),
                }
                data_sug: dict[str, str] = {"job_description": sug_jd}
                if st.session_state.saved_profile_json:
                    data_sug["profile_json"] = st.session_state.saved_profile_json
                try:
                    resp = requests.post(
                        f"{api_url}/suggest", files=files, data=data_sug, timeout=180
                    )
                except requests.exceptions.RequestException as exc:
                    st.error(f"Cannot reach API: {exc}")
                    st.stop()

            if resp.ok:
                result = resp.json()
                st.divider()
                st.subheader("Match Score", divider="green", anchor=False)
                _render_score_section(
                    result["overall_score"],
                    result["breakdown"],
                    [],
                    result["processing_time_ms"],
                )

                st.divider()

                with st.expander("Bullet Rewrites", expanded=True):
                    rewrites = result.get("bullet_rewrites", [])
                    if rewrites:
                        # Group by section + context
                        groups: dict[str, list[dict]] = {}
                        for br in rewrites:
                            group_key = f"[{br['section']}]  {br['context'] or '—'}"
                            groups.setdefault(group_key, []).append(br)
                        for group_key, bullets in groups.items():
                            st.markdown(f"**{group_key}**")
                            col_orig, col_new = st.columns(2)
                            with col_orig:
                                st.markdown("*Original*")
                            with col_new:
                                st.markdown("*Rewritten*")
                            for br in bullets:
                                col_orig2, col_new2 = st.columns(2)
                                with col_orig2:
                                    st.code(br["original"], language="text")
                                with col_new2:
                                    st.code(br["rewritten"], language="text")
                    else:
                        st.info("No weak bullets detected in your resume.")

                with st.expander("Skill Gaps", expanded=True):
                    gaps = result.get("skill_gaps", [])
                    if gaps:
                        for gap in gaps:
                            st.markdown(f"- {gap}")
                    else:
                        st.success("No significant skill gaps identified.")

                with st.expander("Keywords to Add", expanded=True):
                    keywords = result.get("injected_keywords", [])
                    if keywords:
                        st.markdown(" ".join(f"`{kw}`" for kw in keywords))
                    else:
                        st.info("No additional keywords recommended.")

                with st.expander("Career Summary", expanded=True):
                    summary = result.get("career_summary", "")
                    if summary:
                        st.text_area(
                            "Rewritten career summary (copyable)",
                            value=summary,
                            height=120,
                            key="sug_summary_output",
                            label_visibility="collapsed",
                        )
                    else:
                        st.info("No career summary generated.")

                st.caption(f"Powered by {result.get('provider', 'unknown')}")

            else:
                try:
                    detail = resp.json().get("detail", resp.text)
                except (ValueError, Exception):
                    detail = resp.text
                st.error(f"API error {resp.status_code}: {detail}")


# ── Tab 4: Profile ────────────────────────────────────────────────────────────

with tab_profile:
    st.space(1)
    st.subheader("My Profile", divider="blue", anchor=False)
    st.caption(
        "Your profile lets the optimizer inject only skills you actually have "
        "and ground suggestions in your real experience. Saved once — used every time you Improve."
    )
    st.space(1)

    # ── Basic Info ────────────────────────────────────────────────────────────
    st.subheader("Basic Info", divider="gray", anchor=False)
    col_name, col_tone = st.columns([2, 1])
    with col_name:
        p_full_name = st.text_input("Full Name", key="p_full_name", placeholder="Jane Smith")
    with col_tone:
        p_tone = st.selectbox(
            "Writing Tone",
            options=["professional", "technical", "direct"],
            key="p_tone",
        )

    p_target_roles = st.text_input(
        "Target Roles",
        key="p_target_roles",
        placeholder="Senior ML Engineer, Data Scientist, AI Engineer  (comma-separated)",
    )
    p_career_summary = st.text_area(
        "Career Summary",
        height=100,
        key="p_career_summary",
        placeholder="2-3 sentences in your own words about your background and what you bring…",
    )
    p_avoid_phrases = st.text_input(
        "Phrases to Avoid",
        key="p_avoid_phrases",
        placeholder="passionate about, leverage, synergy  (comma-separated)",
    )

    st.space(1)

    # ── Skills ────────────────────────────────────────────────────────────────
    st.subheader("Skills", divider="gray", anchor=False)
    st.caption("Only list skills you can actually speak to in an interview.")

    skills_to_remove: list[int] = []
    for idx, skill in enumerate(st.session_state.profile_skills):
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 0.5])
            with c1:
                skill["name"] = st.text_input(
                    "Skill", value=skill.get("name", ""), key=f"sk_name_{idx}",
                    placeholder="Python", label_visibility="collapsed"
                )
            with c2:
                skill["proficiency"] = st.selectbox(
                    "Proficiency", options=["beginner", "intermediate", "expert"],
                    index=["beginner", "intermediate", "expert"].index(skill.get("proficiency", "intermediate")),
                    key=f"sk_prof_{idx}", label_visibility="collapsed"
                )
            with c3:
                if st.button("x", key=f"sk_rm_{idx}", help="Remove skill"):
                    skills_to_remove.append(idx)

    for idx in reversed(skills_to_remove):
        st.session_state.profile_skills.pop(idx)
    if skills_to_remove:
        st.rerun()

    if st.button("+ Add Skill", key="sk_add"):
        st.session_state.profile_skills.append({"name": "", "proficiency": "intermediate"})
        st.rerun()

    st.space(1)

    # ── Work History ──────────────────────────────────────────────────────────
    st.subheader("Work History", divider="gray", anchor=False)
    st.caption("The more specific your accomplishments, the better the optimizer performs.")

    work_to_remove: list[int] = []
    for idx, work in enumerate(st.session_state.profile_work):
        label = work.get("company") or f"Entry {idx + 1}"
        with st.expander(label, expanded=not work.get("company")):
            w1, w2 = st.columns(2)
            with w1:
                work["company"] = st.text_input("Company", value=work.get("company", ""), key=f"wk_co_{idx}", placeholder="Acme Corp")
                work["dates"] = st.text_input("Dates", value=work.get("dates", ""), key=f"wk_dates_{idx}", placeholder="Jan 2022 – Mar 2024")
            with w2:
                work["title"] = st.text_input("Title", value=work.get("title", ""), key=f"wk_title_{idx}", placeholder="Senior Data Engineer")
                work["location"] = st.text_input("Location", value=work.get("location", ""), key=f"wk_loc_{idx}", placeholder="Remote")

            work["technologies"] = st.text_input(
                "Technologies used", value=", ".join(work.get("technologies") or []),
                key=f"wk_tech_{idx}", placeholder="Python, Spark, Airflow, AWS"
            )
            work["accomplishments_raw"] = st.text_area(
                "Accomplishments (one per line)",
                value="\n".join(work.get("accomplishments") or []),
                height=100, key=f"wk_acc_{idx}",
                placeholder="Reduced pipeline latency by 40% by rewriting Spark jobs\nMentored 3 junior engineers",
            )

            col_opts, col_rm = st.columns([3, 1])
            with col_opts:
                work["promoted"] = st.checkbox("Promoted?", value=work.get("promoted", False), key=f"wk_promo_{idx}")
            with col_rm:
                st.write("")
                if st.button("Remove", key=f"wk_rm_{idx}"):
                    work_to_remove.append(idx)

    for idx in reversed(work_to_remove):
        st.session_state.profile_work.pop(idx)
    if work_to_remove:
        st.rerun()

    if st.button("+ Add Work Entry", key="wk_add"):
        st.session_state.profile_work.append({
            "company": "", "title": "", "dates": "", "location": "",
            "accomplishments": [], "technologies": [], "promoted": False,
        })
        st.rerun()

    st.space(1)

    # ── Projects ──────────────────────────────────────────────────────────────
    st.subheader("Projects", divider="gray", anchor=False)
    st.caption("Include side projects, open-source work, or research.")

    proj_to_remove: list[int] = []
    for idx, proj in enumerate(st.session_state.profile_projects):
        label = proj.get("name") or f"Project {idx + 1}"
        with st.expander(label, expanded=not proj.get("name")):
            p1, p2 = st.columns(2)
            with p1:
                proj["name"] = st.text_input("Project Name", value=proj.get("name", ""), key=f"pj_name_{idx}", placeholder="ResumeIQ")
                proj["url"] = st.text_input("URL (optional)", value=proj.get("url") or "", key=f"pj_url_{idx}", placeholder="https://github.com/…")
            with p2:
                proj["technologies"] = st.text_input(
                    "Technologies", value=", ".join(proj.get("technologies") or []),
                    key=f"pj_tech_{idx}", placeholder="FastAPI, spaCy, sentence-transformers"
                )

            proj["description"] = st.text_input(
                "Description", value=proj.get("description", ""), key=f"pj_desc_{idx}",
                placeholder="End-to-end resume scoring and improvement engine"
            )
            proj["outcomes_raw"] = st.text_area(
                "Outcomes (one per line)",
                value="\n".join(proj.get("outcomes") or []),
                height=80, key=f"pj_out_{idx}",
                placeholder="Achieved 92% accuracy on held-out test set\nDeployed to 500 beta users",
            )

            if st.button("Remove", key=f"pj_rm_{idx}"):
                proj_to_remove.append(idx)

    for idx in reversed(proj_to_remove):
        st.session_state.profile_projects.pop(idx)
    if proj_to_remove:
        st.rerun()

    if st.button("+ Add Project", key="pj_add"):
        st.session_state.profile_projects.append({
            "name": "", "description": "", "technologies": [],
            "outcomes": [], "url": None,
        })
        st.rerun()

    st.space(2)

    # ── Save ──────────────────────────────────────────────────────────────────
    st.divider()
    col_save, col_clear, col_preview = st.columns([2, 1, 1])

    with col_save:
        if st.button("Save Profile", type="primary", use_container_width=True, key="profile_save"):
            work_entries: list[WorkDetail] = []
            for work in st.session_state.profile_work:
                tech_raw = work.get("technologies", "")
                tech = [t.strip() for t in (tech_raw.split(",") if isinstance(tech_raw, str) else tech_raw) if t.strip()]
                acc_raw = work.get("accomplishments_raw", "")
                acc = [a.strip() for a in acc_raw.splitlines() if a.strip()]
                work_entries.append(WorkDetail(
                    company=work.get("company", ""),
                    title=work.get("title", ""),
                    dates=work.get("dates", ""),
                    location=work.get("location", ""),
                    accomplishments=acc,
                    technologies=tech,
                    promoted=work.get("promoted", False),
                ))

            proj_entries: list[ProjectDetail] = []
            for proj in st.session_state.profile_projects:
                tech_raw = proj.get("technologies", "")
                tech = [t.strip() for t in (tech_raw.split(",") if isinstance(tech_raw, str) else tech_raw) if t.strip()]
                out_raw = proj.get("outcomes_raw", "")
                outcomes = [o.strip() for o in out_raw.splitlines() if o.strip()]
                proj_entries.append(ProjectDetail(
                    name=proj.get("name", ""),
                    description=proj.get("description", ""),
                    technologies=tech,
                    outcomes=outcomes,
                    url=proj.get("url") or None,
                ))

            skill_entries: list[SkillEntry] = [
                SkillEntry(
                    name=sk["name"].strip(),
                    proficiency=sk.get("proficiency", "intermediate"),
                )
                for sk in st.session_state.profile_skills
                if sk.get("name", "").strip()
            ]

            try:
                profile = UserProfile(
                    full_name=st.session_state.get("p_full_name", ""),
                    target_roles=[r.strip() for r in st.session_state.get("p_target_roles", "").split(",") if r.strip()],
                    career_summary=st.session_state.get("p_career_summary", ""),
                    preferred_tone=st.session_state.get("p_tone", "professional"),
                    avoid_phrases=[p.strip() for p in st.session_state.get("p_avoid_phrases", "").split(",") if p.strip()],
                    skills=skill_entries,
                    work_history=work_entries,
                    projects=proj_entries,
                )
            except ValueError as exc:
                st.error(f"Profile validation failed: {exc}")
            else:
                st.session_state.saved_profile_json = profile.model_dump_json(indent=2)
                st.success("Profile saved — it will be used automatically in the Improve tab.")

    with col_clear:
        if st.button("Clear Profile", use_container_width=True, key="profile_clear"):
            st.session_state.saved_profile_json = ""
            st.session_state.profile_skills = []
            st.session_state.profile_work = []
            st.session_state.profile_projects = []
            st.rerun()

    with col_preview:
        if st.session_state.saved_profile_json and st.button("Preview JSON", use_container_width=True, key="profile_preview"):
            with st.expander("Saved profile JSON", expanded=True):
                st.code(st.session_state.saved_profile_json, language="json")
