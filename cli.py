import argparse
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resumeiq",
        description="Score a resume PDF against a job description and produce a JSON match report.",
    )
    parser.add_argument(
        "--resume",
        required=True,
        metavar="PDF_PATH",
        help="Path to the resume PDF file.",
    )
    parser.add_argument(
        "--job",
        required=True,
        metavar="JD_PATH_OR_TEXT",
        help="Path to a .txt job description file, or an inline job description string.",
    )
    parser.add_argument(
        "--output",
        required=False,
        metavar="OUTPUT_PATH",
        default=None,
        help="Optional path to save the JSON report (e.g., report.json).",
    )
    parser.add_argument(
        "--improve",
        action="store_true",
        default=False,
        help="Generate an optimized LaTeX resume PDF tailored to the job description.",
    )
    parser.add_argument(
        "--resume-tex",
        required=False,
        metavar="TEX_PATH",
        default=None,
        help="Path to the source .tex resume file (required when --improve is used).",
    )
    parser.add_argument(
        "--improve-output",
        required=False,
        metavar="PDF_PATH",
        default="output/improved_resume.pdf",
        help="Where to save the improved resume PDF (default: output/improved_resume.pdf).",
    )
    parser.add_argument(
        "--profile",
        required=False,
        metavar="PROFILE_JSON",
        default=None,
        help=(
            "Path to a user profile JSON file (see samples/sample_profile.json). "
            "When provided, the optimizer only injects skills you have confirmed "
            "and surfaces relevant accomplishments as improvement hints."
        ),
    )
    return parser


def load_job_description(job_arg: str) -> str:
    candidate = Path(job_arg)
    if candidate.exists():
        if candidate.suffix.lower() not in (".txt", ".md", ""):
            print(
                f"Warning: job description file has extension '{candidate.suffix}'. "
                "Expected a plain text file.",
                file=sys.stderr,
            )
        return candidate.read_text(encoding="utf-8").strip()
    return job_arg.strip()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    resume_path = Path(args.resume)
    if not resume_path.exists():
        print(f"Error: Resume file not found: {args.resume}", file=sys.stderr)
        sys.exit(1)
    if resume_path.suffix.lower() != ".pdf":
        print(f"Error: Resume must be a PDF file, got: {resume_path.suffix!r}", file=sys.stderr)
        sys.exit(1)

    job_text = load_job_description(args.job)
    if not job_text:
        print("Error: Job description is empty.", file=sys.stderr)
        sys.exit(1)

    from engine.extractor import EntityExtractor
    from engine.latex_builder import build_pdf, parse_tex_to_resume_data
    from engine.matcher import SemanticMatcher
    from engine.optimizer import optimize
    from engine.parser import extract_text_from_pdf
    from engine.profile import UserProfile
    from engine.reporter import generate_report
    from engine.scorer import MatchScorer

    print("Extracting text from resume PDF...", file=sys.stderr)
    try:
        resume_text = extract_text_from_pdf(resume_path)
    except ValueError as exc:
        print(f"Error parsing resume: {exc}", file=sys.stderr)
        sys.exit(1)

    if not resume_text.strip():
        print("Error: Could not extract any text from the resume PDF.", file=sys.stderr)
        sys.exit(1)

    print("Extracting entities from resume and job description...", file=sys.stderr)
    extractor = EntityExtractor()
    resume_entities = extractor.extract(resume_text)
    jd_entities = extractor.extract(job_text)

    print("Computing semantic similarity...", file=sys.stderr)
    matcher = SemanticMatcher()
    semantic_sim = matcher.similarity(resume_text, job_text)

    print("Scoring match...", file=sys.stderr)
    scorer = MatchScorer()
    match_report = scorer.score(resume_entities, jd_entities, semantic_sim)

    report_dict = generate_report(match_report, output_path=args.output)

    if args.output:
        print(f"Report saved to: {args.output}", file=sys.stderr)

    print(json.dumps(report_dict, indent=2))

    # --- Phase 1b: generate improved resume PDF if requested ---
    if args.improve:
        tex_path = args.resume_tex
        if not tex_path:
            print(
                "Error: --improve requires --resume-tex pointing to your source .tex file.",
                file=sys.stderr,
            )
            sys.exit(1)

        tex_path = Path(tex_path)
        if not tex_path.exists():
            print(f"Error: .tex file not found: {tex_path}", file=sys.stderr)
            sys.exit(1)

        print("\nParsing source .tex file...", file=sys.stderr)
        resume_data = parse_tex_to_resume_data(tex_path)

        profile: UserProfile | None = None
        if args.profile:
            profile_path = Path(args.profile)
            if not profile_path.exists():
                print(f"Error: Profile file not found: {args.profile}", file=sys.stderr)
                sys.exit(1)
            print(f"Loading user profile from {profile_path}...", file=sys.stderr)
            profile = UserProfile.from_json(profile_path)

        print("Optimizing resume against match report...", file=sys.stderr)
        result = optimize(match_report, resume_data, profile=profile)

        if result.injected_skills:
            print(f"  + Injected skills: {', '.join(result.injected_skills)}", file=sys.stderr)
        if result.weak_bullets:
            print(f"  ! Flagged {len(result.weak_bullets)} bullet(s) for improvement", file=sys.stderr)
        for note in result.notes:
            print(f"  > {note}", file=sys.stderr)

        print(f"Compiling improved resume to PDF...", file=sys.stderr)
        try:
            pdf_path = build_pdf(result.resume, args.improve_output, keep_tex=True)
            print(f"Improved resume saved to: {pdf_path}", file=sys.stderr)
        except RuntimeError as exc:
            print(f"Error compiling PDF: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
