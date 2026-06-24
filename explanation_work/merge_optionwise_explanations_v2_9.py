from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
OUTPUT_DIR = ROOT / "explanation_work" / "agent_outputs"
BACKUP_PATH = ROOT / "explanation_work" / "questions.before_v2_9_optionwise_merge.json"
REPORT_PATH = ROOT / "explanation_work" / "v2_9_optionwise_merge_report.md"

AGENT_FILES = [
    OUTPUT_DIR / "chapter1_full_optionwise.json",
    OUTPUT_DIR / "chapter2_full_optionwise.json",
    OUTPUT_DIR / "chapter3_full_optionwise.json",
    OUTPUT_DIR / "chapter4_full_optionwise.json",
    OUTPUT_DIR / "chapter5_7_full_optionwise.json",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def clean_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in str(text).replace("\r\n", "\n").strip().split("\n")).strip()


def build_explanation(quick: str, detail: str) -> str:
    quick_title = "\u3010\u5feb\u901f\u505a\u9898\u3011"
    detail_title = "\u3010\u77e5\u8bc6\u70b9\u8be6\u89e3\u3011"
    return f"{quick_title}\n{clean_text(quick)}\n\n{detail_title}\n{clean_text(detail)}"


def main() -> None:
    questions = load_json(QUESTIONS_PATH)
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(
            json.dumps(questions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    merged = {}
    source_counts = {}
    missing_files = []

    for path in AGENT_FILES:
        if not path.exists():
            missing_files.append(path.name)
            continue
        data = load_json(path)
        source_counts[path.name] = len(data)
        for item in data:
            label = item["label"]
            merged[label] = {
                "quickExplanation": clean_text(item["quickExplanation"]),
                "knowledgeDetail": clean_text(item["knowledgeDetail"]),
                "source": path.name,
            }

    updated = 0
    untouched = []
    source_used = {}
    for q in questions:
        payload = merged.get(q["label"])
        if not payload:
            untouched.append(q["label"])
            continue
        q["quickExplanation"] = payload["quickExplanation"]
        q["knowledgeDetail"] = payload["knowledgeDetail"]
        q["explanation"] = build_explanation(q["quickExplanation"], q["knowledgeDetail"])
        updated += 1
        source_used[q["label"]] = payload["source"]

    QUESTIONS_PATH.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# v2.9 Optionwise Merge Report",
        "",
        f"- total_questions: {len(questions)}",
        f"- replaced_questions: {updated}",
        f"- untouched_questions: {len(untouched)}",
        f"- missing_outputs: {', '.join(missing_files) if missing_files else 'none'}",
        "",
        "## Agent File Counts",
        "",
    ]
    for name, count in source_counts.items():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Untouched Labels", ""])
    if untouched:
        lines.append(", ".join(untouched))
    else:
        lines.append("none")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
