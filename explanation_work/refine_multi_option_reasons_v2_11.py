from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
BACKUP_PATH = ROOT / "explanation_work" / "questions.before_v2_11_multi_option_refine.json"
REPORT_PATH = ROOT / "explanation_work" / "v2_11_multi_option_refine_report.md"


def load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def clean_option_text(text: str) -> str:
    value = str(text or "").strip()
    return re.sub(r"^[A-Z][\.\u3001\uFF0E]\s*", "", value).strip()


def clean_topic(text: str) -> str:
    value = str(text or "").strip()
    value = value.strip("。；;，, ")
    value = re.sub(r"^\d+[.、\s]*", "", value)
    value = value.replace("（ ）", "").replace("()", "").strip()
    return value


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").replace("\r", " ").replace("\n", " ")).strip()


def answer_keys(answer: str) -> set[str]:
    return set(re.findall(r"[A-Z]", str(answer or "").upper()))


def parse_option_line(line: str):
    stripped = line.strip()
    if not stripped.startswith("- "):
        return None
    body = stripped[2:]
    if not body:
        return None
    key = body[0]
    if not ("A" <= key <= "Z"):
        return None
    colon = body.find("：")
    if colon < 0:
        colon = body.find(":")
    if colon < 0:
        return None
    head = body[:colon].strip()
    tail = body[colon + 1 :].strip()
    opt_text = ""
    left = head.find("（")
    right = head.rfind("）")
    if left >= 0 and right > left:
        opt_text = head[left + 1 : right].strip()
    else:
        opt_text = head[1:].strip(" .。、")
    verdict = ""
    reason = tail
    verdict_match = re.match(r"^(对|错)(?:[，,]\s*)?(?:因为)?(.*)$", tail)
    if verdict_match:
        verdict = verdict_match.group(1)
        reason = verdict_match.group(2).strip()
    return key, opt_text, verdict, reason


def normalize_reason(reason: str) -> str:
    text = str(reason or "").strip()
    text = text.lstrip("因为").strip()
    text = text.strip("。；;，, ")
    return apply_reason_replacements(text)


def apply_reason_replacements(text: str) -> str:
    replacements = {
        "在五层中": "在教学常用的五层体系中",
        "在五层里": "在教学常用的五层体系中",
        "是典型拓扑": "是网络拓扑的经典类型之一",
        "是公式参数": "是香农公式里的参数",
        "是典型模式": "是端系统之间的典型通信方式",
        "是该分类名称": "是这道题对应的标准分类名称",
        "不是该分类名称": "不是这道题对应的标准分类名称",
        "同理，不是教材这里的两类": "同理，不属于教材这里强调的两类端系统通信方式",
        "不是这里的两类": "不是这道题这里强调的两类",
        "等连接方式P2P": "对等连接方式P2P",
        "源MA": "源MAC地址",
        "地址自学习；C用生成树协议避免环路": "透明网桥通过生成树协议避免环路",
        "源MAC源MA": "源MAC地址",
        "源MAC源MAC地址": "源MAC地址",
    }
    for src, dst in replacements.items():
        if src in text:
            text = text.replace(src, dst)
    return text


def starts_with_subject_like(text: str) -> bool:
    if len(text) < 6:
        return True
    prefixes = (
        "是", "为", "在", "由", "属于", "表示", "说明", "负责", "采用", "通过",
        "不是", "不属于", "并非", "可", "能", "会", "需", "用", "有", "无", "适合", "提供",
        "支持", "依赖", "基于", "体现", "意味着",
    )
    return text.startswith(prefixes)


def widen_short_reason(topic: str, opt_text: str, verdict: str, reason: str) -> str:
    topic = clean_topic(topic)
    opt_text = clean_option_text(opt_text)
    text = normalize_reason(reason)

    if not text:
        if verdict == "对":
            return f"{opt_text}符合{topic or '本题考查范围'}。"
        return f"{opt_text}不属于{topic or '本题考查范围'}。"

    if verdict == "对" and opt_text and opt_text not in text and starts_with_subject_like(text):
        text = f"{opt_text}{text}"
    elif verdict == "错" and opt_text and opt_text not in text and starts_with_subject_like(text):
        text = f"{opt_text}{text}"

    if verdict == "对" and topic and topic not in text and len(text) < 18:
        text = f"{text}，符合{topic}"
    elif verdict == "错" and topic and topic not in text and len(text) < 18:
        text = f"{text}，不属于{topic}"

    text = text.strip("。；;，, ")
    if verdict == "对":
        return f"{text}。"
    return f"{text}。"


