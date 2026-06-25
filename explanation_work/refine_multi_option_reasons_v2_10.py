from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
BACKUP_PATH = ROOT / "explanation_work" / "questions.before_v2_10_multi_option_refine.json"
REPORT_PATH = ROOT / "explanation_work" / "v2_10_multi_option_refine_report.md"
OPTION_LINE_RE = re.compile(r"^-\s*([A-Z])\uff08?.*?\uff09?\uff1a([^\uff0c,]+)[\uff0c,]?(.*)$")


def load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def clean_option_text(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(r"^[A-Z][\.\u3001\uFF0E]\s*", "", value)
    return value.strip()


def normalize_body(body: str) -> str:
    text = str(body or "").strip()
    if text.startswith("\u56e0\u4e3a"):
        text = text[2:].strip()
    return text.rstrip("\u3002\uff1b;,\uff0c ")


def should_prefix_subject(body: str) -> bool:
    if len(body) < 8:
        return True
    prefixes = (
        "\u662f", "\u4e3a", "\u5c5e", "\u6709", "\u65e0", "\u53ef", "\u80fd", "\u4f1a",
        "\u628a", "\u6309", "\u5728", "\u7531", "\u9700", "\u7528", "\u975e", "\u4e0d",
        "\u5e76", "\u5373", "\u4ec5", "\u90fd", "\u66f4", "\u4e0e", "\u5bf9", "\u9760",
        "\u901a\u8fc7", "\u91c7\u7528", "\u8d1f\u8d23", "\u652f\u6301", "\u5b9e\u73b0",
        "\u89c4\u5b9a", "\u8868\u793a", "\u8986\u76d6", "\u63d0\u9ad8", "\u901a\u5e38",
        "\u4e00\u822c", "\u5c5e\u4e8e", "\u4e0d\u662f", "\u5e76\u975e", "\u8bf4\u660e",
    )
    return body.startswith(prefixes)


def has_overlap(option_text: str, body: str) -> bool:
    compact_option = option_text.replace(" ", "")
    compact_body = body.replace(" ", "")
    if compact_option and compact_option in compact_body:
        return True
    for i in range(max(0, len(compact_option) - 1)):
        part = compact_option[i:i + 2]
        if len(part) == 2 and part in compact_body:
            return True
    return False


def strip_redundant_prefix(option_text: str, body: str) -> str:
    compact = option_text.replace(" ", "")
    for size in range(len(compact), 1, -1):
        prefix = compact[:size]
        if body.startswith(prefix):
            return body[size:].lstrip()
    return body


def enrich_option_line(option_text: str, verdict: str, body: str) -> str:
    normalized = normalize_body(body)
    if not normalized:
        normalized = option_text + (
            "\u7b26\u5408\u672c\u9898\u5224\u65ad\u6761\u4ef6"
            if verdict == "\u5bf9"
            else "\u4e0d\u7b26\u5408\u672c\u9898\u5224\u65ad\u6761\u4ef6"
        )
    elif option_text and has_overlap(option_text, normalized):
        normalized = strip_redundant_prefix(option_text, normalized)
        if not normalized:
            normalized = option_text + (
                "\u7b26\u5408\u672c\u9898\u5224\u65ad\u6761\u4ef6"
                if verdict == "\u5bf9"
                else "\u4e0d\u7b26\u5408\u672c\u9898\u5224\u65ad\u6761\u4ef6"
            )
    elif option_text and should_prefix_subject(normalized):
        normalized = option_text + normalized
    return f"{verdict}\uff0c\u56e0\u4e3a{normalized}\u3002"


def rebuild_multi_explanation(question: dict) -> tuple[str, bool]:
    quick = str(question.get("quickExplanation") or "").replace("\r\n", "\n").replace("\r", "\n")
    if not quick.strip():
        return quick, False
    lines = quick.split("\n")
    changed = False
    rebuilt_lines: list[str] = []
    option_map = {opt.get("key"): clean_option_text(opt.get("text")) for opt in question.get("options", [])}

    for line in lines:
        stripped = line.strip()
        match = OPTION_LINE_RE.match(stripped)
        if not match:
            rebuilt_lines.append(line)
            continue
        key, verdict, body = match.groups()
        key = key.strip()
        verdict = verdict.strip()
        option_text = option_map.get(key, key)
        rebuilt = f"- {key}\uff08{option_text}\uff09\uff1a{enrich_option_line(option_text, verdict, body)}"
        rebuilt_lines.append(rebuilt)
        if rebuilt != stripped:
            changed = True
    return "\n".join(rebuilt_lines).strip(), changed


def rebuild_full_explanation(question: dict) -> str:
    quick = str(question.get("quickExplanation") or "").strip()
    detail = str(question.get("knowledgeDetail") or "").strip()
    if quick and detail:
        return f"\u3010\u5feb\u901f\u505a\u9898\u3011\n{quick}\n\n\u3010\u77e5\u8bc6\u70b9\u8be6\u89e3\u3011\n{detail}"
    return quick or detail


def main() -> None:
    questions = load_questions()
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    total_multi = 0
    changed_labels: list[str] = []
    for question in questions:
        if question.get("type") != "multi":
            continue
        total_multi += 1
        rebuilt, changed = rebuild_multi_explanation(question)
        if changed:
            question["quickExplanation"] = rebuilt
            question["explanation"] = rebuild_full_explanation(question)
            changed_labels.append(question.get("label", ""))

    QUESTIONS_PATH.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_lines = [
        "# v2.10 multi option reason refine report",
        "",
        f"- multi_questions: {total_multi}",
        f"- changed_questions: {len(changed_labels)}",
        "",
        "## Changed Labels",
        "",
        ", ".join(changed_labels) if changed_labels else "none",
        "",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
