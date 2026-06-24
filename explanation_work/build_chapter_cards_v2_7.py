# -*- coding: utf-8 -*-
"""Build exhaustive chapter memory-card data for the Android quiz app.

The app should not infer review cards by sampling the first few explanations:
that loses small exam facts.  This script treats questions.json as the source
of truth, adds hand-curated beginner review points for every knowledge group,
and then appends one short coverage line for every question in the group.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
CARDS_PATH = ROOT / "app" / "src" / "main" / "assets" / "chapter_cards.json"
REPORT_PATH = ROOT / "explanation_work" / "chapter_cards_v2_7_coverage.md"


SEEDS = {
    "互联网发展、组成与通信方式": {
        "layer": "全局基础。先分清互联网、Web/WWW、接入网、边缘部分和核心部分，再判断端系统采用 C/S 还是 P2P。",
        "core": [
            "互联网不是某一个应用：Web/WWW 是运行在互联网之上的应用服务，Internet 是底层互连网络。",
            "时间顺序要背清：ARPANET 先出现并发展，后来形成 Internet；Web 的普及推动 Internet 应用，不是推动 ARPANET 诞生。",
            "互联网组成常考“两部分”：边缘部分是主机、服务器、手机等端系统，核心部分是大量路由器和网络组成的分组交换网。",
            "边缘端系统常见通信方式是 C/S 和 P2P；B/S 是浏览器/服务器形式，本质仍属于 C/S，不是与 C/S 并列的端系统通信大类。",
            "Internet 的两个重要基本特点是连通性和共享；共享指资源、信息和服务可通过网络被访问。",
            "接入网只负责把用户接入互联网，不能把 ADSL、HFC、局域网接入误当成互联网本身。",
            "ADSL 用户侧需要 ADSL modem，另一端通常接入运营商 DSLAM；HFC 的 cable modem 是用户侧接入设备，不是两端成对使用。",
        ],
        "must": [
            "C/S = Client/Server，P2P = Peer-to-Peer；P2P 是题库填空标准答案。",
            "Internet = 互联网；WWW/Web = 万维网，是应用层服务。",
            "互联网基本特点：连通性、共享。",
        ],
        "traps": [
            "看到 Web 不要自动等同“互联网起源”。",
            "题干把 C/S 和 B/S 并列时通常在偷换分类口径。",
            "接入设备是否“成对使用”要看具体技术，不能机械套 modem 两端成对。",
        ],
    },
    "交换技术与网络性能指标": {
        "layer": "全局性能与核心交换模型。重点是电路交换、报文交换、分组交换，以及带宽、时延、吞吐量等指标。",
        "core": [
            "电路交换先建立专用电路，适合连续实时业务；资源预留但空闲时会浪费。",
            "分组交换把长报文切成分组，采用存储转发；常见实现方式是数据报和虚电路。",
            "数据报方式每个分组独立选路，不保证顺序；虚电路先建立逻辑连接，之后分组沿同一路径转发。",
            "总时延常拆成发送时延 L/R、传播时延 d/v、处理时延和排队时延；排队时延随网络拥塞波动最大。",
            "带宽在通信中常表示信道最高数据率，单位 bit/s；吞吐量是实际通过量，可能低于额定带宽。",
            "RTT 是往返时间；访问 Web 对象时常见考法是 DNS 查询、TCP 建连和 HTTP 请求/响应各占多少 RTT。",
            "奈奎斯特准则和香农公式都描述带宽与速率关系；香农公式强调带宽、信噪比越大，极限传输速率越高。",
        ],
        "must": [
            "分组交换实现方法：数据报、虚电路。",
            "时延公式抓手：发送时延 = 数据长度 / 发送速率；传播时延 = 距离 / 传播速率。",
            "带宽、吞吐量、时延、RTT、利用率要分开背。",
            "香农公式：信道极限传输速率与带宽、信噪比有关。",
        ],
        "traps": [
            "带宽大不等于实际吞吐量一定大，还可能被拥塞、协议开销、瓶颈链路限制。",
            "传播时延看距离和传播速度，发送时延看分组长度和发送速率。",
            "数据报和虚电路都是分组交换，不要把虚电路误认为电路交换。",
        ],
    },
    "协议、标准与分层模型": {
        "layer": "体系结构基础。把协议三要素、OSI 七层、TCP/IP 分层、服务与协议关系分清。",
        "core": [
            "网络协议三要素是语法、语义、同步。语法管格式，语义管含义和动作，同步管事件顺序和时序。",
            "OSI 七层自下而上：物理层、数据链路层、网络层、运输层、会话层、表示层、应用层。",
            "TCP/IP 常按网络接口层、网际层、运输层、应用层理解；教材也可能把网络接口层拆成物理层和数据链路层。",
            "同层实体之间遵守协议；相邻层之间通过服务接口提供服务。协议是水平的，服务是垂直的。",
            "封装方向：发送方从高层到低层逐层加首部/尾部；接收方从低层到高层逐层解封装。",
            "Internet 标准通常以 RFC 形式发表；不是所有 RFC 都自动成为标准。",
            "分层的价值是降低复杂度、模块化和接口清晰，但会有封装开销。",
        ],
        "must": [
            "协议三要素：语法、语义、同步。",
            "Internet 标准文档形式：RFC。",
            "OSI 七层顺序必须能从下到上背出来。",
        ],
        "traps": [
            "“协议”和“服务”不要混：协议管同层通信规则，服务管下层给上层用什么能力。",
            "TCP/IP 没有严格照搬 OSI 七层，题干问哪个体系要看清。",
            "同步不是“时钟同步”狭义，而是通信事件发生顺序和时序规则。",
        ],
    },
    "数据通信基础、信号编码与调制": {
        "layer": "物理层。研究比特如何变成信号、信号如何在信道上传输，以及编码、调制和同步。",
        "core": [
            "数据可以是数字/模拟，信号也可以是数字/模拟；调制解调器负责计算机数字信号与电话线模拟信号之间转换。",
            "基带传输是不调制，直接传电脉冲；频带/带通传输要把数字数据调制到载波上。",
            "模拟载波三个基本要素是幅度、频率、相位；调制常围绕这三者变化。",
            "编码要解决怎样用信号表示 0/1；曼彻斯特编码用每位中间跳变携带同步和数值信息。",
            "为了防止收发双方计时漂移，需要同步；同步不是协议三要素里的同步含义完全相同，要看题干语境。",
            "信道受带宽、噪声、衰减和失真影响；码元速率、数据率、误码率是常见指标。",
            "数据通信系统模型由源系统、传输系统、目的系统组成。",
        ],
        "must": [
            "调制载波三要素：幅度、频率、相位。",
            "调制解调器分类：内置式、外置式。",
            "曼彻斯特图题标准答案：1011011011000011。",
            "未经调制的电脉冲直接传输叫基带传输。",
        ],
        "traps": [
            "数字数据不一定用数字信号传，经过调制也可在模拟信道上传。",
            "曼彻斯特编码要按题图给定规则读，不要凭直觉把高电平直接当 1。",
            "同步在物理层题里常指收发时钟配合，在协议三要素题里指通信时序。",
        ],
    },
    "多路复用与码分多址": {
        "layer": "物理层信道共享。核心是多个用户怎样共用同一传输媒体。",
        "core": [
            "多路复用是静态划分信道，典型有频分复用 FDM、时分复用 TDM、波分复用 WDM、码分复用 CDM。",
            "FDM 按频带切分，TDM 按时间片切分，WDM 本质是光纤中的频分思想，CDM 按码片序列区分用户。",
            "码分多址 CDMA 中各站使用相互正交或近似正交的码片序列，接收端用内积/相关运算把目标用户信号取出来。",
            "静态划分适合稳定业务；随机接入属于动态媒体接入控制，适合突发共享信道。",
            "共享通信媒体的方法可以分为静态划分信道和动态接入控制；动态接入也叫多点接入/随机接入。",
        ],
        "must": [
            "最常用两种复用：频分多路复用、时分多路复用。",
            "共享媒体动态接入标准填法：随机接入。",
            "FDM/TDM/WDM/CDM/CDMA 英文缩写要能和中文互认。",
        ],
        "traps": [
            "复用是物理层共享信道方法，不是网络层路由选择。",
            "TDM 是分时间，不是分频率；FDM 是分频率，不是排队发送。",
            "CDMA 判断站点数据时要看码片正交运算，不是简单看 0/1 个数。",
        ],
    },
    "传输媒体：双绞线、同轴、光纤与无线": {
        "layer": "物理层传输媒体。重点是有线/无线介质的特性、适用场景和标准名词。",
        "core": [
            "有导向媒体包括双绞线、同轴电缆、光纤；非导向媒体包括无线电、微波、红外、激光等。",
            "双绞线有 UTP/STP，常用于以太网接入；同轴电缆可分基带同轴电缆和宽带同轴电缆。",
            "光纤通过光信号传输，需要电信号与光信号转换；优点是带宽大、损耗低、抗电磁干扰强。",
            "无线直线传输常见微波、红外通信、激光通信；它们不需要实体导线，但会受遮挡、距离、天气影响。",
            "高速数字传输系统常见 SONET（美国标准）和 SDH（国际标准）。",
            "构建局域网常见介质：双绞线、同轴电缆、光纤、无线通信信道。",
        ],
        "must": [
            "同轴电缆分类：基带同轴电缆、宽带同轴电缆。",
            "无线直线传输三项：微波、红外通信、激光通信。",
            "SONET 对应美国标准，SDH 对应国际标准。",
            "光纤传输要完成电信号与光信号转换。",
        ],
        "traps": [
            "无线传输媒体不只有无线电波，还包括微波、红外、激光。",
            "光纤不是传电信号，而是传光信号。",
            "基带/宽带在同轴电缆题里是电缆用途分类，在传输方式题里是信号是否调制。",
        ],
    },
    "物理层接口、传输系统与标准": {
        "layer": "物理层接口与传输系统。重点是物理层规定哪些接口特性以及 DTE/DCE 等设备关系。",
        "core": [
            "物理层接口特性常分机械特性、电气特性、功能特性、过程特性。",
            "机械特性规定连接器形状、尺寸、引脚数；电气特性规定电压、电平、阻抗、速率等。",
            "功能特性规定每条信号线的用途；过程特性规定事件顺序和操作过程。",
            "DTE 是数据终端设备，DCE 是数据电路端接设备；物理层接口常发生在二者之间。",
            "物理层不解释比特含义，只保证透明传输比特流。",
        ],
        "must": [
            "物理层接口四特性：机械、电气、功能、过程。",
            "DTE/DCE 中文含义要能识别。",
        ],
        "traps": [
            "物理层只传比特，不负责成帧、寻址、路由或可靠传输。",
            "功能特性不是“应用功能”，而是接口信号线分别做什么。",
        ],
    },
    "成帧、透明传输、差错检测与 ARQ": {
        "layer": "数据链路层基础。把比特流组织成帧，并解决透明传输、差错检测和重传控制。",
        "core": [
            "成帧就是给一段数据加帧界定，让接收方知道一帧从哪里开始、到哪里结束。",
            "透明传输保证数据内容中即使出现和帧定界符相同的比特/字符，也不会被误认为边界。",
            "字符填充常用于面向字节/异步传输；零比特填充常用于面向比特/同步传输。",
            "差错检测常用 CRC/FCS，只能发现大多数差错；发现差错后的可靠交付要靠 ARQ 等机制。",
            "ARQ 是自动重传请求，常见思想是确认、超时、重传；停止等待是最简单的 ARQ。",
            "数据链路层的任务不是端到端，而是相邻结点/同一链路上的帧传输。",
        ],
        "must": [
            "透明传输关键词：字符填充、零比特填充。",
            "ARQ = Automatic Repeat reQuest，自动重传请求。",
            "差错检测不是差错纠正，CRC/FCS 发现错不代表自动改对。",
        ],
        "traps": [
            "链路层可靠传输只管相邻链路，TCP 可靠传输才是端到端。",
            "看到“透明”不是加密隐藏，而是数据内容不受帧定界符影响。",
            "检测到差错通常丢弃或请求重传，不是每次都能纠正。",
        ],
    },
    "PPP、HDLC 与点到点链路": {
        "layer": "数据链路层点到点信道。重点是 PPP、HDLC 的透明传输和链路控制。",
        "core": [
            "数据链路层使用的信道主要有点到点信道和广播信道；PPP 面向点到点链路。",
            "PPP 包含 LCP 用于建立/配置/测试数据链路，NCP 用于配置不同网络层协议。",
            "PPP 本身不提供可靠传输，不使用序号和确认机制保证可靠交付。",
            "PPP 在异步传输时常用字符填充；在 SONET/SDH 同步链路中常用零比特填充。",
            "HDLC 是面向比特的数据链路控制协议，常见帧结构含标志字段。",
            "点到点链路没有共享广播信道的冲突检测问题。",
        ],
        "must": [
            "链路层信道：点到点信道、广播信道。",
            "PPP 异步：字符填充；PPP 同步/SONET/SDH：零比特填充。",
            "PPP = Point-to-Point Protocol。",
        ],
        "traps": [
            "PPP 不是 P2P 文件共享，PPP 是点到点链路层协议。",
            "PPP 不等于 TCP，不保证端到端可靠字节流。",
            "字符填充和零比特填充的使用场景要分清。",
        ],
    },
    "以太网、MAC 地址、CSMA/CD 与交换": {
        "layer": "数据链路层局域网。看到 MAC、以太网帧、交换机、网桥、冲突域/广播域，优先放到链路层。",
        "core": [
            "以太网是局域网技术，工作重点在数据链路层的 MAC 子层；MAC 地址是网卡/适配器的硬件地址。",
            "以太网提供无连接、不可靠服务：不建立连接，不给正确帧逐帧确认，差错帧通常丢弃。",
            "CSMA/CD 可概括为多点接入、载波监听、冲突检测；共享式半双工以太网才需要它，全双工交换式以太网不再发生传统冲突。",
            "10BASE-T：10 Mbit/s、基带、双绞线、星形拓扑。",
            "网桥和以太网交换机工作在数据链路层，根据 MAC 帧的目的地址转发/过滤，并通过自学习建立交换表。",
            "交换机每个接口通常是一个独立冲突域；所有接口默认仍在同一广播域，除非划分 VLAN。",
            "不同 VLAN 之间通信需要路由器或三层交换机进行三层转发。",
            "网络适配器/NIC/网卡负责计算机与局域网通信。",
        ],
        "must": [
            "10BASE-T：星形、10 Mbit/s、双绞线、基带。",
            "CSMA/CD 三词：多点接入、载波监听、冲突检测。",
            "交换机/网桥根据 MAC 帧目的地址转发过滤，工作在数据链路层。",
            "交换机：每端口一个冲突域，默认同一广播域。",
        ],
        "traps": [
            "MAC 地址不是 IP 地址，交换机转发不是路由选择。",
            "交换机隔离冲突域，但不自动隔离广播域。",
            "以太网帧出错通常丢弃，不等同 TCP 那种确认重传可靠机制。",
        ],
    },
    "无线局域网、WPAN 与 802.11/802.15": {
        "layer": "数据链路层无线局域网/个人区域网。重点是 802.11、CSMA/CA、AP 和 WPAN 标准。",
        "core": [
            "IEEE 802.11 系列是无线局域网标准，常称无线以太网；常见类型有 802.11a、802.11b、802.11g、802.11n。",
            "无线信道难以做冲突检测，所以 802.11 使用 CSMA/CA，即冲突避免，不是 CSMA/CD。",
            "802.11 在使用 CSMA/CA 的同时还使用停止等待协议和确认帧，提高链路可靠性。",
            "有固定基础设施的 WLAN 通过 AP 接入；802.11 MAC 帧可有四个地址字段，基础设施模式常用源、目的、AP 三类地址。",
            "WPAN 属于无线个人区域网：蓝牙 802.15.1，低速 ZigBee 802.15.4，高速 WPAN 802.15.3。",
            "无线局域网、传统以太网都属于局域网技术，但媒体接入控制方式不同。",
        ],
        "must": [
            "常见 WLAN 标准填空：802.11b。",
            "高速 WPAN 标准：802.15.3。",
            "基础设施 WLAN 常见关键设备/地址：AP。",
            "802.11 使用 CSMA/CA + 停止等待。",
        ],
        "traps": [
            "无线局域网不是用 CSMA/CD，而是 CSMA/CA。",
            "AP 不是路由器的同义词，在 802.11 题里先按接入点理解。",
            "802.15 是 WPAN，不是 802.11 WLAN。",
        ],
    },
    "路由器、转发、网关与路由协议": {
        "layer": "网络层。重点是路由器如何按 IP/路由表转发分组，以及默认网关、VLAN 三层互通和路由协议。",
        "core": [
            "路由器工作在网络层，核心动作是根据目的 IP 地址和路由表选择下一跳/输出接口。",
            "转发是单个路由器按表把分组送出去；路由选择是路由器之间计算、维护路由表的过程。",
            "主机接入 Internet 常配置 IP 地址、子网掩码、默认网关 IP、DNS 服务器 IP。",
            "默认网关通常是本局域网出口路由器接口地址，主机访问外网时把分组交给它。",
            "网关在广义上可做协议转换；题库里“传输层及以上协议转换设备”标准答案是网关。",
            "不同 VLAN 间互通需要路由器或三层交换机，因为跨 VLAN 已经是三层转发问题。",
            "RIP 是距离向量，常用跳数作度量；OSPF 是链路状态，所有路由器最终形成链路状态数据库；BGP 用于自治系统间。",
            "OSI 模型中决定通过通信子网路径的是网络层。",
        ],
        "must": [
            "默认网关、路由器、网关、三层交换机、链路状态数据库这些标准词要原样记。",
            "OSPF：链路状态数据库；RIP：距离向量/跳数；BGP：自治系统间路径向量。",
            "VLAN 间通信：路由器或三层交换机。",
        ],
        "traps": [
            "交换机按 MAC 转发，路由器按 IP 转发，不要混层。",
            "默认网关不是 DNS 服务器；DNS 负责域名解析，网关负责出网转发。",
            "路由选择协议更新路由表，不是应用层用户协议。",
        ],
    },
    "IP 地址、子网划分、CIDR、VLSM 与 NAT": {
        "layer": "网络层地址规划。重点是 IPv4 地址、子网掩码、网络地址、广播地址、CIDR/VLSM/NAT 和 IPv6 过渡。",
        "core": [
            "IPv4 地址是 32 bit，点分十进制书写；IP 地址分网络号和主机号，子网掩码用来划分两部分。",
            "网络地址 = IP 地址与子网掩码逐位 AND；主机号全 0 表示网络地址，全 1 常表示该网络的广播地址。",
            "CIDR 使用斜线前缀长度表示网络，如 /24；路由查找常用最长前缀匹配。",
            "VLSM 允许不同子网使用不同长度掩码，提高地址利用率。",
            "NAT 在私有地址和公网地址之间转换，缓解 IPv4 地址不足，也隐藏内部地址结构。",
            "127.0.0.0/8 用于本机回环测试，常见地址 127.0.0.1。",
            "IPv6 过渡技术包括双协议栈和隧道技术。",
            "多归属主机是同时连接到两个或更多网络、具有两个或多个 IP 地址的主机。",
        ],
        "must": [
            "129.7.255.255 表示网络 129.7.0.0 上的所有主机。",
            "200.100.60.0 在题库语境中是网络地址。",
            "子网掩码可判断是否同一子网，并得到网络地址。",
            "循环测试 IP 网络：127.0.0.0。",
            "IPv6 过渡：双协议栈、隧道技术。",
        ],
        "traps": [
            "全 0 主机号是网络地址，全 1 主机号常是广播地址。",
            "CIDR 前缀越长，网络越小；路由匹配选最长前缀。",
            "NAT 不是路由协议，它是地址转换机制。",
        ],
    },
    "IP 数据报、ARP、ICMP、IGMP 与多播": {
        "layer": "网络层及其辅助协议。重点是 IP 数据报首部、ARP 地址解析、ICMP 差错/询问、IGMP 多播。",
        "core": [
            "IP 提供无连接、尽最大努力交付的数据报服务，不保证可靠、顺序或不重复。",
            "IPv4 数据报首部固定部分 20 字节，可变部分最多 40 字节；TTL/生存时间防止分组无限兜圈。",
            "ARP 在同一局域网内把目的 IP 地址解析成 MAC 地址；它服务于 IP 转发，但实际通过链路层广播请求。",
            "ICMP 报文分差错报告报文和询问报文；ping 使用回送请求和回送回答。",
            "IGMP 用于主机和本地路由器之间的 IP 多播组成员管理，IP 多播还需要多播路由选择协议。",
            "适配器接收发往本站的帧包括单播帧、广播帧、多播帧。",
            "存储转发实现方式可分数据报方式和虚电路方式。",
        ],
        "must": [
            "IP 首部固定部分：20 字节。",
            "TTL 中文标准：生存时间。",
            "ICMP 两类：差错报告、询问；ping：回送请求、回送回答。",
            "IP 多播需要 IGMP 和多播路由选择协议。",
            "ARP：IP 地址 -> MAC 地址。",
        ],
        "traps": [
            "ARP 不负责跨互联网找最终主机 MAC，只解析下一跳/同链路 IP 对应 MAC。",
            "ICMP 不是运输层协议，它围绕 IP 工作。",
            "TTL 不是按真实秒数精确计时，通常每过一跳减 1。",
        ],
    },
    "TCP 连接管理、可靠传输与流量控制": {
        "layer": "运输层 TCP。重点是连接、套接字、序号/确认号、可靠传输、滑动窗口和流量控制。",
        "core": [
            "TCP 面向连接、可靠、全双工，向应用层提供字节流服务，不保留应用报文边界。",
            "TCP 连接端点是套接字 socket，即 IP 地址 + 端口号；不是单纯一台主机。",
            "建立连接通常三次握手，释放连接通常四次挥手；握手用于同步初始序号并确认双方收发能力。",
            "TCP 序号按字节编号；确认号 n 表示期望收到的下一个字节序号，也意味着 n 之前字节已正确收到。",
            "可靠传输依靠序号、确认、超时重传、快速重传、校验和、滑动窗口等机制。",
            "流量控制看接收方接收能力，用接收窗口 rwnd 限制发送方，避免把接收缓存打爆。",
            "FTP 是应用层协议，但它的控制连接和数据连接都使用 TCP。",
        ],
        "must": [
            "TCP 首部“确认号”：期望收到对方下一个报文段首字节序号。",
            "TCP 连接端点：套接字 = IP 地址 + 端口号。",
            "流量控制保护接收方，不是解决全网拥塞。",
        ],
        "traps": [
            "TCP 是字节流，不是 UDP 那种保留报文边界。",
            "确认号不是“我已经收到的最后一个字节编号”，而是“下一个希望收到的编号”。",
            "流量控制和拥塞控制常被混淆：前者看接收方，后者看网络。",
        ],
    },
    "运输层服务、UDP、端口与套接字": {
        "layer": "运输层通用服务与 UDP。重点是进程到进程通信、端口复用分用，以及 UDP 的简单低开销。",
        "core": [
            "网络层提供主机到主机的逻辑通信，运输层提供应用进程到应用进程的端到端逻辑通信。",
            "端口号标识主机上的应用进程；一台主机常见三类地址标识：MAC 地址、IP 地址、端口号。",
            "运输层通过复用/分用把多个应用进程的数据交给网络层或从网络层分给正确进程。",
            "UDP 无连接、尽最大努力交付、面向报文，首部开销小，适合实时、简单请求响应或应用自己控制可靠性的场景。",
            "TCP/IP 运输层定义 TCP 和 UDP 两个主要传输协议。",
            "套接字常用于应用编程接口，也可作为 TCP 连接端点的标识。",
        ],
        "must": [
            "运输层服务对象：应用进程。",
            "主机三类地址：MAC 地址、IP 地址、端口号。",
            "TCP/IP 运输层协议：TCP、UDP。",
        ],
        "traps": [
            "端口号不是主机地址，它只在某台主机内标识进程。",
            "UDP 无连接不代表完全不能校验，UDP 首部有校验和字段。",
            "运输层不负责路由，路由是网络层任务。",
        ],
    },
    "TCP 拥塞控制": {
        "layer": "运输层 TCP 的网络保护机制。重点是拥塞窗口 cwnd 和四个经典算法。",
        "core": [
            "拥塞控制目标是保护网络，防止过多分组注入网络导致路由器队列溢出和吞吐下降。",
            "TCP 发送窗口受接收窗口 rwnd 和拥塞窗口 cwnd 共同限制；实际能发多少取二者较小值。",
            "慢开始并不是速度慢，而是 cwnd 从小开始按指数增长，探测网络可承受能力。",
            "拥塞避免通常按线性增长，出现拥塞后按乘法减小，体现 AIMD 思想。",
            "快重传根据重复确认尽早重传丢失报文段；快恢复避免一丢包就完全回到慢开始。",
            "RFC 2581 定义四种算法：慢开始、拥塞避免、快重传、快恢复。",
        ],
        "must": [
            "四算法：慢开始、拥塞避免、快重传、快恢复。",
            "流量控制看接收方 rwnd；拥塞控制看网络拥塞窗口 cwnd。",
        ],
        "traps": [
            "慢开始不是一直慢，而是起步小、指数增。",
            "丢包可能来自拥塞，不要只从接收方能力解释。",
            "拥塞控制属于 TCP 机制，但保护目标是整个网络。",
        ],
    },
    "DNS 域名系统": {
        "layer": "应用层。DNS 把人容易记的域名解析成 IP 地址，是层次化、分布式数据库系统。",
        "core": [
            "DNS 的核心作用是域名到 IP 地址解析，应用最终仍要拿 IP 地址交给网络层通信。",
            "DNS 采用层次化域名空间和分布式数据库，常见服务器包括根、顶级域、权限域名服务器和本地域名服务器。",
            "主机向本地域名服务器的查询一般采用递归查询；本地域名服务器对外常使用迭代查询。",
            "DNS 缓存能减少查询次数和时延，但缓存记录有 TTL。",
            "DNS 通常使用 UDP 53；区域传送或响应过大等场景可使用 TCP 53。",
            "常见资源记录：A 记录给 IPv4 地址，MX 指邮件服务器，CNAME 是别名，NS 指域名服务器。",
        ],
        "must": [
            "主机到本地域名服务器：递归查询。",
            "域名解析由许多域名服务器共同完成。",
            "DNS 常用 UDP 53，也可能用 TCP 53。",
        ],
        "traps": [
            "DNS 不是路由协议，它只解析名字到地址。",
            "本地 DNS 不等于根 DNS；根 DNS 不保存所有主机 IP。",
            "递归和迭代要看发起者和查询对象。",
        ],
    },
    "FTP 文件传输": {
        "layer": "应用层文件传输。重点是 FTP 使用两个并行 TCP 连接：控制连接和数据连接。",
        "core": [
            "FTP 是应用层协议，底层使用 TCP 提供可靠传输。",
            "FTP 客户和服务器之间建立两个连接：控制连接传命令和响应，数据连接传文件数据。",
            "控制连接在整个会话期间保持，数据连接可按传输任务建立和释放。",
            "传统主动模式中服务器数据端口常是 20，控制端口常是 21；被动模式由服务器开放临时端口供客户端连接。",
            "FTP 的控制信息和数据分离，属于带外控制思想。",
            "文件传输可靠性主要来自 TCP，不是 FTP 自己做链路层重传。",
        ],
        "must": [
            "FTP 两个 TCP 连接：控制连接、数据连接。",
            "常见端口：控制 21，主动模式数据 20。",
        ],
        "traps": [
            "FTP 不是只建立一条连接。",
            "FTP 是应用层协议，不是运输层协议；可靠传输依赖 TCP。",
            "控制连接传命令，不直接承载文件内容主体。",
        ],
    },
    "Web、HTTP、URL 与万维网": {
        "layer": "应用层 Web。重点是 URL、HTTP、浏览器/服务器交互，以及 Web 与 Internet 的区别。",
        "core": [
            "Web/WWW 是互联网之上的应用服务，不等同于互联网本身。",
            "URL 用来定位资源，常见结构包括协议、主机名、端口、路径等。",
            "HTTP 是应用层协议，通常基于 TCP；HTTPS 是 HTTP over TLS/SSL。",
            "HTTP 是无状态协议，每个请求本身不记住上一次请求；Cookie 等机制可在应用层维持状态。",
            "非持续连接每个对象可能单独建立 TCP 连接；持续连接可在同一 TCP 连接上传多个对象，减少 RTT 开销。",
            "访问网页常见过程：解析 URL，DNS 查 IP，建立 TCP 连接，发送 HTTP 请求，服务器返回响应。",
            "代理服务器/缓存可以减少访问时延和外部链路流量。",
        ],
        "must": [
            "HTTP：应用层、通常基于 TCP、无状态。",
            "URL：统一资源定位符。",
            "Web 不等于 Internet。",
        ],
        "traps": [
            "浏览器访问网页不是只靠 HTTP，还常先需要 DNS 和 TCP。",
            "无状态不是不能登录，而是协议本身不保存会话状态。",
            "持续连接减少重复建连 RTT，不代表只发一个对象。",
        ],
    },
    "DHCP、SNMP/MIB 与其他应用层协议": {
        "layer": "应用层辅助协议。重点是 DHCP 动态配置主机参数，SNMP/MIB 做网络管理。",
        "core": [
            "DHCP 是动态主机配置协议，用来自动分配 IP 地址、子网掩码、默认网关、DNS 等配置。",
            "DHCP 典型流程可记 DORA：Discover、Offer、Request、ACK。",
            "DHCP 通常基于 UDP，客户端初始还没有 IP 时会使用广播。",
            "SNMP 用于网络管理，管理站通过代理获取或设置被管设备信息。",
            "SNMP 网络管理体系常由 SNMP、SMI、MIB 组成；MIB 是管理信息库。",
        ],
        "must": [
            "DHCP = 动态主机配置协议。",
            "SNMP 组成：SNMP、SMI、MIB。",
            "MIB = 管理信息库。",
        ],
        "traps": [
            "DHCP 解决自动配置，不负责域名解析；域名解析是 DNS。",
            "SNMP 不是 SMTP，少一个字母含义完全不同。",
            "MIB 是管理信息库，不是某个邮件协议。",
        ],
    },
    "电子邮件：SMTP、POP3、IMAP 与 MIME": {
        "layer": "应用层电子邮件。重点是发送、接收、服务器存储和附件/非 ASCII 扩展。",
        "core": [
            "电子邮件系统通常包括用户代理、邮件服务器和邮件协议。",
            "SMTP 用于发送/转发邮件，采用推送方式，常基于 TCP 25。",
            "POP3 和 IMAP 用于用户从邮件服务器读取邮件；POP3 简单下载，IMAP 更适合服务器端管理和多设备同步。",
            "MIME 扩展电子邮件内容类型，使邮件能携带非 ASCII 文本、图片、音频、附件等。",
            "发信通常用 SMTP，收信通常用 POP3/IMAP；不要把 SMTP 当成用户收取邮件的协议。",
            "互联网中使用最多、最受欢迎的应用之一是电子邮件。",
        ],
        "must": [
            "SMTP：发送/推送邮件。",
            "POP3/IMAP：读取/接收邮件。",
            "MIME：支持多媒体附件和非 ASCII 内容。",
            "题库填空：电子邮件。",
        ],
        "traps": [
            "SMTP 不负责从邮箱服务器把邮件取到用户本地。",
            "POP3 和 IMAP 都是收信，但 IMAP 更强调服务器端管理。",
            "MIME 不是加密协议，它是邮件内容扩展。",
        ],
    },
    "密码学、报文鉴别、数字签名与不可否认": {
        "layer": "网络安全机制，可服务于多个层次。重点是安全目标、加密、报文鉴别和数字签名。",
        "core": [
            "安全目标常见：机密性、完整性、鉴别、不可否认、可用性。",
            "加密主要保护机密性；报文鉴别验证消息来源和内容没有被篡改。",
            "数字签名通常用发送方私钥签名，接收方用发送方公钥验证，从而实现报文鉴别、完整性、不可否认。",
            "公钥密码有一对密钥：公钥公开，私钥保密；RSA 是常见公钥密码算法。",
            "数字签名不等于“用接收方公钥加密”；签名关注证明是谁发的，保密关注谁能解密。",
            "哈希/摘要可辅助完整性检查，但单独哈希不能证明发送者身份。",
        ],
        "must": [
            "数字签名三功能：报文鉴别、报文完整性、不可否认。",
            "签名方向：发送方私钥签名，接收方用发送方公钥验证。",
            "RSA 是公钥密码算法。",
        ],
        "traps": [
            "加密和签名目的不同，方向也常不同。",
            "不可否认/不可抵赖意思接近，但题库标准词有时写“不可否认”。",
            "只保证机密性不等于保证完整性和身份。",
        ],
    },
    "防火墙、安全协议、VPN 与网络攻击": {
        "layer": "网络安全防护与攻击分类。重点是主动/被动攻击、防火墙类型、SSL/TLS/VPN 等机制。",
        "core": [
            "被动攻击主要是窃听、流量分析；主动攻击会修改、伪造、重放、拒绝服务或传播恶意程序。",
            "最常见主动攻击可包括篡改、恶意程序、拒绝服务等。",
            "防火墙位于内部网络和外部网络边界，用访问控制策略过滤或代理流量。",
            "防火墙常见类型：分组过滤路由器、代理服务器/应用网关。",
            "分组过滤主要看 IP、端口、协议、方向等首部字段；应用网关/代理能理解更高层应用语义。",
            "SSL/TLS 用于在传输层之上为应用提供安全通道；题库填空把 SSL 称作安全套接字层。",
            "VPN 通过隧道和加密在公网上构造逻辑专用网络。",
        ],
        "must": [
            "主动攻击标准词：拒绝服务。",
            "SSL 中文：安全套接字层；TLS：运输层安全。",
            "防火墙类型：分组过滤路由器、代理服务器/应用网关。",
        ],
        "traps": [
            "防火墙不是万能，不能阻止所有内部攻击或已授权流量中的恶意行为。",
            "分组过滤看低层首部，应用网关看应用层内容。",
            "SSL/TLS 保护通信通道，不等于自动保证业务逻辑安全。",
        ],
    },
}


EXTRA_SEED_POINTS = {
    "互联网发展、组成与通信方式": {
        "core": [
            "基础网络三类：电信网络、有线电视网络、计算机网络；按作用范围可分广域网、城域网、局域网、个人区域网。",
            "资源子网负责可共享资源，典型有主机、服务器、网络打印机；通信子网负责传输和转发，典型有路由器等通信设备。",
            "计算机内部常见并行传输，通信线路上更多是串行传输；题目问“线路上传输”不要套成并行。",
        ],
        "must": [
            "三大基础网络：电信网络、有线电视网络、计算机网络。",
            "作用范围：广域网、城域网、局域网、个人区域网。",
            "计算机内和线路上传输：并行、串行；题库还考数字传输。",
            "CCITT、6G 等缩写/代际词看到要能识别。",
        ],
        "traps": [
            "资源子网看“用资源”，通信子网看“把数据送过去”。",
            "问网络拓扑时再想总线型、星型、环型、树型，不要和按作用范围分类混。",
        ],
    },
    "交换技术与网络性能指标": {
        "core": [
            "bps = Bits per Second；baud/波特率表示每秒码元数。若每个码元携带 4 bit，2000 baud 对应 8000 bit/s。",
            "高速链路提高的是发送速率/数据率，不会改变电磁信号在介质中的传播速率。",
            "电路交换三阶段：建立连接、数据传输、释放连接；报文交换整报文存储转发；分组交换拆小包存储转发。",
            "信道利用率不是越高越好，利用率过高会导致排队时延急剧增大；全网利用率常看加权平均。",
        ],
        "must": [
            "bps = Bits per Second。",
            "2000 baud × 4 bit/码元 = 8000 bit/s。",
            "电路交换三阶段：建立连接、数据传输、释放连接。",
            "总时延：发送时延、传播时延、处理时延、排队时延。",
        ],
        "traps": [
            "发送速率是把比特推上链路，传播速率是信号在链路上跑，两者不是一回事。",
            "吞吐量是实际通过量，不等于链路标称带宽。",
        ],
    },
    "协议、标准与分层模型": {
        "core": [
            "网络层在数据链路层和运输层之间；OSI 最高层是应用层，TCP/IP 工业标准常分网络接口层、网际层、运输层、应用层。",
            "教学五层通常是物理层、数据链路层、网络层、运输层、应用层，不含会话层和表示层。",
            "ATM 中“异步”常指 ATM 信元可按需插入，不是简单理解成收发双方完全不协调。",
        ],
        "must": [
            "OSI：物理、数据链路、网络、运输、会话、表示、应用。",
            "TCP/IP：网络接口层、网际层、运输层、应用层。",
            "RFC、ATM、OSI/RM 这些缩写要能认。",
        ],
        "traps": [
            "OSI 和 TCP/IP 的层名不是一一同名，OSI 的网络层在 TCP/IP 常对应网际层。",
        ],
    },
    "数据通信基础、信号编码与调制": {
        "core": [
            "采样频率至少为模拟信号最高频率的 2 倍；4 kHz 语音至少 8 kHz 采样。",
            "量化级数需要二进制位数：ceil(log2 125)=7 位；PCM 数据率 = 采样率 × 每样本位数，例如 8k 样本/s × 4 bit = 32 Kbit/s。",
            "码元是承载信息的基本信号单位，波特率是每秒码元数；一个码元可以携带多个 bit。",
            "ASK 改振幅，FSK 改频率，PSK 改相位；A/F/P 分别对应 Amplitude/Frequency/Phase。",
        ],
        "must": [
            "采样：4 kHz -> 8 kHz；125 个量化级 -> 7 位；PCM 例题 -> 32 Kbps。",
            "ASK/FSK/PSK：振幅/频率/相位。",
            "信源、通信媒体、信宿；源系统、传输系统、目的系统。",
        ],
        "traps": [
            "bit 是信息量，baud 是信号变化次数；不能直接把二者当同一个单位。",
        ],
    },
    "多路复用与码分多址": {
        "core": [
            "STDM 是统计时分复用，按需动态分配时隙，利用率高，通常需要集中器；它不是固定时隙的普通 TDM。",
            "CDMA 同频通信，靠正交码片/扩频区分用户；接收端用相关运算还原目标站信号。",
            "ADSL 复用电话线，采用频分复用，下行速率通常高于上行，不适合以上行为主的大流量业务。",
            "复用提高线路利用率和总传输能力，但不会直接降低误码率。",
        ],
        "must": [
            "STDM = 统计时分复用。",
            "CDMA：同频、正交码片、扩频。",
            "ADSL：非对称，下行高于上行，频分复用。",
        ],
        "traps": [
            "FDM 是不同频带同时传，TDM 是不同时间片轮流传，STDM 是按需求动态分时隙。",
        ],
    },
    "传输媒体：双绞线、同轴、光纤与无线": {
        "core": [
            "STP 是屏蔽双绞线，UTP 是非屏蔽双绞线；双绞线绞合能降低干扰，成本低但距离有限。",
            "同轴电缆抗干扰能力通常强于双绞线；FTTx 常见 FTTH、FTTB、FTTC，不包含 HFC。",
            "远距离光纤通信常用单模光纤，近距离可用多模光纤；题干反说时要判错。",
            "局域网特性主要由网络拓扑和传输媒体决定。",
        ],
        "must": [
            "STP = 屏蔽双绞线；UTP = 非屏蔽双绞线。",
            "FTTx：FTTH、FTTB、FTTC；HFC 不属于 FTTx。",
            "远距离：单模光纤；近距离：多模光纤。",
        ],
        "traps": [
            "光纤是有线导引介质，不是无线媒体。",
        ],
    },
    "物理层接口、传输系统与标准": {
        "core": [
            "题库口径中，物理层互连常要求数据传输率和链路协议一致；中继器处于物理层。",
            "完整数据通信系统是源系统、传输系统、目的系统，不包括认证系统。",
        ],
        "must": [
            "中继器：物理层。",
            "数据通信系统：源系统、传输系统、目的系统。",
        ],
        "traps": [
            "认证系统属于安全/应用相关语境，不是基础数据通信模型的组成部分。",
        ],
    },
    "成帧、透明传输、差错检测与 ARQ": {
        "core": [
            "数据链路层处理的数据单位是帧；三大基本问题是封装成帧、透明传输、差错检测。",
            "停止等待 ARQ 不是累计确认；奇偶校验只能检出奇数个比特错误。",
        ],
        "must": [
            "帧、封装成帧、透明传输、差错检测、CRC、ARQ。",
        ],
        "traps": [
            "拥塞控制不是数据链路层基本功能，它属于 TCP/网络整体控制语境。",
            "检错不等于纠错，可靠传输还要确认、超时、重传。",
        ],
    },
    "PPP、HDLC 与点到点链路": {
        "core": [
            "PPP 组成：封装方法、LCP、NCP；核心特点是点到点、简单、不纠错、可承载多种网络层协议。",
            "题库口径里 PPP 既不是只支持单工/半双工，也不能简单说“只支持双工链路”；做判断题要回到具体表述。",
        ],
        "must": [
            "PPP 组成：封装方法、LCP、NCP。",
            "PPP 与 P2P 是两个概念：PPP 是链路层协议，P2P 是端系统通信方式。",
        ],
        "traps": [
            "PPP 不提供纠错可靠传输，不能把它套成 TCP。",
        ],
    },
    "以太网、MAC 地址、CSMA/CD 与交换": {
        "core": [
            "MAC 地址通常 48 位、全球唯一、固化或配置在网卡中；广播 MAC 是 FF-FF-FF-FF-FF-FF。",
            "传统以太网常用曼彻斯特编码；CSMA/CD 争用期是最远两端往返传播时延，传统以太网争用期常背 51.2μs。",
            "最小帧长计算：最小帧长 = 争用期 × 数据率；题中 10km / 200m/μs = 50μs，往返 100μs，10Mb/s = 10bit/μs，所以最小 1000bit。",
            "集线器工作在物理层，扩大冲突域、共享带宽、广播转发；交换机/网桥工作在数据链路层，每端口一个冲突域。",
            "交换机自学习看源 MAC + 入端口，转发时查目的 MAC；空表未知单播会泛洪。",
            "STP 用来防二层环路；VLAN 缩小广播域，但不同 VLAN 不能靠二层直接通信。",
        ],
        "must": [
            "MAC 地址：48 位；广播 MAC：FF-FF-FF-FF-FF-FF。",
            "争用期：51.2μs；例题最小帧长：1000bit。",
            "交换机自学习：源 MAC + 入端口；转发查目的 MAC。",
            "STP 防二层环路；VLAN 缩小广播域。",
        ],
        "traps": [
            "集线器是一层设备，交换机/网桥是二层设备，路由器是三层设备。",
            "交换机默认同一广播域；划分 VLAN 后才隔离广播域。",
        ],
    },
    "无线局域网、WPAN 与 802.11/802.15": {
        "core": [
            "隐藏站是“以为空闲，其实会撞”；暴露站是“以为忙，其实可以发”。",
            "ad hoc 网络没有固定基础设施；有固定基础设施的 WLAN 通过 AP 连接。",
            "MIPv4 要区分永久 IP 地址和转交地址，移动站在外地网络通信不能简单只用原 IP。",
        ],
        "must": [
            "802.15.1 = 蓝牙；802.15.4 = ZigBee；802.15.3 = 高速 PAN。",
            "CA = Collision Avoidance；CD = Collision Detection。",
        ],
        "traps": [
            "无线环境不能可靠边发送边检测冲突，所以不用 CSMA/CD。",
        ],
    },
    "IP 数据报、ARP、ICMP、IGMP 与多播": {
        "core": [
            "IPv4 分片因超过 MTU；标识字段用于把分片归组，片偏移单位是 8 字节，MF 标志只能是 1/0。",
            "IP 首部校验和只校验首部，不校验数据部分，也不是 CRC。",
            "tracert 常利用 TTL 逐跳到期产生 ICMP 时间超过报文，也可能遇到终点不可达。",
        ],
        "must": [
            "片偏移单位：8 字节；MF：1 表示后面还有分片，0 表示最后一片。",
            "IP 首部校验和：只校验首部，不采用 CRC。",
            "tracert：ICMP 时间超过。",
        ],
        "traps": [
            "跨网 ARP 解析的是下一跳/默认网关的 MAC，不是远端目标主机的 MAC。",
        ],
    },
    "IP 地址、子网划分、CIDR、VLSM 与 NAT": {
        "core": [
            "C 类地址特征：前 3 位 110，默认网络号 24 位、主机号 8 位，默认掩码 255.255.255.0。",
            "IPv6 地址 128 位，使用扩展首部、即插即用、无首部检验和；地址类型有单播、多播、任播，没有广播。",
            "掩码 1 表示网络位，0 表示主机位；网络地址 = IP 与掩码相与，主机号 = IP 与反掩码相与。",
            "主机换网络通常要改 IP 地址，不改 MAC 地址；网卡接收时先检查目的 MAC。",
        ],
        "must": [
            "255.255.255.224 块大小 32。",
            "10.130.12.29 同网可用到 10.130.12.30。",
            "IPv6：128 位；单播、多播、任播；没有广播。",
            "C 类默认掩码：255.255.255.0。",
            "255.255.255.255 是受限广播。",
        ],
        "traps": [
            "根本解决 IPv4 地址耗尽靠 IPv6，NAT 只是缓解。",
            "VLSM 是可变长子网掩码，不是合并标准网络。",
        ],
    },
    "路由器、转发、网关与路由协议": {
        "core": [
            "路由表通常含目的网络和下一跳 IP/输出接口，不保存完整路径，也不是保存下一跳 MAC。",
            "跨网转发时源/目的 IP 地址一般保持不变，链路层源/目的 MAC 每一跳都会改变。",
            "默认路由是没有更具体匹配时的兜底，前缀 /0 优先级最低；路由查找遵循最长前缀匹配。",
            "RIP 是距离向量，和相邻路由器交换完整路由表，最大 15 跳；OSPF 是链路状态，洪泛链路状态并划分区域，收敛较快。",
            "BGP 是自治系统之间的外部网关协议；RIP/OSPF 是自治系统内部的 IGP。",
        ],
        "must": [
            "最长前缀匹配；默认路由 /0。",
            "RIP 最大 15 跳。",
            "BGP = 外部网关协议；RIP/OSPF = IGP。",
        ],
        "traps": [
            "三层交换机按三层信息实现 VLAN 间转发，不是靠二层 MAC 表直接让 VLAN 互通。",
        ],
    },
    "TCP 连接管理、可靠传输与流量控制": {
        "core": [
            "TCP 首部最小 20 字节；三次握手常见标志位 SYN、SYN+ACK、ACK。",
            "确认号公式：ACK = 起始序号 + 已正确收到的字节数。例如起始 200，收到 300+500 字节，下一个期望字节为 1000。",
            "TCP 会把应用数据分段并加首部，可靠性来自 TCP 机制；FTP 的 20/21 端口不要误当成所有 TCP 连接的端口规律。",
        ],
        "must": [
            "TCP 首部最小：20 字节。",
            "ACK = seq + 已收到字节数；例题确认号：1000。",
            "SYN、SYN+ACK、ACK。",
            "题库还出现 60% 这类窗口/效率计算结果，遇到数字题要回到公式。",
        ],
        "traps": [
            "确认号不包含自己，它指向下一个希望收到的字节。",
        ],
    },
    "运输层服务、UDP、端口与套接字": {
        "core": [
            "端口号是 16 位；熟知端口常见范围 1～1023。连接由源 IP、源端口、目的 IP、目的端口等组合区分，所以同一端口号可出现在不同连接中。",
            "UDP 长度字段包括 UDP 首部和数据部分，长度单位按 8 位/字节理解。",
            "按信息交互方向可分单工、半双工、全双工；全双工是两个方向可同时传输。",
            "Ping 直接封装 ICMP 报文；ICMP 可报告网络不可达，它不是 TCP/UDP。",
        ],
        "must": [
            "端口号：16 位；熟知端口：1～1023。",
            "UDP = User Datagram Protocol。",
            "单工、半双工、全双工。",
            "Ping/网络不可达：ICMP，不是 TCP/UDP。",
        ],
        "traps": [
            "UDP 能校验不等于可靠交付；能发现坏了不代表能修好。",
        ],
    },
    "TCP 拥塞控制": {
        "core": [
            "拥塞发生的判断题常看：通信子网负载增加而吞吐量反而降低。",
            "TCP 超时后拥塞窗口可降为 1 个 MSS；题中 MSS=2KB 时窗口变 2KB。",
        ],
        "must": [
            "超时后拥塞窗口例题：2KB。",
            "拥塞控制是全局性的过程。",
        ],
        "traps": [
            "流量控制怕接收方撑爆，拥塞控制怕全网堵车。",
        ],
    },
    "DNS 域名系统": {
        "core": [
            "DNS 是基于 C/S 的分布式系统；组成包括域名空间、分布式数据库、域名服务器，不包括内外网地址翻译程序。",
            "权限域名服务器能把自己管辖的主机名转换成 IP 地址。",
            "递归查询中，给客户端返回最终结果的是客户端最开始连接的本地域名服务器。",
            "域名和 IP 不一定一一对应：多个域名可指向同一 IP，同一域名也可能解析到多个 IP。",
            "迭代查询次数题要看缓存；题库出现最少/最多 0，4。",
        ],
        "must": [
            "DNS 查询次数例题：0，4。",
            "DNS 组成：域名空间、分布式数据库、域名服务器。",
            "DNS 不是 NAT，不负责内外网地址翻译。",
        ],
        "traps": [
            "递归像代办到底，迭代像给下一步线索。",
        ],
    },
    "FTP 文件传输": {
        "core": [
            "FTP 控制连接先建立、晚于数据连接释放；数据连接每次传输完数据后关闭。",
            "LIST 文件列表通过数据连接传输，不是在控制连接里直接传完整列表内容。",
        ],
        "must": [
            "控制连接先来后走，数据连接后建先关。",
            "LIST 走数据连接。",
        ],
        "traps": [
            "FTP 由于双连接机制，并不属于“小且容易实现”的简单协议。",
        ],
    },
    "电子邮件：SMTP、POP3、IMAP 与 MIME": {
        "core": [
            "邮件地址格式：用户名@邮箱所在主机的域名。",
            "原始 SMTP 直接支持 7 比特 ASCII；JPEG/MPEG/EXE 等非 ASCII 或多媒体内容需要 MIME 扩展。",
            "邮件由首部和主体组成，Subject 是主题字段，不是邮件主机。",
            "图示三阶段常考：SMTP、SMTP、POP3。",
        ],
        "must": [
            "用户名@邮箱所在主机的域名。",
            "SMTP、SMTP、POP3。",
            "ASCII、JPEG、MPEG、EXE、MIME。",
        ],
        "traps": [
            "Subject 是邮件主题，不是服务器地址。",
        ],
    },
    "Web、HTTP、URL 与万维网": {
        "core": [
            "WWW 使用 HTML 显示 Web Page，HTML5 是常见标准；Web 客户端通常是浏览器，Web 服务器也叫 WWW 服务器。",
            "HTTP 默认端口是 TCP 80；HTTP/1.0 访问 1 个文本页 + 3 幅图像常需 0 个 UDP、4 个 TCP 连接。",
            "HTTP/1.1 持续非流水线访问 1 个 HTML + 3 个 JPEG，共 4 个对象；题设一次请求-响应为 RTT 时答案是 4 RTT。",
            "Connection: keep-alive 表示持续连接，不是非持续连接。",
            "Cookie 由服务器产生、存储在客户端，可跟踪状态，也带来隐私风险。",
            "访问 Web 可能涉及 TCP、ARP、PPP，不使用 SMTP。",
            "Web 服务器存储/提供 HTML 文档，不一定负责创建和编辑网页。",
        ],
        "must": [
            "HTTP 默认端口：TCP 80。",
            "HTTP/1.0 图文对象连接题：0 个 UDP、4 个 TCP。",
            "HTTP/1.1 非流水线例题：4 RTT。",
            "RTT 例题答案：20ms，50ms。",
            "Cookie 存储在客户端；Connection: keep-alive = 持续连接。",
        ],
        "traps": [
            "先数对象，再看连接方式，再看是否流水线。",
        ],
    },
    "DHCP、SNMP/MIB 与其他应用层协议": {
        "core": [
            "DHCP Discover 时客户端还没有 IP，源 IP 用 0.0.0.0；不知道服务器位置，目的 IP 用受限广播 255.255.255.255。",
            "127.0.0.1 是本机回环，不能用于发现 DHCP 服务器。",
        ],
        "must": [
            "DHCP Discover：源 IP 0.0.0.0，目的 IP 255.255.255.255。",
        ],
        "traps": [
            "还没地址就写 0，全网喊话就广播 255。",
        ],
    },
    "密码学、报文鉴别、数字签名与不可否认": {
        "core": [
            "数字签名时发送方 A 用 A 的私钥签名，接收方用 A 的公钥验证；公钥不是用来生成签名的。",
        ],
        "must": [
            "私钥签名，公钥验证。",
            "不可抵赖/不可否认在题库中要能互认，填空按标准答案写。",
        ],
        "traps": [
            "保密加密常用对方公钥，数字签名用自己私钥，方向不能反。",
        ],
    },
    "防火墙、安全协议、VPN 与网络攻击": {
        "core": [
            "主动攻击包括篡改、恶意程序、拒绝服务；被动攻击主要是窃听和流量分析。",
            "分组过滤看分组头部字段和规则，代理服务器/应用网关在更高层代理并检查通信。",
        ],
        "must": [
            "SSL = 安全套接字层；TLS = 运输层安全。",
        ],
        "traps": [
            "防火墙分类题别只写“路由器”，要写完整术语“分组过滤路由器”。",
        ],
    },
}


def merge_extra_seed_points() -> None:
    for knowledge, extra in EXTRA_SEED_POINTS.items():
        if knowledge not in SEEDS:
            raise KeyError(f"Extra seed targets unknown knowledge: {knowledge}")
        seed = SEEDS[knowledge]
        for key in ("core", "must", "traps"):
            seed.setdefault(key, [])
            for value in extra.get(key, []):
                if value not in seed[key]:
                    seed[key].append(value)


def line_value(text: str | None, prefix: str) -> str:
    if not text:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def one_line(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\r", " ").replace("\n", " ")).strip()


def truncate(text: str, size: int) -> str:
    text = one_line(text)
    return text if len(text) <= size else text[:size] + "..."


def answer_display(q: dict) -> str:
    answer = q.get("answer")
    if q.get("type") == "blank":
        values = answer if isinstance(answer, list) else [answer]
        return "；".join(str(x) for x in values)
    if q.get("type") == "tf":
        return "T（正确）" if answer == "TRUE" else "F（错误）"
    answer_str = str(answer)
    texts = []
    for opt in q.get("options") or []:
        if opt["key"] in answer_str:
            texts.append(opt["text"])
    return answer_str + (f"（{'；'.join(texts)}）" if texts else "")


def type_distribution(items: list[dict]) -> str:
    counts = collections.Counter(q["typeName"] for q in items)
    return "，".join(f"{k} {v}" for k, v in counts.items())


def collect_eyes(items: list[dict], max_count: int = 14) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for q in items:
        value = line_value(q.get("quickExplanation"), "题眼：")
        if not value:
            value = truncate(q.get("stem", ""), 44)
        value = truncate(value, 64)
        if value and value not in seen:
            seen.add(value)
            values.append(value)
        if len(values) >= max_count:
            break
    return values


def derived_rules(items: list[dict], max_count: int = 8) -> list[str]:
    prefixes = ["底层模型：", "底层抓手：", "底层原理：", "相邻概念区别：", "为什么这样判题："]
    values: list[str] = []
    seen: set[str] = set()
    for q in items:
        for source in [q.get("knowledgeDetail"), q.get("quickExplanation"), q.get("explanation")]:
            for prefix in prefixes:
                value = truncate(line_value(source, prefix), 150)
                if value and value not in seen:
                    seen.add(value)
                    values.append(value)
                    if len(values) >= max_count:
                        return values
    return values


def derived_traps(items: list[dict], max_count: int = 10) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for q in items:
        for prefix in ["易错：", "本题陷阱：", "排除/易混：", "别踩坑：", "别写成："]:
            value = truncate(line_value(q.get("quickExplanation"), prefix), 120)
            if not value:
                value = truncate(line_value(q.get("knowledgeDetail"), prefix), 120)
            if value and value not in seen:
                seen.add(value)
                values.append(value)
                if len(values) >= max_count:
                    return values
    return values


def must_from_questions(items: list[dict]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    important = re.compile(
        r"(\d|[A-Z]{2,}|802\.|CSMA|MAC|IP|TCP|UDP|HTTP|DNS|FTP|SMTP|POP3|IMAP|"
        r"ARP|ICMP|IGMP|PPP|HDLC|CIDR|VLSM|NAT|RSA|SSL|TLS|MIB|SNMP|DHCP|SONET|SDH)"
    )
    for q in items:
        ans = answer_display(q)
        eye = line_value(q.get("quickExplanation"), "题眼：") or truncate(q.get("stem", ""), 42)
        if q.get("type") == "blank":
            value = f"{q['label']} 标准答案：{ans}；题眼：{truncate(eye, 46)}"
        elif important.search(ans):
            value = f"{q['label']} 答案要认准：{truncate(ans, 80)}"
        else:
            continue
        if value not in seen:
            seen.add(value)
            values.append(value)
    return values


def question_tip(q: dict) -> str:
    eye = line_value(q.get("quickExplanation"), "题眼：") or truncate(q.get("stem", ""), 48)
    reason = (
        line_value(q.get("quickExplanation"), "理由：")
        or line_value(q.get("quickExplanation"), "本题理由：")
        or line_value(q.get("quickExplanation"), "做题理由：")
        or line_value(q.get("quickExplanation"), "为什么选它：")
        or line_value(q.get("quickExplanation"), "为什么：")
        or line_value(q.get("quickExplanation"), "标准填法：")
        or line_value(q.get("quickExplanation"), "判断：")
        or line_value(q.get("quickExplanation"), "答案：")
    )
    return (
        f"{q['label']}：题眼「{truncate(eye, 44)}」；"
        f"答案 {truncate(answer_display(q), 70)}；"
        f"{truncate(reason, 110)}"
    )


def chapter_map(chapter: str) -> str:
    if chapter.startswith("1."):
        return "本章是全局地图：互联网由什么组成、数据怎样交换、协议怎样分层。做题先问：它是在讲网络整体、性能指标，还是分层规则？"
    if chapter.startswith("2."):
        return "本章站在物理层：只关心比特怎样变成信号、通过什么介质传、多个用户怎样共享信道。"
    if chapter.startswith("3."):
        return "本章站在数据链路层：把比特组织成帧，用 MAC 地址在同一链路/局域网内传送，并处理局域网接入。"
    if chapter.startswith("4."):
        return "本章站在网络层：用 IP 地址、路由表和路由协议，把分组从源主机送到目的主机。"
    if chapter.startswith("5."):
        return "本章站在运输层：用端口把主机通信交给应用进程；TCP 管可靠与控制，UDP 管简单快速。"
    if chapter.startswith("6."):
        return "本章站在应用层：DNS、FTP、HTTP、DHCP、SNMP、电子邮件直接服务具体网络应用。"
    if chapter.startswith("7."):
        return "本章站在安全视角：加密、鉴别、签名、防火墙、SSL/TLS、VPN 会跨层保护通信。"
    return "先判断题干在问哪一层、哪个对象、哪条机制。"


def build_cards() -> tuple[list[dict], str]:
    merge_extra_seed_points()
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    groups: "collections.OrderedDict[tuple[str, str], list[dict]]" = collections.OrderedDict()
    for q in questions:
        groups.setdefault((q["chapter"], q["knowledge"]), []).append(q)

    cards: list[dict] = []
    covered: list[str] = []
    for (chapter, knowledge), items in groups.items():
        seed = SEEDS.get(knowledge)
        if seed is None:
            raise KeyError(f"Missing card seed for knowledge: {knowledge}")
        labels = [q["label"] for q in items]
        covered.extend(labels)
        core = list(seed["core"])
        for value in derived_rules(items):
            if value not in core:
                core.append(value)
        must = list(seed["must"])
        for value in must_from_questions(items):
            if value not in must:
                must.append(value)
        traps = list(seed["traps"])
        for value in derived_traps(items):
            if value not in traps:
                traps.append(value)
        cards.append(
            {
                "chapter": chapter,
                "chapterMap": chapter_map(chapter),
                "knowledge": knowledge,
                "questionCount": len(items),
                "typeDistribution": type_distribution(items),
                "labels": labels,
                "layerHint": seed["layer"],
                "eyeLines": collect_eyes(items),
                "selfChecks": [
                    "先说它属于哪一层/哪类机制，避免把应用、运输、网络、链路、物理层混在一起。",
                    "再说它解决什么问题：寻址、转发、可靠性、媒体接入、信号传输，还是具体应用服务。",
                    "最后用本卡“逐题覆盖线索”回查每一道题，确认标准词、数字和易混点都能说出来。",
                ],
                "corePoints": core,
                "mustRemember": must,
                "traps": traps,
                "questionTips": [question_tip(q) for q in items],
            }
        )

    if len(questions) != 372:
        raise AssertionError(f"Expected 372 questions, got {len(questions)}")
    if len(covered) != 372 or len(set(covered)) != 372:
        duplicates = [k for k, v in collections.Counter(covered).items() if v > 1]
        missing = sorted(set(q["label"] for q in questions) - set(covered))
        raise AssertionError(f"Coverage mismatch: covered={len(covered)} unique={len(set(covered))} dup={duplicates} missing={missing}")

    question_order = {q["label"]: q["id"] for q in questions}

    def chapter_number(card: dict) -> int:
        match = re.match(r"(\d+)\.", card["chapter"])
        return int(match.group(1)) if match else 999

    cards.sort(key=lambda card: (chapter_number(card), min(question_order[label] for label in card["labels"])))

    by_chapter = collections.OrderedDict()
    for card in cards:
        by_chapter.setdefault(card["chapter"], []).append(card)

    report = []
    report.append("# v2.7.0 章节知识卡片覆盖报告\n")
    report.append(f"- 生成时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"- 题库文件：`{QUESTIONS_PATH}`")
    report.append(f"- 输出文件：`{CARDS_PATH}`")
    report.append("- 校验结论：通过，372/372 题全部进入知识卡片逐题覆盖线索。\n")
    report.append("## 章节覆盖\n")
    report.append("| 章节 | 题数 | 卡片数 | 题型分布 |")
    report.append("|---|---:|---:|---|")
    for chapter, chapter_cards in by_chapter.items():
        labels = [label for c in chapter_cards for label in c["labels"]]
        chapter_questions = [q for q in questions if q["chapter"] == chapter]
        report.append(
            f"| {chapter} | {len(labels)} | {len(chapter_cards)} | {type_distribution(chapter_questions)} |"
        )
    report.append("\n## 知识点卡片覆盖\n")
    report.append("| 知识点 | 题数 | 题号 |")
    report.append("|---|---:|---|")
    for card in cards:
        report.append(
            f"| {card['chapter']} / {card['knowledge']} | {card['questionCount']} | "
            f"{'、'.join(card['labels'])} |"
        )
    report.append("")
    return cards, "\n".join(report)


def main() -> None:
    cards, report = build_cards()
    CARDS_PATH.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"wrote {CARDS_PATH}")
    print(f"wrote {REPORT_PATH}")
    print(f"cards={len(cards)} questions={sum(c['questionCount'] for c in cards)}")


if __name__ == "__main__":
    main()
