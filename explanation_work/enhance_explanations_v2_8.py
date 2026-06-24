# -*- coding: utf-8 -*-
"""Reshape quiz explanations into knowledge-first three-part notes.

Target structure for every question:
1. 核心知识点
2. 题目变形
3. 知识拓展

The script keeps a short `quickExplanation` for in-app first-screen reading, but
removes the old step-by-step template language from both quick and detailed
sections.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from build_chapter_cards_v2_7 import SEEDS
from enhance_explanations_v2_6 import (
    answer_keys,
    answer_text,
    apply_metadata_fix,
    clean_space,
    eye_of,
    label_of,
    option_map,
    reason_of,
    sentence_trim,
    strip_numbering,
    topic_profile,
    trap_of,
)


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
BACKUP = ROOT / "explanation_work" / "questions.before_v2_8_knowledge_structure.json"
REPORT = ROOT / "explanation_work" / "v2_8_knowledge_structure_report.md"

FORBIDDEN_PATTERNS = [
    "第一步",
    "第二步",
    "第三步",
    "一步步做",
    "本题怎么一步步做",
    "先定规则",
    "做题理由",
    "小白复述",
]


SPECIAL_TERMS = [
    "ARPANET",
    "Internet",
    "WWW",
    "Web",
    "ADSL",
    "DSLAM",
    "HFC",
    "cable modem",
    "CIDR",
    "VLSM",
    "NAT",
    "NAPT",
    "IPv4",
    "IPv6",
    "PPP",
    "HDLC",
    "LCP",
    "NCP",
    "SONET",
    "SDH",
    "ICMP",
    "IGMP",
    "ARP",
    "ping",
    "tracert",
    "TCP/IP",
    "OSI",
    "RFC",
    "ATM",
    "CSMA/CD",
    "CSMA/CA",
    "MAC",
    "STDM",
    "CDMA",
    "FTTx",
    "FTTH",
    "FTTB",
    "FTTC",
    "UTP",
    "STP",
    "互联网",
    "万维网",
    "接入网",
    "边缘部分",
    "核心部分",
    "资源子网",
    "通信子网",
    "物理层",
    "数据链路层",
    "网络层",
    "运输层",
    "会话层",
    "表示层",
    "应用层",
    "网际层",
    "网络接口层",
    "IP 地址",
    "子网掩码",
    "网络地址",
    "广播地址",
    "最长前缀匹配",
    "可变长子网掩码",
    "双协议栈",
    "隧道技术",
    "默认路由",
    "默认网关",
    "本机回环",
    "受限广播",
    "回送请求",
    "回送回答",
    "差错报告报文",
    "询问报文",
    "点到点链路",
    "点到点信道",
    "全双工",
    "半双工",
    "单工",
    "字符填充",
    "零比特填充",
    "冲突域",
    "广播域",
    "存储转发",
    "封装成帧",
    "透明传输",
    "差错检测",
    "核心特点",
    "基本特点",
]

TERM_SUFFIX_RE = re.compile(
    r"[\u4e00-\u9fff]{1,8}(?:层|地址|掩码|报文|协议|网关|广播|时延|带宽|吞吐量|"
    r"信道|链路|交换|路由|网络|前缀|主机号|网络号|首部|冲突域|广播域)"
)

IP_LIKE_RE = re.compile(r"\d+(?:\.\d+){1,3}(?:/\d+)?")
ACRONYM_RE = re.compile(r"[A-Za-z][A-Za-z0-9./-]*")


def unique_keep(items):
    seen = set()
    out = []
    for item in items:
        value = clean_space(item)
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def seed_for(q):
    seed = SEEDS.get(q.get("knowledge"))
    if seed:
        return seed
    profile = topic_profile(q)
    return {
        "layer": profile["model"],
        "core": [profile["model"]],
        "must": [],
        "traps": [profile["boundary"]],
    }


def rotate_pick(items, index, count):
    items = unique_keep(items)
    if not items:
        return []
    out = []
    for offset in range(min(count, len(items))):
        out.append(items[(index + offset) % len(items)])
    return out


def question_text(q):
    parts = [
        q.get("stem", ""),
        q.get("knowledge", ""),
        q.get("chapter", ""),
        reason_of(q),
        " ".join(str(opt.get("text", "")) for opt in q.get("options", []) or []),
    ]
    return clean_space(" ".join(parts))


def extract_terms(text):
    text = clean_space(text)
    if not text:
        return []
    terms = []
    seen = set()

    def add(term):
        value = clean_space(term)
        if len(value) < 2:
            return
        if value not in seen:
            seen.add(value)
            terms.append(value)

    for term in SPECIAL_TERMS:
        if term in text:
            add(term)
    for part in ACRONYM_RE.findall(text):
        add(part)
    for part in IP_LIKE_RE.findall(text):
        add(part)
    for part in TERM_SUFFIX_RE.findall(text):
        add(part)
    return terms


def question_term_weights(q):
    weights = {}

    def push(text, base):
        for term in extract_terms(text):
            weight = base
            if ACRONYM_RE.fullmatch(term):
                weight += 5
            elif term in SPECIAL_TERMS:
                weight += 3
            elif term.endswith("层"):
                weight += 4
            elif len(term) >= 4:
                weight += 2
            weights[term] = max(weights.get(term, 0), weight)

    push(q.get("stem", ""), 8)
    push(eye_of(q), 6)
    push(reason_of(q), 5)
    push(" ".join(str(opt.get("text", "")) for opt in q.get("options", []) or []), 4)
    push(answer_text(q), 3)
    push(q.get("knowledge", ""), 1)
    return weights


def score_item(item, token_weights):
    item = clean_space(item)
    score = 0
    for token, weight in token_weights.items():
        if token in item:
            score += weight
            if ACRONYM_RE.fullmatch(token):
                score += 4
            elif token in SPECIAL_TERMS:
                score += 2
            elif len(token) >= 4:
                score += 1
    return score


def scored_seed_items(q, items):
    values = unique_keep(items)
    token_weights = question_term_weights(q)
    ranked = sorted(
        [(value, score_item(value, token_weights), index) for index, value in enumerate(values)],
        key=lambda row: (-row[1], row[2]),
    )
    return ranked


def ranked_seed_items(q, items):
    return [value for value, _, _ in scored_seed_items(q, items)]


def best_seed_item(q, items, fallback=""):
    ranked = ranked_seed_items(q, items)
    if ranked:
        return ranked[0]
    return fallback


def best_seed_item_with_score(q, items, fallback=""):
    ranked = scored_seed_items(q, items)
    if ranked:
        value, score, _ = ranked[0]
        return value, score
    return fallback, -1


def reason_fact(q):
    text = clean_space(reason_of(q))
    if not text:
        return ""
    for sep in ("；题干", ";题干", "。题干", "，题干", ",题干"):
        if sep in text:
            text = text.split(sep, 1)[0]
    text = re.sub(r"^(时间顺序反了|重点是|关键是|关键在于|原因是|因为|本题真正考的是|本题考的是)[，：: ]*", "", text)
    return sentence_trim(text, 140)


def layer_sentence(seed):
    return sentence_trim(clean_space(seed.get("layer", "")), 120)


def join_cn(items):
    values = [clean_space(x).strip("。；;，,：: ") for x in items if clean_space(x)]
    if not values:
        return ""
    return "、".join(values)


def stem_statement(q):
    text = strip_numbering(q.get("stem", ""))
    text = re.sub(r"[（(]\s*[）)]\s*$", "", text)
    text = re.sub(r"[_＿]+", "", text)
    text = re.sub(r"[。；;：:？?！!]+$", "", text)
    return clean_space(text)


def selected_option_values(q):
    amap = option_map(q)
    values = []
    for key in answer_keys(q):
        value = clean_space(amap.get(key, ""))
        if value:
            values.append(value)
    return values


def rejected_option_values(q):
    amap = option_map(q)
    answer_set = set(answer_keys(q))
    return [clean_space(value) for key, value in amap.items() if key not in answer_set and clean_space(value)]


def question_center_reason(q):
    reason = clean_space(reason_fact(q))
    if not reason:
        return ""
    if q.get("type") == "multi":
        return ""
    if any(flag in reason for flag in ("应选", "不选", "排除组", "正确项", "错误项")):
        return ""
    return sentence_trim(reason, 140)


def multi_core_statement(q):
    selected = selected_option_values(q)
    if not selected:
        return ""
    subject = clean_space(eye_of(q) or stem_statement(q))
    subject = re.sub(r"[：:。；;，, ]+$", "", subject)
    picked = join_cn(selected)
    if not subject:
        base = f"本题对应的正确并列知识点包括{picked}。"
    elif "方向" in subject or "双工" in subject:
        base = f"{subject}是{picked}。"
    elif subject.endswith("有"):
        base = f"{subject}{picked}。"
    else:
        base = f"{subject}包括{picked}。"
    rejected = rejected_option_values(q)
    if len(rejected) == 1:
        base += f"不包括{rejected[0]}。"
    return sentence_trim(base, 140)


def true_false_core_statement(q):
    reason = question_center_reason(q)
    if reason:
        return reason
    statement = stem_statement(q)
    if not statement:
        return ""
    keys = answer_keys(q)
    if keys and keys[0] == "TRUE":
        return sentence_trim(statement + "。", 140)
    return ""


def question_center_fact(q):
    if q.get("type") == "multi":
        value = multi_core_statement(q)
        if value:
            return value
    if q.get("type") == "tf":
        value = true_false_core_statement(q)
        if value:
            return value
    value = question_center_reason(q)
    if value:
        return value
    return ""


def question_specific_pack(q):
    text = question_text(q)
    eye = clean_space(eye_of(q))
    if any(token in text for token in ("NAT", "NAPT", "IPv6")):
        return {
            "variant": "NAT 在私有地址和公网地址之间转换，能缓解 IPv4 地址不足，但根本扩容还要靠 IPv6。",
            "model": "这类题先分“缓解”和“根治”：NAT/NAPT 属于地址复用与转换机制，IPv6 才是从地址空间上根本扩容。",
            "points": [
                "NAT/NAPT 的作用是让私网地址复用公网地址，缓解 IPv4 地址紧张。",
                "真正从地址数量上解决 IPv4 耗尽问题的是 IPv6 的 128 bit 地址空间。",
                "遇到“最根本”“彻底解决”这类绝对词，要先想是不是在偷换“缓解”和“根治”。",
            ],
            "contrast": "NAT 是缓解机制，不是根本扩容方案；根本扩容靠 IPv6。",
        }
    if "PPP" in text:
        return {
            "variant": "PPP 不提供可靠传输，不使用序号和确认机制保证可靠交付。",
            "model": "PPP 题先抓它的本体：它是点到点链路层协议，特点是点到点、全双工、简单、不纠错、可承载多种网络层协议。",
            "points": [
                "PPP 适用于点到点链路。",
                "PPP 设计简单，不负责可靠传输和纠错。",
                "PPP 可通过 NCP 支持多种网络层协议。",
            ],
            "contrast": "PPP 是点到点链路层协议，不是 P2P 应用通信模式，也不提供 TCP 那样的可靠流量控制。",
        }
    if "TCP" in text and any(token in text for token in ("字节流", "报文段", "分段", "首部")):
        return {
            "variant": "TCP 面向字节流，会把应用数据划分成报文段，加上 TCP 首部后再交给网络层。",
            "model": "这类题先分清 TCP 向下交付的对象：应用层给 TCP 的是应用数据，TCP 会分段并加首部后再交给网络层。",
            "points": [
                "TCP 面向字节流，不保留应用报文边界。",
                "TCP 会把应用数据划分成报文段，并为每段加上 TCP 首部。",
                "真正交给网络层的是带 TCP 首部的报文段，而不是原封不动的应用数据。",
            ],
            "contrast": "TCP 面向字节流；UDP 更强调按用户数据报直接封装，不提供 TCP 这种可靠字节流机制。",
        }
    if "bps" in text or "baud" in text.lower() or "比特率" in text or "码元率" in text:
        return {
            "variant": "1B = 8b；baud 表示每秒码元数，不等于 bit/s。",
            "model": "速率单位题先分清 bit、Byte、baud：bps 是每秒比特数，Byte 是字节，baud 是每秒码元数。",
            "points": [
                "b 是 bit，B 是 Byte，1B = 8b。",
                "bps 表示 bit per second；baud 表示每秒码元数，二者只有在 1 个码元恰好携带 1 bit 时才数值相同。",
                "遇到单位题，先看它问的是“位”“字节”还是“码元”。",
            ],
            "contrast": "bps 不是 Bytes/s，也不是 baud；bit、Byte、baud 三个量不要混。",
        }
    if any(token in text for token in ("全双工", "半双工", "单工")):
        return {
            "variant": "半双工可以双向传输，但不能双方同时传；单工只能单向传输。",
            "model": "方向性题先背三分法：单工只单向，半双工能双向但不能同时，全双工则能同时双向收发。",
            "points": [
                "单工：只能一个方向传输。",
                "半双工：两个方向都能传，但同一时刻只能一个方向工作。",
                "全双工：两个方向可以同时传输和接收。",
            ],
            "contrast": "半双工和全双工都能双向，但是否“同时”是分界线。",
        }
    if (
        ("网络层" in text and ("运输层" in text or "应用层" in text))
        and any(token in text for token in ("之间", "上面", "下面", "之上", "之下", "顺序", "层次", "自下而上", "自上而下"))
    ):
        return {
            "variant": "OSI 七层中网络层在数据链路层之上、运输层之下；应用层在最上面。",
            "model": "层次顺序题先把层从下往上排出来，再定位题干提到的那一层在谁上面、在谁下面。",
            "points": [
                "OSI 七层顺序：物理层、数据链路层、网络层、运输层、会话层、表示层、应用层。",
                "教学五层里网络层也在运输层下面，应用层在最上面。",
                "这类题常考“谁在谁上面/下面”，不是只考层名会不会背。",
            ],
            "contrast": "网络层在运输层下面，不在运输层和应用层之间。",
        }
    if "ICMP" in text or "ping" in text.lower():
        return {
            "variant": "ping 使用 ICMP 回送请求和回送回答报文，属于询问报文，不属于差错报告报文。",
            "model": "ICMP 题常考“两大类”：差错报告报文和询问报文；ping 对应的是回送请求/回送回答这组询问报文。",
            "points": [
                "ICMP 有差错报告报文，也有询问报文。",
                "ping 用的是回送请求和回送回答。",
                "看到 ping，不要条件反射地归到“差错报告”。",
            ],
            "contrast": "ICMP 不只有差错报告；ping 走的是询问报文。",
        }
    if any(token in text for token in ("ADSL", "HFC", "cable modem")):
        return {
            "variant": "ADSL 用户侧需要 ADSL modem，HFC 的 cable modem 通常在用户侧使用，不能机械理解成两端成对摆放。",
            "model": "接入网题先分清“用户侧设备”和“运营商侧设备”，不要把一种接入技术的设备结构直接套到另一种技术上。",
            "points": [
                "ADSL 常见的是用户侧 modem + 局端 DSLAM。",
                "HFC 的 cable modem 通常是用户侧接入设备。",
                "接入技术相似，不代表设备部署方式完全一样。",
            ],
            "contrast": "ADSL 的两端设备模式不能机械套到 HFC。",
        }
    if "光纤" in text and "波长" in text:
        return {
            "variant": "按工作波长区，光纤通信可分短波长光纤通信和长波长光纤通信。",
            "model": "这类填空题要抓“分类依据”本身：题干问的是按工作波长区分类，不是按传输模式或是否无线分类。",
            "points": [
                "题干中的分类依据是“工作波长区”。",
                "对应的两类标准术语是短波长光纤通信、长波长光纤通信。",
                "填空要保留“光纤”这个限定，不能只写成短波长、长波长。",
            ],
            "contrast": "这里的短波长/长波长说的是光纤通信工作波长区，不是无线电短波/长波概念。",
        }
    return {}


def core_definition(q, seed):
    centered = question_center_fact(q)
    if centered:
        return sentence_trim(centered, 140)
    core = unique_keep(seed.get("core", []))
    if core:
        best_core, core_score = best_seed_item_with_score(q, core, core[0])
        factual_traps = [
            item
            for item in unique_keep(seed.get("traps", []))
            if not any(flag in item for flag in ("看到", "不要自动", "机械套", "题干把", "要看清"))
        ]
        if factual_traps:
            best_trap, trap_score = best_seed_item_with_score(q, factual_traps, factual_traps[0])
            if trap_score >= core_score + 6:
                return sentence_trim(best_trap, 140)
        return sentence_trim(best_core, 140)
    return sentence_trim(topic_profile(q)["model"], 140)


def hit_sentence(q):
    reason = reason_fact(q)
    eye = eye_of(q)
    if reason:
        return reason
    return f"题干真正要你分清的是“{eye}”背后的规则。"


def variant_statement(q, seed):
    pack = question_specific_pack(q)
    custom = clean_space(pack.get("variant", ""))
    if custom and clean_space(custom) != clean_space(core_definition(q, seed)):
        return sentence_trim(custom, 88)
    core_value = core_definition(q, seed)
    pool = [
        item
        for item in ranked_seed_items(q, seed.get("must", []) + seed.get("core", []))
        if clean_space(item) != clean_space(core_value)
    ]
    if not pool:
        return sentence_trim(topic_profile(q)["model"], 88)
    return sentence_trim(pool[0], 88)


def variant_tip(q, seed, profile):
    trap = sentence_trim(trap_of(q), 88)
    if trap:
        return trap
    traps = unique_keep(seed.get("traps", []))
    if traps:
        return sentence_trim(traps[0], 88)
    return sentence_trim(profile["boundary"], 88)


def contrast_sentence(q, seed, profile):
    pack = question_specific_pack(q)
    custom = clean_space(pack.get("contrast", ""))
    if custom:
        return sentence_trim(custom, 110)
    traps = ranked_seed_items(q, seed.get("traps", []))
    if traps:
        return sentence_trim(traps[0], 110)
    return sentence_trim(profile["boundary"], 110)


def extension_points(q, seed, variant):
    used = {clean_space(variant), clean_space(core_definition(q, seed))}
    pack = question_specific_pack(q)
    custom_points = [item for item in unique_keep(pack.get("points", [])) if clean_space(item) not in used]
    pool = [item for item in ranked_seed_items(q, seed.get("core", []) + seed.get("must", [])) if clean_space(item) not in used]
    return unique_keep(custom_points + pool)[:3]


def extension_model(q, seed, profile):
    pack = question_specific_pack(q)
    custom = clean_space(pack.get("model", ""))
    if custom:
        return sentence_trim(custom, 180)
    points = ranked_seed_items(q, seed.get("core", []) + seed.get("must", []))[:2]
    parts = [layer_sentence(seed)] + points
    value = "；".join(clean_space(x) for x in parts if clean_space(x))
    if value:
        return sentence_trim(value, 180)
    return sentence_trim(profile["model"], 180)


def make_quick(q):
    lines = [
        f"题眼：{sentence_trim(eye_of(q), 72)}",
        f"答案：{answer_text(q)}",
        f"理由：{sentence_trim(reason_fact(q) or hit_sentence(q), 150)}",
        f"易错：{sentence_trim(trap_of(q), 96)}",
    ]
    return "\n".join(lines)


def make_knowledge(q):
    seed = seed_for(q)
    profile = topic_profile(q)
    variant = variant_statement(q, seed)
    lines = [
        "核心知识点：",
        f"本体定义：{core_definition(q, seed)}",
        f"所在层次：{layer_sentence(seed)}",
        f"本题命中：{hit_sentence(q)}",
        "",
        "题目变形：",
        f"变形题：判断正误：{variant}",
        "变形答案：正确。",
        f"变形提醒：{variant_tip(q, seed, profile)}",
        "",
        "知识拓展：",
        f"底层模型：{extension_model(q, seed, profile)}",
    ]
    for item in extension_points(q, seed, variant):
        lines.append(f"- {item}")
    lines.extend(
        [
            f"易混对比：{contrast_sentence(q, seed, profile)}",
            f"易错：{sentence_trim(trap_of(q), 110)}",
        ]
    )
    return "\n".join(lines)


def make_full_explanation(q):
    return f"【快速做题】\n{q['quickExplanation']}\n\n【知识点详解】\n{q['knowledgeDetail']}"


def count_hits(questions, token, field=None):
    total = 0
    for q in questions:
        text = q.get(field, "") if field else "\n".join(
            [q.get("quickExplanation", ""), q.get("knowledgeDetail", ""), q.get("explanation", "")]
        )
        if token in text:
            total += 1
    return total


def main():
    if not BACKUP.exists():
        shutil.copy2(QUESTIONS, BACKUP)
    questions = json.loads(BACKUP.read_text(encoding="utf-8"))

    missing_seeds = set()
    for q in questions:
        apply_metadata_fix(q)
        if q.get("knowledge") not in SEEDS:
            missing_seeds.add(q.get("knowledge", ""))
        q["quickExplanation"] = make_quick(q)
        q["knowledgeDetail"] = make_knowledge(q)
        q["explanation"] = make_full_explanation(q)

    QUESTIONS.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    forbidden_counts = {token: count_hits(questions, token) for token in FORBIDDEN_PATTERNS}
    structure_counts = {
        "核心知识点": count_hits(questions, "核心知识点：", "knowledgeDetail"),
        "题目变形": count_hits(questions, "题目变形：", "knowledgeDetail"),
        "知识拓展": count_hits(questions, "知识拓展：", "knowledgeDetail"),
    }
    avg_quick = sum(len(q.get("quickExplanation", "")) for q in questions) / len(questions)
    avg_detail = sum(len(q.get("knowledgeDetail", "")) for q in questions) / len(questions)
    avg_full = sum(len(q.get("explanation", "")) for q in questions) / len(questions)

    REPORT.write_text(
        "# v2.8 知识点解析重构报告\n\n"
        f"- 题目总数：{len(questions)}\n"
        f"- 备份文件：{BACKUP}\n"
        f"- quickExplanation 平均长度：{avg_quick:.1f}\n"
        f"- knowledgeDetail 平均长度：{avg_detail:.1f}\n"
        f"- explanation 平均长度：{avg_full:.1f}\n"
        f"- 缺失 seed 的知识点：{sorted(x for x in missing_seeds if x) or '无'}\n\n"
        "## 三段结构覆盖\n\n"
        + "\n".join(f"- {name}：{value}/{len(questions)}" for name, value in structure_counts.items())
        + "\n\n## 禁用旧模板词残留\n\n"
        + "\n".join(f"- {name}：{value}" for name, value in forbidden_counts.items())
        + "\n",
        encoding="utf-8",
    )

    print(f"updated {len(questions)} questions")
    print(f"backup: {BACKUP}")
    print(f"report: {REPORT}")
    print(f"missing seeds: {len([x for x in missing_seeds if x])}")


if __name__ == "__main__":
    main()
