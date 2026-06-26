from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
TARGET = ROOT / "explanation_work" / "agent_outputs" / "relational_v1_chapter4_a.json"


SPECIFIC_TF_OPTION_LINES = {
    "1-5": (
        "- T：不选。题干把路由器说成运输层设备；正确应是网络层按 IP 地址查路由表转发分组。",
        "- F：应选。路由器负责网络互联，运输层负责端到端进程通信，这两个层次不能互换。",
    ),
    "1-6": (
        "- T：不选。VLSM 是把一个地址块按不同掩码继续切分，不是把多个标准网络合并。",
        "- F：应选。多个网络合成更大前缀属于 CIDR 路由聚合思路，和 VLSM 的“细分子网”方向相反。",
    ),
    "1-7": (
        "- T：不选。IPv4 首部校验和确实只管首部，但算法不是 CRC，而是 16 位反码求和。",
        "- F：应选。题干把链路层常见的 CRC 检错机制错套到 IPv4 首部校验和上。",
    ),
    "1-8": (
        "- T：不选。ping 和 tracert/traceroute 依赖 ICMP，IGMP 不负责连通性测试或路径跟踪。",
        "- F：应选。IGMP 的关键词是多播组成员管理，看到 ping、tracert 应立即回到 ICMP。",
    ),
    "1-14": (
        "- T：应选。OSPF 是链路状态协议，洪泛链路状态并用 SPF 计算路径，网络变化后收敛较快。",
        "- F：不选。把 OSPF 判慢，通常是把它和 RIP 这类距离向量协议的收敛特点混在一起了。",
    ),
    "1-25": (
        "- T：应选。转发是单台路由器查表送出口；路由选择是多台路由器通过协议协作生成路由信息。",
        "- F：不选。如果判错，就会把“本机查表动作”和“全网协议协作”两个层级混成一件事。",
    ),
    "1-33": (
        "- T：应选。CIDR 的 /n 前缀表示网络部分，剩余后缀表示主机部分。",
        "- F：不选。CIDR 的核心就是无分类前缀，不能再按 A/B/C 类固定网络位去理解。",
    ),
    "1-34": (
        "- T：不选。NAT/NAPT 只是让私网地址复用公网地址，属于缓解方案，不会扩大 IPv4 地址空间。",
        "- F：应选。根本解决 IPv4 地址耗尽要靠 IPv6 的大地址空间，而不是 NAT 本身。",
    ),
    "1-44": (
        "- T：不选。tracert 的目标是显示路径上的路由器跳点，不是最直接的主机连通性测试命令。",
        "- F：应选。主机连通性测试通常看 ping 的 ICMP Echo；tracert 主要利用 TTL 超时报文跟踪路径。",
    ),
    "1-46": (
        "- T：不选。OSPF 属于链路状态路由协议，距离向量的典型代表是 RIP。",
        "- F：应选。题干把 OSPF 和 RIP 的算法类型对调了。",
    ),
    "1-49": (
        "- T：不选。RIPv1 更新中不携带子网掩码，是有分类路由协议。",
        "- F：应选。支持 VLSM/CIDR 的是 RIPv2 这类携带掩码的无分类信息，而不是 RIPv1。",
    ),
    "1-55": (
        "- T：不选。STP 解决的是交换机/网桥二层环路，不是路由器之间的三层路由回路。",
        "- F：应选。看到生成树要定位到数据链路层交换网络，不能把它当路由协议用。",
    ),
    "1-57": (
        "- T：应选。划分子网会借走一部分主机位做子网号，所以每个子网可容纳主机数会下降。",
        "- F：不选。子网划分提升管理灵活性，但代价就是主机位变少，并且每个子网还要保留网络/广播地址。",
    ),
    "1-63": (
        "- T：应选。按默认 B 类网络看，191.1.255.255 是 191.1.0.0 网络的直接广播地址。",
        "- F：不选。这里不是受限广播 255.255.255.255，而是带有具体网络号的定向广播。",
    ),
    "1-64": (
        "- T：应选。掩码取反后主机位为 1，与 IP 相与会保留主机号部分。",
        "- F：不选。若直接用原掩码相与得到的是网络地址，不是主机地址。",
    ),
    "1-65": (
        "- T：不选。路由器互连可跨不同物理层/链路层，但网络层协议要能统一转发；交换机互连则更受二层协议约束。",
        "- F：应选。题干把交换机和路由器的互连要求一概而论，忽略了二层转发和三层互联的差别。",
    ),
    "1-66": (
        "- T：不选。255.255.255.255 是受限广播地址，只在本网络内广播。",
        "- F：应选。直接广播地址应是“具体网络号 + 主机号全 1”，例如某网络的 x.x.255.255。",
    ),
    "1-71": (
        "- T：不选。三层交换做路由转发时看 IP/路由表，MAC 地址表是二层交换用的。",
        "- F：应选。把 MAC 表当成路由选择依据，就是把二层交换和三层转发混了。",
    ),
    "1-73": (
        "- T：应选。默认路由是路由表没有更具体匹配时使用的兜底路径。",
        "- F：不选。默认路由不是随便选的路由，而是在最长前缀匹配失败后才命中。",
    ),
    "1-74": (
        "- T：应选。ping 发送 ICMP Echo Request，收到 Echo Reply 就说明目标主机在网络层可达。",
        "- F：不选。若把 ping 判错，就会漏掉 ICMP 最常考的回送请求/回答应用。",
    ),
    "1-76": (
        "- T：应选。NAT 在边界设备上把私有地址转换为公网地址，让内网主机访问互联网。",
        "- F：不选。NAT 的核心不是重新分配全球地址，而是在出口处做地址转换和复用。",
    ),
    "1-78": (
        "- T：不选。默认路由是兜底路由，不保证最短路径。",
        "- F：应选。最短路径是路由算法/度量的结果；默认路由只表示“没有更具体项时往这里走”。",
    ),
    "1-79": (
        "- T：应选。ARP 缓存保存同一链路上 IP 地址到 MAC 地址的映射，便于封装数据帧。",
        "- F：不选。ARP 表不是路由表，它解决的是下一跳 IP 对应哪个物理地址。",
    ),
    "1-82": (
        "- T：不选。三层交换的“三层”指网络层，转发对象是 IP 分组。",
        "- F：应选。数据链路层处理帧；把三层交换说成在链路层实现分组转发，层次错了。",
    ),
    "1-84": (
        "- T：不选。IPv6 使用冒号分隔的十六进制表示，并支持零压缩。",
        "- F：应选。点分十进制是 IPv4 的常见写法，不是 IPv6 的地址表示法。",
    ),
    "1-85": (
        "- T：不选。OSPF 是链路状态内部网关协议，不是距离向量协议。",
        "- F：应选。距离向量的典型代表是 RIP；OSPF 的关键词是链路状态、LSA、SPF。",
    ),
    "1-89": (
        "- T：应选。网络层服务可抽象为虚电路服务和数据报服务，对应面向连接与无连接思想。",
        "- F：不选。不能只记互联网采用数据报服务，就否认网络层理论上还有虚电路服务模型。",
    ),
    "1-90": (
        "- T：应选。BGP 是外部网关协议，用于自治系统 AS 之间交换可达性信息。",
        "- F：不选。AS 内常看 RIP/OSPF，AS 间才看 BGP。",
    ),
    "1-94": (
        "- T：应选。IPv4 校验和只覆盖首部，并采用反码求和，不采用 CRC。",
        "- F：不选。CRC 更常见于数据链路层帧检错，不能把它套到 IPv4 首部校验和上。",
    ),
    "1-96": (
        "- T：不选。IP 地址是网络层逻辑地址。",
        "- F：应选。数据链路层使用的是 MAC/硬件地址，IP 地址和 MAC 地址分属不同层。",
    ),
    "1-99": (
        "- T：不选。ping 用的是 ICMP 回送请求/回答，属于询问/查询类报文。",
        "- F：应选。ICMP 差错报告用于目的不可达、超时等情况，不是 ping 的核心报文类型。",
    ),
    "1-101": (
        "- T：不选。RIP 是距离向量路由协议，不是链路状态协议。",
        "- F：应选。链路状态的典型代表是 OSPF；题干把 RIP 和 OSPF 的协议类型混了。",
    ),
    "1-102": (
        "- T：应选。IGMP 报文封装在 IP 数据报中，同时帮助 IP 层完成多播组成员管理。",
        "- F：不选。IGMP 既“借 IP 传输”，又“服务于 IP 多播”，这正是题干考点。",
    ),
    "1-105": (
        "- T：应选。ping 的基本报文对就是 ICMP Echo Request 和 Echo Reply。",
        "- F：不选。把 ping 看成其他 ICMP 差错报文，会错过“回送请求/回答”这个固定搭配。",
    ),
    "1-110": (
        "- T：不选。二层交换机在数据链路层，路由器在网络层。",
        "- F：应选。两者都是转发设备，但查看的地址字段和 TCP/IP 层次不同，不能归为同一层。",
    ),
}


