import json
from pathlib import Path

from engine.scorer import MatchReport


def generate_report(
    match_report: MatchReport,
    output_path: str | Path | None = None,
) -> dict:
    report_dict = match_report.model_dump()

    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)

    return report_dict
