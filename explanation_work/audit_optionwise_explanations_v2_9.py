from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
REPORT_PATH = ROOT / "explanation_work" / "v2_9_optionwise_audit.md"

LABEL_EYE = "\u9898\u773c\uff1a"
LABEL_REASON = "\u7406\u7531\uff1a"
LABEL_TRAP = "\u6613\u9519\uff1a"
LABEL_ANSWER = "\u7b54\u6848\uff1a"
LABEL_JUDGMENT = "\u5224\u65ad\uff1a"
LABEL_CORE = "\u6838\u5fc3\u77e5\u8bc6\u70b9\uff1a"
LABEL_VARIANT = "\u9898\u76ee\u53d8\u5f62\uff1a"
LABEL_EXPAND = "\u77e5\u8bc6\u62d3\u5c55\uff1a"
REQUIRED_QUICK_LABELS = [LABEL_EYE, LABEL_REASON, LABEL_TRAP]
REQUIRED_DETAIL_LABELS = [LABEL_CORE, LABEL_VARIANT, LABEL_EXPAND]
FORBIDDEN_TERMS = [
    "\u7b2c\u4e00\u6b65",
    "\u7b2c\u4e8c\u6b65",
    "\u7b2c\u4e09\u6b65",
    "\u6b65\u9aa4\u5982\u4e0b",
    "\u89e3\u9898\u6b65\u9aa4",
]


def load_questions():
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def option_keys(question):
    return [str(opt.get("key", "")).strip() for opt in question.get("options", []) or [] if str(opt.get("key", "")).strip()]


def option_prefixes(question) -> list[list[str]]:
    prefixes = []
    for key in option_keys(question):
        if question.get("type") == "tf":
            if key == "TRUE":
                prefixes.append(["TRUE", "T"])
            elif key == "FALSE":
                prefixes.append(["FALSE", "F"])
            else:
                prefixes.append([key])
        else:
            prefixes.append([key])
    return prefixes


def has_answer_label(text: str) -> bool:
    return LABEL_ANSWER in text or LABEL_JUDGMENT in text


def count_option_lines(text: str, accepted_prefixes: list[list[str]]) -> int:
    stripped_lines = [line.strip() for line in text.splitlines() if line.strip()]
    count = 0
    for variants in accepted_prefixes:
        if any(any(line.startswith(f"- {variant}\uff1a") for variant in variants) for line in stripped_lines):
            count += 1
    return count


def count_blank_lines(text: str) -> int:
    stripped_lines = [line.strip() for line in text.splitlines() if line.strip()]
    return sum(
        1
        for line in stripped_lines
        if line.startswith("- \u7b2c") and "\u7a7a\uff1a" in line
    )


def main() -> None:
    questions = load_questions()
    problems = []

    ok_answer_label = 0
    ok_quick_labels = 0
    ok_detail_labels = 0
    ok_optionwise = 0
    ok_no_steps = 0

    for q in questions:
        label = q["label"]
        quick = str(q.get("quickExplanation", "")).strip()
        detail = str(q.get("knowledgeDetail", "")).strip()
        q_type = q.get("type")

        local_problems = []

        if has_answer_label(quick):
            ok_answer_label += 1
        else:
            local_problems.append("missing answer/judgment label")

        if all(tag in quick for tag in REQUIRED_QUICK_LABELS):
            ok_quick_labels += 1
        else:
            missing = [tag for tag in REQUIRED_QUICK_LABELS if tag not in quick]
            local_problems.append("quickExplanation missing " + ", ".join(missing))

        if all(tag in detail for tag in REQUIRED_DETAIL_LABELS):
            ok_detail_labels += 1
        else:
            missing = [tag for tag in REQUIRED_DETAIL_LABELS if tag not in detail]
            local_problems.append("knowledgeDetail missing " + ", ".join(missing))

        if not any(term in quick or term in detail for term in FORBIDDEN_TERMS):
            ok_no_steps += 1
        else:
            local_problems.append("contains step-template wording")

        if q_type == "blank":
            if count_blank_lines(quick) >= 1:
                ok_optionwise += 1
            else:
                local_problems.append("blank question missing per-blank explanation")
        else:
            accepted = option_prefixes(q)
            if accepted and count_option_lines(quick, accepted) == len(accepted):
                ok_optionwise += 1
            else:
                local_problems.append("missing per-option explanation")

        if local_problems:
            problems.append((label, q_type, "; ".join(local_problems)))

    lines = [
        "# v2.9 Optionwise Explanation Audit",
        "",
        f"- total_questions: {len(questions)}",
        f"- answer_or_judgment_label_ok: {ok_answer_label}/{len(questions)}",
        f"- eye_reason_trap_label_ok: {ok_quick_labels}/{len(questions)}",
        f"- core_variant_expand_label_ok: {ok_detail_labels}/{len(questions)}",
        f"- optionwise_or_blankwise_ok: {ok_optionwise}/{len(questions)}",
        f"- no_step_template_ok: {ok_no_steps}/{len(questions)}",
        "",
        "## Problem List",
        "",
    ]
    if problems:
        for label, q_type, reason in problems:
            lines.append(f"- {label} ({q_type}): {reason}")
    else:
        lines.append("none")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
