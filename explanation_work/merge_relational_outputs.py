from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
OUTPUT_DIR = ROOT / "explanation_work" / "agent_outputs"
BACKUP_PATH = ROOT / "explanation_work" / "questions.before_relational_v1.json"
REPORT_PATH = ROOT / "explanation_work" / "relational_v1_merge_report.md"

DEFAULT_FILES = [
    OUTPUT_DIR / "relational_v1_chapter1.json",
    OUTPUT_DIR / "relational_v1_chapter2_3.json",
    OUTPUT_DIR / "relational_v1_chapter4_a.json",
    OUTPUT_DIR / "relational_v1_chapter4_b.json",
    OUTPUT_DIR / "relational_v1_chapter5.json",
    OUTPUT_DIR / "relational_v1_chapter6_7.json",
]

BAD_CHARS_RE = re.compile(r"\ufffd|[\u00c0-\u00ff]{2,}")
GENERIC_PHRASES = [
    "干扰项，和题干限定不符或范围不对",
    "正确项，符合题干限定",
    "答案来自这个考点",
    "本题答案包含",
    "本题答案不包含",
    "不要被同层相近术语带偏",
    "满足才选",
    "题干关键词，需要按本题语境理解",
    "本题核心知识范围",
    "看它在",
    "不只看字面",
    "填空题错在同义词不稳或漏写单位",
    "若选 T，就等于承认题干表述成立",
    "若选 F，就是否定题干",
    "该考点的标准关系",
    "重点是按题干限定逐项核对",
    "其余选项要么",
    "把空前后的概念接成同一组术语",
    "依据是题干中",
    "最后看选项：本题落到",
    "本题理由?",
    "选项判断?",
    "?不选?",
    "?应选?",
    "不选。原句说法不成立",
    "判断题选",
    "本题本题理由",
    "空位所在句已经给出",
    "本题归入",
    "解题时先定层次",
    "与题干问法不贴合",
    "本题要抓的是",
    "关键是按正确概念层次逐项判断",
]


def clean_text(text: object) -> str:
    return "\n".join(
        line.rstrip()
        for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")
    ).strip()


def build_explanation(quick: str, detail: str) -> str:
    return f"【快速做题】\n{clean_text(quick)}\n\n【知识点详解】\n{clean_text(detail)}"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_text(label: str, quick: str, detail: str, source: str) -> list[str]:
    issues: list[str] = []
    whole = quick + "\n" + detail
    if not quick:
        issues.append(f"{label} from {source}: empty quickExplanation")
    if not detail:
        issues.append(f"{label} from {source}: empty knowledgeDetail")
    if "题目变形" in whole:
        issues.append(f"{label} from {source}: contains forbidden 题目变形")
    if BAD_CHARS_RE.search(whole) or "???" in whole:
        issues.append(f"{label} from {source}: suspect mojibake chars")
    for phrase in GENERIC_PHRASES:
        if phrase in whole:
            issues.append(f"{label} from {source}: generic phrase {phrase}")
    for marker in ("核心知识框架", "做题抓手"):
        if marker not in detail:
            issues.append(f"{label} from {source}: missing {marker}")
    if "知识关系表" not in detail and "易混辨析表" not in detail:
        issues.append(f"{label} from {source}: missing relation/discrimination section")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="*", default=[str(p) for p in DEFAULT_FILES])
    args = parser.parse_args()

    questions = load_json(QUESTIONS_PATH)
    by_label = {q["label"]: q for q in questions}

    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")

    merged: dict[str, dict[str, str]] = {}
    source_counts: dict[str, int] = {}
    errors: list[str] = []

    for raw_path in args.files:
        path = Path(raw_path)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            errors.append(f"missing file: {path}")
            continue
        rows = load_json(path)
        if not isinstance(rows, list):
            errors.append(f"{path.name}: expected JSON array")
            continue
        source_counts[path.name] = len(rows)
        for row in rows:
            label = row.get("label")
            if not label:
                errors.append(f"{path.name}: row missing label")
                continue
            if label not in by_label:
                errors.append(f"{label} from {path.name}: unknown label")
                continue
            quick = clean_text(row.get("quickExplanation"))
            detail = clean_text(row.get("knowledgeDetail"))
            errors.extend(validate_text(label, quick, detail, path.name))
            merged[label] = {
                "quickExplanation": quick,
                "knowledgeDetail": detail,
                "source": path.name,
            }

    if errors:
        raise RuntimeError("invalid relational outputs:\n" + "\n".join(errors[:100]))

    updated = 0
    for question in questions:
        payload = merged.get(question["label"])
        if not payload:
            continue
        question["quickExplanation"] = payload["quickExplanation"]
        question["knowledgeDetail"] = payload["knowledgeDetail"]
        question["explanation"] = build_explanation(question["quickExplanation"], question["knowledgeDetail"])
        updated += 1

    QUESTIONS_PATH.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Relational v1 Merge Report",
        "",
        f"- total_questions: {len(questions)}",
        f"- replaced_questions: {updated}",
        f"- output_files: {len(source_counts)}",
        "",
        "## Agent File Counts",
        "",
    ]
    for name, count in source_counts.items():
        lines.append(f"- {name}: {count}")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