def clean_reason(quick: str) -> str:
    match = re.search(r"本题理由：(.+?)(?:\n选项判断：|\Z)", quick, flags=re.S)
    if not match:
        return ""
    reason = " ".join(match.group(1).strip().split())
    return reason.rstrip("。") + "。"


def build_tf_quick(question: dict, reason: str) -> str:
    answer = question.get("answer")
    if answer == "TRUE":
        option_lines = [
            f"- T：应选。{reason}",
            "- F：不选。题干说法成立，判错会把本题的层次或机制关系反过来。",
        ]
        verdict = "正确"
    else:
        option_lines = [
            f"- T：不选。题干错在：{reason}",
            "- F：应选。本题应判错误，因为题干把上面的关键关系说反或偷换了概念。",
        ]
        verdict = "错误"
    return "\n".join(
        [
            f"本题判断：{verdict}。",
            f"本题理由：{reason}",
            "选项判断:",
            *option_lines,
        ]
    ).replace("选项判断:", "选项判断：")


def repair_detail(detail: str) -> str:
    text = detail
    text = text.replace("- 归属考点：", "- 相关知识：")
    text = text.replace("- 判定依据：", "- 本题落点：")
    text = re.sub(r"(?m)^- 先抓本题关键词：(.+)$", r"- 做题先抓关键词：\1。", text)
    text = text.replace("题干中的关键词容易和相邻概念混用", "考试常把这个概念和相邻概念互换")
    text = text.replace("。。", "。")
    return text


def repair_quick_text(quick: str) -> str:
    text = quick.replace("的P地址", "的 IP 地址")
    return text


def apply_specific_option_lines(row: dict) -> None:
    lines = SPECIFIC_TF_OPTION_LINES.get(row["label"])
    if not lines:
        return
    quick = row.get("quickExplanation", "")
    prefix = quick.split("选项判断：", 1)[0].rstrip()
    row["quickExplanation"] = "\n".join([prefix, "选项判断：", *lines])


def main() -> None:
    questions = {q["label"]: q for q in json.loads(QUESTIONS.read_text(encoding="utf-8"))}
    rows = json.loads(TARGET.read_text(encoding="utf-8"))
    for row in rows:
        q = questions[row["label"]]
        if q.get("type") == "tf":
            reason = clean_reason(row.get("quickExplanation", ""))
            if reason:
                row["quickExplanation"] = build_tf_quick(q, reason)
            apply_specific_option_lines(row)
        row["quickExplanation"] = repair_quick_text(row.get("quickExplanation", ""))
        row["knowledgeDetail"] = repair_detail(row.get("knowledgeDetail", ""))
    TARGET.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
