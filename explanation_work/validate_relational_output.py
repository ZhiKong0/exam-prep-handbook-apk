import argparse
import json
import re
from pathlib import Path


TABLE_RE = re.compile(r"(?m)^\|.+\|\s*\n^\|[\s:\-|]+\|")
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


def option_keys(question):
    keys = []
    for index, option in enumerate(question.get("options") or []):
        key = option.get("key")
        text = option.get("text") or ""
        if key == "TRUE":
            keys.append("T")
        elif key == "FALSE":
            keys.append("F")
        elif key:
            keys.append(str(key).strip().upper())
        else:
            match = re.match(r"\s*([A-DTF])\s*[.．、:：]", text, flags=re.I)
            keys.append(match.group(1).upper() if match else chr(ord("A") + index))
    return keys


def has_option_line(text, key):
    return re.search(rf"(?m)^\s*[-*•]?\s*{re.escape(key)}\s*[：:]", text) is not None


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def validate(output_path, questions_path, chapters, labels):
    questions = load_json(questions_path)
    by_label = {q["label"]: q for q in questions}
    chapter_set = set(chapters or [])
    label_set = set(labels or [])
    rows = load_json(output_path)
    if not isinstance(rows, list):
        raise SystemExit("output must be a JSON array")

    issues = []
    seen = set()
    for row in rows:
        label = row.get("label")
        if not label:
            issues.append("missing label")
            continue
        if label in seen:
            issues.append(f"{label}: duplicate label")
        seen.add(label)
        q = by_label.get(label)
        if not q:
            issues.append(f"{label}: unknown label")
            continue
        if label_set and label not in label_set:
            issues.append(f"{label}: label not in requested subset")
        if chapter_set and q.get("chapter") not in chapter_set:
            issues.append(f"{label}: chapter mismatch {q.get('chapter')!r}")

        quick = row.get("quickExplanation") or ""
        detail = row.get("knowledgeDetail") or ""
        whole = quick + "\n" + detail

        if "题目变形" in whole:
            issues.append(f"{label}: contains forbidden 题目变形")
        if BAD_CHARS_RE.search(whole) or "???" in whole:
            issues.append(f"{label}: suspect mojibake chars")
        for phrase in GENERIC_PHRASES:
            if phrase in whole:
                issues.append(f"{label}: generic phrase {phrase}")
        for required in ("本题理由", "选项判断"):
            if q.get("options") and required not in quick:
                issues.append(f"{label}: quickExplanation missing {required}")
        for key in option_keys(q):
            if not has_option_line(quick, key):
                issues.append(f"{label}: quickExplanation missing option line {key}")

        if "核心知识框架" not in detail:
            issues.append(f"{label}: knowledgeDetail missing 核心知识框架")
        if "做题抓手" not in detail:
            issues.append(f"{label}: knowledgeDetail missing 做题抓手")
        if "知识关系表" not in detail and "易混辨析表" not in detail:
            issues.append(f"{label}: knowledgeDetail missing relation/discrimination section")
        if not TABLE_RE.search(detail):
            issues.append(f"{label}: knowledgeDetail has no markdown table")

    if label_set:
        expected = [label for label in labels if label in by_label]
        unknown = sorted(label_set - set(by_label))
        for label in unknown:
            issues.append(f"{label}: requested label not found in questions")
    else:
        expected = [
            q["label"]
            for q in questions
            if not chapter_set or q.get("chapter") in chapter_set
        ]
    missing = sorted(set(expected) - seen)
    extra = sorted(seen - set(expected))
    for label in missing:
        issues.append(f"{label}: missing output")
    for label in extra:
        issues.append(f"{label}: extra output")

    summary = {
        "output": str(output_path),
        "chapters": sorted(chapter_set),
        "labels": len(label_set),
        "rows": len(rows),
        "expected": len(expected),
        "issues": len(issues),
        "sampleIssues": issues[:50],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if issues:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--questions", default="app/src/main/assets/questions.json")
    parser.add_argument("--chapter", default="")
    parser.add_argument("--chapters", nargs="*", default=[])
    parser.add_argument("--labels", nargs="*", default=[])
    args = parser.parse_args()
    chapters = args.chapters or ([args.chapter] if args.chapter else [])
    validate(args.output, args.questions, chapters, args.labels)


if __name__ == "__main__":
    main()
