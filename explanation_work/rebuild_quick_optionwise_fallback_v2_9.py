from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
EXPLANATION_DIR = ROOT / "explanation_work"
BACKUP_PATH = EXPLANATION_DIR / "questions.before_v2_9_fallback_quick.json"
REPORT_PATH = EXPLANATION_DIR / "v2_9_fallback_quick_report.md"

SOURCE_FILES = {
    "single": EXPLANATION_DIR / "single_explanations.json",
    "multi": EXPLANATION_DIR / "multi_explanations.json",
    "tf": EXPLANATION_DIR / "tf_explanations.json",
    "blank": EXPLANATION_DIR / "blank_explanations.json",
}

LABEL_EYE = "\u9898\u773c\uff1a"
LABEL_ANSWER = "\u7b54\u6848\uff1a"
LABEL_JUDGMENT = "\u5224\u65ad\uff1a"
LABEL_REASON = "\u7406\u7531\uff1a"
LABEL_TRAP = "\u6613\u9519\uff1a"
LABEL_MEMORY = "\u8bb0\u5fc6\u70b9\uff1a"
LABEL_OPTIONWISE = "\u9009\u9879\u5224\u65ad\uff1a"
LABEL_BLANKWISE = "\u7a7a\u683c\u5224\u65ad\uff1a"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def option_text_map(question) -> dict[str, str]:
    out = {}
    for opt in question.get("options", []) or []:
        key = str(opt.get("key", "")).strip()
        text = str(opt.get("text", "")).strip()
        if key:
            out[key] = text
    return out


def answer_keys(question) -> list[str]:
    answer = str(question.get("answer", "")).strip()
    if not answer:
        return []
    if question.get("type") == "multi":
        if re.fullmatch(r"[A-Z]+", answer):
            return list(answer)
        return [part.strip() for part in re.split(r"[,，、/\s]+", answer) if part.strip()]
    return [answer]


def split_lines_map(text: str) -> dict[str, str]:
    mapping = {}
    for raw in str(text).replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line or "\uff1a" not in line:
            continue
        key, value = line.split("\uff1a", 1)
        mapping[key.strip()] = value.strip()
    return mapping


def normalize_sentence(text: str) -> str:
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip("。；; ")
    return text


def option_display_text(raw: str) -> str:
    text = str(raw).strip()
    return re.sub(r"^[A-ZTRUEFALS]+\s*[.．、]\s*", "", text)


def extract_keywords(text: str) -> list[str]:
    tokens = []
    for part in re.findall(r"[A-Za-z][A-Za-z0-9./-]*|[\u4e00-\u9fff]{2,8}", text):
        if part not in tokens:
            tokens.append(part)
    return tokens


def split_fragments(text: str) -> list[str]:
    parts = re.split(r"[；;。]\s*", str(text))
    return [normalize_sentence(part) for part in parts if normalize_sentence(part)]


def find_best_fragment(option_text: str, fragments: list[str]) -> str:
    display = option_display_text(option_text)
    keywords = extract_keywords(display)
    best = ""
    best_score = -1
    for frag in fragments:
        score = 0
        for token in keywords:
            if token and token in frag:
                score += max(len(token), 2)
        if score > best_score:
            best = frag
            best_score = score
    return best if best_score > 0 else ""


def parse_multi_judgments(text: str) -> dict[str, str]:
    text = str(text).strip()
    pattern = re.compile(r"(?:^|[；;])\s*([A-Z])(?:[.．、:： ]*)?(.*?)(?=(?:[；;]\s*[A-Z](?:[.．、:： ]*)?)|$)")
    out = {}
    for key, body in pattern.findall(text):
        out[key] = normalize_sentence(body)
    return out


def compose_explanation(quick: str, detail: str) -> str:
    quick_title = "\u3010\u5feb\u901f\u505a\u9898\u3011"
    detail_title = "\u3010\u77e5\u8bc6\u70b9\u8be6\u89e3\u3011"
    return f"{quick_title}\n{quick.strip()}\n\n{detail_title}\n{detail.strip()}"