def rebuild_multi_question(question: dict) -> tuple[str, bool]:
    quick = str(question.get("quickExplanation") or "").replace("\r\n", "\n").replace("\r", "\n")
    if not quick.strip():
        return quick, False

    topic = ""
    for line in quick.splitlines():
        if line.startswith("题眼："):
            topic = line[len("题眼：") :].strip()
            break
    if not topic:
        topic = clean_topic(question.get("stem", ""))

    opt_map = {
        str(opt.get("key", "")).strip(): clean_option_text(opt.get("text", ""))
        for opt in question.get("options", [])
        if str(opt.get("key", "")).strip()
    }
    correct = answer_keys(question.get("answer", ""))

    seen_keys: set[str] = set()
    rebuilt: list[str] = []
    changed = False

    for raw_line in quick.splitlines():
        parsed = parse_option_line(raw_line)
        if not parsed:
            rebuilt.append(raw_line)
            continue

        key, opt_text, verdict, reason = parsed
        seen_keys.add(key)
        opt_text = opt_map.get(key, opt_text or key)
        if not verdict:
            verdict = "对" if key in correct else "错"
        if len(normalize_reason(reason)) < 8:
            reason = widen_short_reason(topic, opt_text, verdict, reason)
        else:
            reason = normalize_reason(reason)
            if opt_text and opt_text not in reason and starts_with_subject_like(reason):
                reason = f"{opt_text}{reason}"
            reason = reason.strip("。；;，, ") + "。"

        new_line = f"- {key}（{opt_text}）：{verdict}，因为{reason.rstrip('。') }。"
        # Normalize duplicate punctuation.
        new_line = re.sub(r"。{2,}", "。", new_line)
        if new_line != raw_line.strip():
            changed = True
        rebuilt.append(new_line)

    # If some option lines are missing, append them so every option is covered.
    for opt in question.get("options", []):
        key = str(opt.get("key", "")).strip()
        if not key or key in seen_keys:
            continue
        opt_text = opt_map.get(key, clean_option_text(opt.get("text", "")) or key)
        verdict = "对" if key in correct else "错"
        reason = widen_short_reason(topic, opt_text, verdict, "")
        rebuilt.append(f"- {key}（{opt_text}）：{verdict}，因为{reason}")
        changed = True

    rebuilt_text = "\n".join(rebuilt).strip()
    if rebuilt_text and not rebuilt_text.endswith("\n"):
        rebuilt_text += "\n"
    return rebuilt_text, changed


def build_explanation(question: dict) -> str:
    quick = str(question.get("quickExplanation") or "").strip()
    detail = str(question.get("knowledgeDetail") or "").strip()
    if quick and detail:
        return f"【快速做题】\n{quick}\n\n【知识点详解】\n{detail}"
    return quick or detail


def main() -> None:
    questions = load_questions()
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(
            json.dumps(questions, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    total_multi = 0
    changed_labels: list[str] = []
    for question in questions:
        if question.get("type") != "multi":
            continue
        total_multi += 1
        rebuilt, changed = rebuild_multi_question(question)
        if changed:
            question["quickExplanation"] = rebuilt.rstrip("\n")
            question["explanation"] = build_explanation(question)
            changed_labels.append(str(question.get("label", "")))

    QUESTIONS_PATH.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    REPORT_PATH.write_text(
        "\n".join(
            [
                "# v2.11 multi option reason refine report",
                "",
                f"- multi_questions: {total_multi}",
                f"- changed_questions: {len(changed_labels)}",
                "",
                "## Changed Labels",
                "",
                ", ".join(changed_labels) if changed_labels else "none",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
