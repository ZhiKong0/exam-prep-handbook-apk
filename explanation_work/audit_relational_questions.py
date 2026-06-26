import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "questions.json"

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
    "与题干问法不贴合",
    "本题要抓的是",
    "关键是按正确概念层次逐项判断",
]


def option_keys(question):
    keys = []
    for index, option in enumerate(question.get("options") or []):
        key = option.get("key")
        if key == "TRUE":
            keys.append("T")
        elif key == "FALSE":
            keys.append("F")
        elif key:
            keys.append(str(key).strip().upper())
        else:
            keys.append(chr(ord("A") + index))
    return keys


def has_option_line(text, key):
    return re.search(rf"(?m)^\s*[-*•]?\s*{re.escape(key)}\s*[：:]", text) is not None


def main():
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    counts = Counter()
    by_chapter = defaultdict(Counter)
    samples = defaultdict(list)

    for q in questions:
        chapter = q.get("chapter", "")
        quick = q.get("quickExplanation") or ""
        detail = q.get("knowledgeDetail") or ""
        whole = quick + "\n" + detail

        def add(issue):
            counts[issue] += 1
            by_chapter[chapter][issue] += 1
            if len(samples[issue]) < 20:
                samples[issue].append(q.get("label"))

        if "题目变形" in whole:
            add("forbidden_variant")
        if BAD_CHARS_RE.search(whole) or "???" in whole:
            add("bad_chars")
        if "核心知识框架" not in detail:
            add("missing_framework")
        if "做题抓手" not in detail:
            add("missing_grip")
        if "知识关系表" not in detail:
            add("missing_relation_table_header")
        if "易混辨析表" not in detail:
            add("missing_discrimination_table_header")
        if not TABLE_RE.search(detail):
            add("missing_markdown_table")
        for phrase in GENERIC_PHRASES:
            if phrase in whole:
                add("generic_phrase")
                break
        if q.get("options"):
            if "本题理由" not in quick:
                add("missing_reason")
            if "选项判断" not in quick:
                add("missing_option_section")
            for key in option_keys(q):
                if not has_option_line(quick, key):
                    add("missing_option_line")
                    break

    result = {
        "total": len(questions),
        "issueCounts": dict(counts),
        "byChapter": {chapter: dict(counter) for chapter, counter in by_chapter.items()},
        "samples": dict(samples),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if counts:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