def rebuild_tf(question, source_text: str) -> str:
    fields = split_lines_map(source_text)
    eye = fields.get("\u9898\u773c", normalize_sentence(question.get("stem", "")))
    judgment = fields.get("\u5224\u65ad", "").rstrip("。")
    reason = fields.get("\u4e3a\u4ec0\u4e48", fields.get("\u7406\u7531", ""))
    trap = fields.get("\u522b\u8e29\u5751", fields.get("\u6613\u9519", ""))
    memory = fields.get("\u8bb0\u6cd5", "")
    answer = answer_keys(question)[0] if answer_keys(question) else ""
    true_line = "\u5bf9" if answer == "TRUE" else "\u9519"
    false_line = "\u5bf9" if answer == "FALSE" else "\u9519"
    lines = [
        f"{LABEL_EYE}{eye}",
        f"{LABEL_JUDGMENT}{judgment}",
        f"{LABEL_REASON}{normalize_sentence(reason)}",
        LABEL_OPTIONWISE,
        f"- TRUE\uff1a{true_line}\uff0c\u56e0\u4e3a{normalize_sentence(reason)}",
        f"- FALSE\uff1a{false_line}\uff0c\u56e0\u4e3a{normalize_sentence(reason)}",
        f"{LABEL_TRAP}{normalize_sentence(trap)}",
    ]
    if memory:
        lines.append(f"{LABEL_MEMORY}{normalize_sentence(memory)}")
    return "\n".join(lines)


def rebuild_blank(question, source_text: str) -> str:
    fields = split_lines_map(source_text)
    eye = fields.get("\u9898\u773c", normalize_sentence(question.get("stem", "")))
    answer = fields.get("\u6807\u51c6\u586b\u6cd5", str(question.get("answer", "")).strip())
    reason = fields.get("\u4e3a\u4ec0\u4e48\u662f\u8fd9\u4e2a\u8bcd", fields.get("\u7406\u7531", ""))
    trap = fields.get("\u522b\u5199\u6210", fields.get("\u6613\u9519", ""))
    memory = fields.get("\u8bb0\u6cd5", "")
    blanks = [part.strip() for part in re.split(r"[、,，/]\s*", answer) if part.strip()]
    if not blanks:
        blanks = [answer.strip()] if str(answer).strip() else []
    lines = [
        f"{LABEL_EYE}{eye}",
        f"{LABEL_ANSWER}{str(answer).strip()}",
        f"{LABEL_REASON}{normalize_sentence(reason)}",
        LABEL_BLANKWISE,
    ]
    if not blanks:
        lines.append(f"- \u7b2c1\u7a7a\uff1a{normalize_sentence(reason)}")
    else:
        for idx, blank in enumerate(blanks, start=1):
            lines.append(f"- \u7b2c{idx}\u7a7a\uff1a\u586b\u201c{blank}\u201d\uff0c\u56e0\u4e3a{normalize_sentence(reason)}")
    lines.append(f"{LABEL_TRAP}{normalize_sentence(trap)}")
    if memory:
        lines.append(f"{LABEL_MEMORY}{normalize_sentence(memory)}")
    return "\n".join(lines)


def rebuild_multi(question, source_text: str) -> str:
    fields = split_lines_map(source_text)
    eye = fields.get("\u9898\u773c", normalize_sentence(question.get("stem", "")))
    answer = fields.get("\u7b54\u6848", str(question.get("answer", "")).strip())
    judgments = parse_multi_judgments(fields.get("\u9010\u9879\u5224\u65ad", ""))
    trap = fields.get("\u6613\u9519", "")
    memory = fields.get("\u8bb0\u6cd5", "")
    answers = set(answer_keys(question))
    options = option_text_map(question)
    right_count = len(answers)
    reason = f"\u672c\u9898\u662f\u591a\u9009\uff0c\u8981\u628a{right_count}\u4e2a\u6b63\u786e\u9879\u90fd\u5bf9\u4e0a\uff0c\u9519\u9879\u8981\u6392\u9664\u6389\u3002"
    lines = [
        f"{LABEL_EYE}{eye}",
        f"{LABEL_ANSWER}{answer}",
        f"{LABEL_REASON}{reason}",
        LABEL_OPTIONWISE,
    ]
    for key, opt_text in options.items():
        body = judgments.get(key, "")
        if body:
            body = re.sub(r"(,|\uff0c)?\s*\u5e94\u9009$", "", body)
            body = re.sub(r"(,|\uff0c)?\s*\u4e0d\u9009$", "", body)
        if key in answers:
            why = body or f"\u8fd9\u4e2a\u9009\u9879\u7b26\u5408\u9898\u5e72\u6240\u95ee\u7684\u7c7b\u522b\u6216\u5b9a\u4e49"
            lines.append(f"- {key}\uff1a\u5bf9\uff0c\u56e0\u4e3a{normalize_sentence(why)}")
        else:
            why = body or f"\u5b83\u4e0d\u5c5e\u4e8e\u672c\u9898\u8981\u627e\u7684\u7c7b\u522b\uff0c\u662f\u5e38\u89c1\u6df7\u6dc6\u9879"
            lines.append(f"- {key}\uff1a\u9519\uff0c\u56e0\u4e3a{normalize_sentence(why)}")
    lines.append(f"{LABEL_TRAP}{normalize_sentence(trap)}")
    if memory:
        lines.append(f"{LABEL_MEMORY}{normalize_sentence(memory)}")
    return "\n".join(lines)


def rebuild_single(question, source_text: str) -> str:
    fields = split_lines_map(source_text)
    eye = fields.get("\u9898\u773c", normalize_sentence(question.get("stem", "")))
    answer = fields.get("\u7b54\u6848", str(question.get("answer", "")).strip())
    reason = fields.get("\u4e3a\u4ec0\u4e48\u9009\u5b83", fields.get("\u7406\u7531", ""))
    trap = fields.get("\u6392\u9664/\u6613\u6df7", fields.get("\u6613\u9519", ""))
    memory = fields.get("\u8bb0\u6cd5", "")
    options = option_text_map(question)
    fragments = split_fragments(trap)
    correct = set(answer_keys(question))
    lines = [
        f"{LABEL_EYE}{eye}",
        f"{LABEL_ANSWER}{answer}",
        f"{LABEL_REASON}{normalize_sentence(reason)}",
        LABEL_OPTIONWISE,
    ]
    for key, raw_text in options.items():
        display = option_display_text(raw_text)
        if key in correct:
            lines.append(f"- {key}\uff1a\u5bf9\uff0c\u56e0\u4e3a{normalize_sentence(reason)}")
            continue
        frag = find_best_fragment(display, fragments)
        if frag:
            why = frag
        else:
            why = f"{display}\u4e0d\u662f\u672c\u9898\u9898\u773c\u8981\u5bf9\u51c6\u7684\u6982\u5ff5\uff0c\u5bb9\u6613\u548c\u6b63\u786e\u9879\u6df7\u6389"
        lines.append(f"- {key}\uff1a\u9519\uff0c\u56e0\u4e3a{normalize_sentence(why)}")
    lines.append(f"{LABEL_TRAP}{normalize_sentence(trap)}")
    if memory:
        lines.append(f"{LABEL_MEMORY}{normalize_sentence(memory)}")
    return "\n".join(lines)


def main() -> None:
    questions = load_json(QUESTIONS_PATH)
    if not BACKUP_PATH.exists():
        dump_json(BACKUP_PATH, questions)

    source_maps = {}
    for q_type, path in SOURCE_FILES.items():
        source_maps[q_type] = {item["label"]: item["explanation"] for item in load_json(path)}

    changed = 0
    missing = []
    by_type = Counter()

    for question in questions:
        q_type = question.get("type")
        label = question.get("label")
        source_text = source_maps.get(q_type, {}).get(label)
        if not source_text:
            missing.append(label)
            continue

        if q_type == "tf":
            quick = rebuild_tf(question, source_text)
        elif q_type == "blank":
            quick = rebuild_blank(question, source_text)
        elif q_type == "multi":
            quick = rebuild_multi(question, source_text)
        else:
            quick = rebuild_single(question, source_text)

        question["quickExplanation"] = quick
        question["explanation"] = compose_explanation(quick, str(question.get("knowledgeDetail", "")).strip())
        changed += 1
        by_type[q_type] += 1

    dump_json(QUESTIONS_PATH, questions)

    report_lines = [
        "# v2.9 Fallback Quick Rewrite",
        "",
        f"- total_questions: {len(questions)}",
        f"- changed: {changed}",
        f"- missing: {len(missing)}",
        "",
        "## Changed By Type",
        "",
    ]
    for q_type in ["tf", "single", "multi", "blank"]:
        report_lines.append(f"- {q_type}: {by_type[q_type]}")
    report_lines.extend(["", "## Missing Labels", "", ", ".join(missing) if missing else "none", ""])
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
