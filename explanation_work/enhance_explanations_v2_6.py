import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "app" / "src" / "main" / "assets" / "questions.json"
BACKUP = ROOT / "explanation_work" / "questions.before_v2_6_personalized.json"
REPORT = ROOT / "explanation_work" / "v2_6_personalized_report.md"

METADATA_FIXES = {
    "103": ("1. 网络基础与体系结构", "互联网发展、组成与通信方式"),
    "150": ("3. 数据链路层与局域网", "成帧、透明传输、差错检测与 ARQ"),
    "215": ("6. 应用层", "Web、HTTP、URL 与万维网"),
}


def clean_space(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def strip_numbering(text):
    text = clean_space(text)
    text = re.sub(r"^\d+[.．、]\s*", "", text)
    text = re.sub(r"^第?\d+\s*[题題][.．、]?\s*", "", text)
    return text


def line_value(text, label):
    if not text:
        return ""
    for raw in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if line.startswith(label):
            return line[len(label):].strip()
    return ""


def sentence_trim(text, max_len=96):
    text = clean_space(text)
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    for sep in "；。;，,":
        pos = cut.rfind(sep)
        if pos >= max_len * 0.55:
            return cut[: pos + 1].strip()
    return cut.rstrip() + "…"


def option_map(q):
    result = {}
    for opt in q.get("options", []) or []:
        key = str(opt.get("key", "")).strip()
        text = str(opt.get("text", "")).strip()
        text = re.sub(r"^[A-Z]\.\s*", "", text)
        text = text.replace("T. ", "").replace("F. ", "")
        if key:
            result[key] = text
    return result


def answer_keys(q):
    ans = q.get("answer")
    if isinstance(ans, list):
        return [str(x) for x in ans]
    ans = str(ans)
    if q.get("type") == "multi":
        return [c for c in ans if "A" <= c <= "Z"]
    return [ans]


def answer_text(q):
    amap = option_map(q)
    keys = answer_keys(q)
    if q.get("type") == "blank":
        ans = q.get("answer")
        return "；".join(str(x) for x in ans) if isinstance(ans, list) else str(ans)
    if q.get("type") == "tf":
        return "正确" if keys and keys[0] == "TRUE" else "错误"
    parts = []
    for key in keys:
        if key in amap:
            parts.append(f"{key}. {amap[key]}")
        else:
            parts.append(key)
    return "；".join(parts)


def apply_metadata_fix(q):
    fixed = METADATA_FIXES.get(str(q.get("id")))
    if fixed:
        q["chapter"], q["knowledge"] = fixed


def label_of(q):
    return str(q.get("label") or q.get("id"))


def eye_of(q):
    quick = q.get("quickExplanation", "")
    eye = line_value(quick, "题眼：")
    if eye:
        return sentence_trim(eye, 70)
    stem = strip_numbering(q.get("stem", ""))
    quoted = re.findall(r"[“\"']([^”\"']{2,24})[”\"']", stem)
    if quoted:
        return sentence_trim("、".join(quoted[:2]), 70)
    return sentence_trim(stem, 70)


def reason_of(q):
    quick = q.get("quickExplanation", "")
    for label in ("理由：", "底层理由：", "做题理由：", "判题理由："):
        value = line_value(quick, label)
        if value:
            return value
    return sentence_trim(q.get("explanation") or q.get("knowledgeDetail") or "", 140)


def trap_of(q):
    quick = q.get("quickExplanation", "")
    for label in ("易错：", "陷阱：", "本题陷阱："):
        value = line_value(quick, label)
        if value:
            return value
    return "不要只记答案，要先看题干问的是层次、字段、机制、单位还是反向选择。"


def is_negative(q):
    stem = clean_space(q.get("stem", ""))
    negative_patterns = [
        "错误的是", "错误的有", "描述错误", "说法错误", "叙述错误",
        "不正确的是", "不正确的有", "不属于", "不可能使用到",
        "不能用于", "不能作为", "不能提供", "不是", "无法实现", "无关的是",
    ]
    return any(x in stem for x in negative_patterns)


def option_reason_map(reason):
    result = {}
    if not reason:
        return result
    text = reason.replace("；", ";")
    for key in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        m = re.search(
            rf"(?:^|[;。])\s*({key}[^\n;。]*?(?:应选|不选|正确|错误|不属于|不是|不能|不可能)[^\n;。]*)",
            text,
        )
        if m:
            result[key] = m.group(1).strip()
    return result


def topic_profile(q):
    stem = q.get("stem", "")
    opts = " ".join(o.get("text", "") for o in q.get("options", []) or [])
    primary_text = stem + " " + q.get("knowledge", "")
    text = primary_text + " " + opts
    knowledge = q.get("knowledge", "")

    def has(*words):
        return any(w in text for w in words)

    def has_primary(*words):
        return any(w in primary_text for w in words)

    # More specific protocol/mechanism profiles must come before broad words like TCP/IP,
    # 利用率, 协议 or Web, otherwise option text can pull a question into the wrong model.
    if has_primary("复用", "TDM", "FDM", "WDM", "CDM", "CDMA", "码片", "统计时分", "STDM", "集中器"):
        return {
            "model": "复用的本质是多路信号共享同一条物理链路。FDM 按频带分，TDM 按固定时间片分，STDM 按需分配时间片，WDM 按光的波长分，CDM/CDMA 用不同码片序列区分用户。",
            "check": "先看题干说的是频率、时间、波长还是码片；“统计”通常意味着按需而不是固定。",
            "boundary": "TDM 的固定时隙可能空转，STDM 利用率更高但需要集中器/地址等控制信息；CDMA 不是靠频率或时隙直接区分。"
        }
    if has_primary("路由器", "网关", "转发表", "路由表", "默认路由", "最长前缀", "RIP", "OSPF", "BGP", "距离向量", "链路状态", "自治系统", "CIDR 聚合") and not has_primary("防火墙", "安全协议", "攻击"):
        return {
            "model": "路由题要分清“算路”和“转发”。路由协议负责生成/维护路由表，转发时路由器按目的 IP 查转发表，通常用最长前缀匹配；RIP 是距离向量，适合小规模，OSPF 是链路状态，属于内部网关协议，BGP 用于自治系统之间。",
            "check": "先判断题干问路由协议类型、路由器转发动作、默认路由/最长匹配，还是网关概念。",
            "boundary": "交换机按 MAC 转发帧，路由器按 IP 转发分组；RIP/OSPF 是 IGP，BGP 是 EGP；网关常指通向其他网络的出口设备。"
        }
    if has_primary("DNS", "域名", "递归", "迭代", "本地域名", "根域名", "顶级域名", "权威域名", "UDP 53"):
        return {
            "model": "DNS 把域名解析成 IP 地址，层次结构从根域、顶级域到权威域。主机通常递归请求本地 DNS，本地 DNS 再迭代询问外部 DNS；普通查询常用 UDP 53，区域传送等场景可用 TCP。",
            "check": "先看题干问解析对象、查询过程、服务器层次，还是运输层协议。",
            "boundary": "DNS 不是 HTTP；ARP 是 IP 找 MAC，DNS 是域名找 IP；递归和迭代的发问者不同。"
        }
    if has_primary("ARPANET", "互联网", "Internet", "C/S", "P2P", "B/S", "基础网络", "ADSL", "HFC") and not has_primary("Web", "HTTP", "URL", "浏览器", "WWW", "万维网"):
        return {
            "model": "先把概念放到正确层次：ARPANET 是早期分组交换网络，Internet 是全球互联网络，Web/WWW 是跑在 Internet 上的应用。互联网工作上常分边缘部分和核心部分；端系统通信常说 C/S 与 P2P，B/S 只是 C/S 的一种具体形式。接入技术如 ADSL、HFC 是用户接入互联网的方法，不等于互联网本身。",
            "check": "先问：题干在考历史顺序、组成部分、通信方式，还是接入方式；不要看见“能通信”就混成同一类。",
            "boundary": "Internet 不等于 Web；P2P 是应用通信模式，PPP 是链路层点到点协议；接入网/基础网络/互联网组成三者不要混写。"
        }
    if has_primary("DHCP", "SNMP", "MIB", "租用", "管理站", "网络管理"):
        return {
            "model": "DHCP 用来让主机自动获得 IP 地址、掩码、网关、DNS 等配置；新主机 Discover 时还没有地址，所以常用源 0.0.0.0、目的 255.255.255.255 广播找服务器。SNMP 用于网络管理，管理站通过代理读取或修改 MIB 中的管理对象。",
            "check": "先判断题干是在自动配置地址，还是在做网络设备管理；DHCP 初始发现阶段尤其要看源/目的地址。",
            "boundary": "DHCP 不是域名解析，DNS 才解析域名；127.0.0.1 是本机环回，不用于发现 DHCP 服务器；SNMP/MIB 是管理体系，不负责普通数据转发。"
        }
    if has_primary("HTTP", "Web", "URL", "浏览器", "主页", "持续连接", "非持续", "流水线", "RTT", "Cookie", "万维网"):
        return {
            "model": "Web 访问通常是浏览器拿 URL，通过 DNS 找到服务器 IP，再用 TCP 连接承载 HTTP 请求/响应。HTTP 是应用层协议，本身无状态；持续连接可在同一 TCP 连接上传多个对象，减少重复建连的 RTT。",
            "check": "先把一次访问拆成 DNS、TCP 建连、HTTP 请求/响应，再看题干是否要求计入 RTT。",
            "boundary": "HTTP 不负责可靠传输，TCP 负责；URL 是资源定位符，不是传输协议；SMTP 属于邮件发送，不属于普通网页获取。"
        }
    if has_primary("SMTP", "POP3", "IMAP", "MIME", "电子邮件", "邮件服务器", "发送邮件", "读取邮件"):
        return {
            "model": "电子邮件系统要分发送和读取：SMTP 负责把邮件从客户端送到邮件服务器、服务器之间转发；POP3/IMAP 负责用户从邮箱服务器读取邮件；MIME 扩展邮件内容类型，让邮件能带非 ASCII 文本和附件。",
            "check": "先看动作是发送、转发、收取，还是内容扩展，再选 SMTP/POP3/IMAP/MIME。",
            "boundary": "SMTP 不负责从邮箱取信；POP3/IMAP 不负责服务器之间投递；MIME 不是传输协议。"
        }
    if has_primary("FTP", "控制连接", "数据连接", "文件传输"):
        return {
            "model": "FTP 是应用层文件传输协议，使用控制连接和数据连接两条 TCP 连接。控制连接负责命令和响应，通常连接到服务器 21 端口；数据连接负责真正传文件，主动/被动模式会影响端口方向。",
            "check": "先区分命令控制和文件数据，再看题干问连接数、端口还是 TCP/UDP。",
            "boundary": "FTP 不是网页浏览协议；控制连接不传文件内容；FTP 常用 TCP 而不是 UDP。"
        }
    if has_primary("数字签名", "公钥", "私钥", "报文鉴别", "不可否认", "加密", "散列", "哈希"):
        return {
            "model": "安全题先分目标：保密性靠加密，完整性/来源确认靠报文鉴别，数字签名还能提供不可否认。数字签名的方向是发送方用自己的私钥签名，接收方用发送方公钥验证；保密加密常用接收方公钥，方向不要混。",
            "check": "先问题干要保密、鉴别、完整性、认证还是不可否认，再看公钥/私钥是用于加密还是签名。",
            "boundary": "加密不自动等于签名；哈希不等于加密；公钥验证签名，私钥生成签名。"
        }
    if has_primary("防火墙", "VPN", "IPsec", "SSL", "TLS", "攻击", "恶意", "入侵", "隧道", "拒绝服务"):
        return {
            "model": "主动攻击强调攻击者主动改变、注入或破坏，如篡改、恶意程序、拒绝服务；被动攻击更像窃听。防火墙按规则过滤或代理访问，VPN 通过隧道和加密在不可信网络上建立逻辑专用通道；SSL/TLS 常用于安全通信。",
            "check": "先判断题干问攻击类型、访问控制、加密隧道，还是安全协议层次。",
            "boundary": "防火墙不是万能杀毒；VPN 不等于物理专线；SSL 是安全套接字层，TLS 是运输层安全。"
        }
    if has_primary("三次握手", "四次挥手", "序号", "确认号", "ACK", "SYN", "FIN", "滑动窗口", "流量控制", "可靠传输", "超时"):
        return {
            "model": "TCP 用序号、确认、重传和窗口实现可靠传输。三次握手建立双方收发能力，四次挥手释放两个方向的数据流；ACK 号表示期望收到的下一个字节序号，接收窗口用于流量控制，避免发送方把接收方淹没。",
            "check": "先画发送方向和字节序号，再看 ACK 表示“下一个想要的字节”，窗口表示“还能收多少”。",
            "boundary": "流量控制管接收方来不来得及收，拥塞控制管网络是否堵；ACK 不是已经收到的最后一个序号本身，而是下一个期望序号。"
        }
    if has_primary("UDP", "TCP", "端口", "套接字", "运输层", "无连接", "面向连接"):
        return {
            "model": "运输层在主机进程之间提供端到端通信，用端口号完成复用和分用。UDP 无连接、开销小、不保证可靠；TCP 面向连接、可靠、有流量控制和拥塞控制。套接字通常由 IP 地址和端口等信息标识通信端点。",
            "check": "先看题干问进程到进程、端口、TCP/UDP 差异，还是套接字标识。",
            "boundary": "IP 负责主机到主机，运输层负责进程到进程；UDP 可以检错但不负责重传和排序；端口不是 IP 地址。"
        }
    if has_primary("拥塞", "cwnd", "ssthresh", "慢开始", "拥塞避免", "快重传", "快恢复", "MSS") or "TCP 拥塞控制" in knowledge:
        return {
            "model": "TCP 拥塞控制站在网络角度调节发送速度。慢开始让拥塞窗口 cwnd 指数增长，到 ssthresh 后进入拥塞避免的线性增长；检测到丢包后根据超时或重复 ACK 调整 cwnd 和 ssthresh。",
            "check": "先判断事件是超时还是重复 ACK，再按阶段更新 cwnd/ssthresh。",
            "boundary": "拥塞控制不是接收方流量控制；cwnd 是发送方对网络拥塞的估计窗口，rwnd 是接收方窗口。"
        }
    if has_primary("以太网", "MAC", "CSMA/CD", "碰撞", "最小帧", "交换机", "网桥", "集线器", "VLAN", "广播域", "冲突域", "IEEE 802.3"):
        return {
            "model": "以太网是数据链路层局域网技术，帧里用 MAC 地址在同一链路/局域网内交付。共享式以太网用 CSMA/CD 处理碰撞，最小帧长是为了在发送完前还能检测到最远端碰撞；交换机按 MAC 表转发，能隔离冲突域，但默认不隔离广播域。",
            "check": "先判断设备是集线器、交换机还是路由器；最小帧长题按“单程传播时延 -> 往返争用期 -> 乘数据率”计算。",
            "boundary": "MAC 管一跳/局域网内交付，IP 管跨网络转发；交换机不是路由器；CSMA/CD 最小帧长不能只算单程。"
        }
    if has("OSI", "TCP/IP", "体系结构", "协议", "服务", "接口", "分层", "五层", "七层", "标准"):
        return {
            "model": "分层题先背方向：下层向上层提供服务，上层通过接口使用下层服务；协议是同层实体之间遵守的规则。OSI 七层偏理论，TCP/IP 四层偏实际，教材五层常把它们折中成应用层、运输层、网络层、数据链路层、物理层。",
            "check": "先判断题干说的是“服务/接口”还是“协议/同层规则”，再把功能放回对应层。",
            "boundary": "服务是上下层关系，协议是同层关系；模型名称和具体协议不要互相替代。"
        }
    if has("bps", "bit", "Byte", "Baud", "波特", "码元", "奈氏", "香农", "带宽", "吞吐", "时延", "利用率", "电路交换", "分组交换", "报文交换", "传播"):
        return {
            "model": "性能题先分清单位和时延来源：bit 是位，Byte 是字节，1B=8b；bps 是每秒比特数，Baud 是每秒码元数。发送时延=数据量/发送速率，传播时延=距离/传播速率；分组交换共享链路，利用率过高会带来排队时延。",
            "check": "先统一单位，再判断考的是发送、传播、处理、排队，还是交换方式/利用率。",
            "boundary": "带宽是理想能力，吞吐量是实际通过量；发送速率不是传播速率；利用率不是越接近 100% 越好。"
        }
    if has("双绞线", "同轴", "光纤", "无线", "微波", "红外", "激光", "单模", "多模", "FTT", "传输媒体"):
        return {
            "model": "物理层关心比特怎样在介质上传。导引型介质把信号限制在线缆里，如双绞线、同轴、光纤；非导引型介质在自由空间传播，如无线电、微波、红外、激光。光纤传光信号，抗电磁干扰强，单模常用于更远距离。",
            "check": "先判断是导引型还是非导引型，再看题干要求距离、带宽、抗干扰还是术语填法。",
            "boundary": "传输媒体不是协议；无线局域网标准不是简单等同于无线传输介质；光纤里不是电信号直接跑。"
        }
    if has("PCM", "调制", "编码", "曼彻斯特", "采样", "量化", "QAM", "ASK", "FSK", "PSK", "基带", "频带"):
        return {
            "model": "信号题先分两类：编码是把数字比特变成适合线路传输的数字信号，调制是把数字/模拟信息搬到载波上。PCM 的链条是采样、量化、编码；曼彻斯特编码用每个码元中间的跳变同时携带时钟和数据。",
            "check": "看到数字、频率、采样、码元时先写出规则，再逐步代入或逐位判读。",
            "boundary": "编码不等于加密；码元不一定等于 bit；曼彻斯特题不能只看高低电平，要看跳变规则。"
        }
    if has("PPP", "HDLC", "LCP", "NCP", "点到点", "字符填充", "零比特填充"):
        return {
            "model": "PPP/HDLC 属于数据链路层的点到点链路协议，解决一段链路上的成帧、透明传输和差错检测。PPP 由封装方法、LCP、NCP 组成；点到点链路只说明链路两端节点数量，不是应用层 P2P。",
            "check": "先把 PPP 放在链路层，再判断题干问组成、填充方法、链路类型还是和 P2P 混淆。",
            "boundary": "PPP 不是 P2P；点到点信道不是广播信道；链路层的一跳不负责端到端路径选择。"
        }
    if has("成帧", "透明传输", "CRC", "奇偶", "差错", "ARQ", "确认", "重传", "帧"):
        return {
            "model": "数据链路层把物理层比特流组织成帧。成帧解决边界，透明传输解决数据里出现定界符的问题，差错检测如 CRC 只能发现错误；要恢复错误通常靠确认、超时和重传这类 ARQ 机制。",
            "check": "先判断题干问链路层三个基本问题、检测能力，还是确认重传流程。",
            "boundary": "CRC 不是纠错码；流量控制不等于教材常列的三个基本问题；链路层是一跳，不是全网路由。"
        }
    if has("以太网", "MAC", "CSMA/CD", "碰撞", "最小帧", "交换机", "网桥", "集线器", "VLAN", "广播域", "冲突域", "IEEE 802.3"):
        return {
            "model": "以太网是数据链路层局域网技术，帧里用 MAC 地址在同一链路/局域网内交付。共享式以太网用 CSMA/CD 处理碰撞，最小帧长是为了在发送完前还能检测到最远端碰撞；交换机按 MAC 表转发，能隔离冲突域，但默认不隔离广播域。",
            "check": "先判断设备是集线器、交换机还是路由器，再看题干考 MAC、碰撞、帧长、冲突域/广播域。",
            "boundary": "MAC 管一跳/局域网内交付，IP 管跨网络转发；交换机不是路由器；广播式发送不等于所有帧的目的地址都是广播地址。"
        }
    if has("无线局域网", "802.11", "802.15", "Wi-Fi", "蓝牙", "CSMA/CA", "AP", "BSS", "WPAN"):
        return {
            "model": "无线局域网属于 802.11，常用 CSMA/CA 避免碰撞，因为无线节点难以像有线以太网那样一边发送一边可靠检测碰撞。AP/BSS 描述无线接入结构；802.15 更偏个人区域网，如蓝牙。",
            "check": "先看题干是无线局域网还是个人区域网，再判断是接入结构、介质访问控制还是标准编号。",
            "boundary": "CSMA/CA 是避免碰撞，CSMA/CD 是检测碰撞；Wi-Fi 不是蓝牙；无线不代表脱离链路层规则。"
        }
    if has("IP 数据报", "IPv4", "首部", "分片", "MTU", "片偏移", "MF", "DF", "TTL", "ARP", "ICMP", "IGMP", "多播"):
        return {
            "model": "网络层用 IP 数据报跨网络转发。超过链路 MTU 可能分片，同一原始数据报靠标识字段重组，MF 表示后面是否还有分片，片偏移以 8 字节为单位；ARP 负责 IP 找 MAC，ICMP 负责差错报告/探测，IGMP 管多播成员关系。",
            "check": "先判断题干问 IP 首部字段、分片计算，还是 ARP/ICMP/IGMP 的分工。",
            "boundary": "ARP 不是查域名，DNS 才查域名；TTL 防兜圈不是保证可靠；MF 只有 0/1，不是分片序号。"
        }
    if has("IP 地址", "子网", "掩码", "CIDR", "VLSM", "NAT", "A类", "B类", "C类", "广播地址", "网络地址", "主机号", "127."):
        return {
            "model": "地址题先把 IP 地址分成网络位和主机位。传统分类按首字节判断 A/B/C 类；CIDR 用斜线后的前缀长度决定网络位。主机位全 0 通常表示网络地址，全 1 通常表示定向广播地址；NAT 把内网私有地址转换成公网地址。",
            "check": "先确定类别或前缀长度，再写出网络位/主机位，最后看全 0、全 1、可用主机或地址块边界。",
            "boundary": "网络地址不能当普通主机地址；127/8 是环回；私有地址可在内网重复，公网路由不可直接转发私有地址。"
        }
    if has("UDP", "TCP", "端口", "套接字", "运输层", "复用", "分用", "无连接", "面向连接"):
        return {
            "model": "运输层在主机进程之间提供端到端通信，用端口号完成复用和分用。UDP 无连接、开销小、不保证可靠；TCP 面向连接、可靠、有流量控制和拥塞控制。套接字通常由 IP 地址和端口等信息标识通信端点。",
            "check": "先看题干问进程到进程、端口、TCP/UDP 差异，还是套接字标识。",
            "boundary": "IP 负责主机到主机，运输层负责进程到进程；UDP 不等于完全不能用，实时/简单查询常用；端口不是 IP 地址。"
        }
    if has("三次握手", "四次挥手", "序号", "确认号", "ACK", "SYN", "FIN", "滑动窗口", "流量控制", "可靠传输", "超时"):
        return {
            "model": "TCP 用序号、确认、重传和窗口实现可靠传输。三次握手建立双方收发能力，四次挥手释放两个方向的数据流；ACK 号表示期望收到的下一个字节序号，接收窗口用于流量控制，避免发送方把接收方淹没。",
            "check": "先画发送方向和字节序号，再看 ACK 表示“下一个想要的字节”，窗口表示“还能收多少”。",
            "boundary": "流量控制管接收方来不来得及收，拥塞控制管网络是否堵；ACK 不是已经收到的最后一个序号本身，而是下一个期望序号。"
        }
    if has("拥塞", "cwnd", "ssthresh", "慢开始", "拥塞避免", "快重传", "快恢复", "MSS"):
        return {
            "model": "TCP 拥塞控制站在网络角度调节发送速度。慢开始让拥塞窗口 cwnd 指数增长，到 ssthresh 后进入拥塞避免的线性增长；检测到丢包后根据超时或重复 ACK 调整 cwnd 和 ssthresh。",
            "check": "先判断事件是超时还是重复 ACK，再按阶段更新 cwnd/ssthresh。",
            "boundary": "拥塞控制不是接收方流量控制；cwnd 是发送方对网络拥塞的估计窗口，rwnd 是接收方窗口。"
        }
    if "TCP 拥塞控制" in knowledge:
        return {
            "model": "拥塞控制调的是发送方对网络压力的估计，不是接收缓存大小。做题时抓住 cwnd、ssthresh、慢开始、拥塞避免这些状态量和阶段。",
            "check": "先看题干事件，再决定窗口如何变化。",
            "boundary": "不要把拥塞控制和链路层功能、流量控制混在一起。"
        }

    return {
        "model": f"这题属于“{knowledge}”。先抓题干关键词，再把它放回对应层次：物理层传比特，链路层传帧，网络层转发 IP 分组，运输层连接进程，应用层规定具体应用交互。",
        "check": "先定位层次，再看题干问定义、字段、机制、计算还是反向选择。",
        "boundary": "相邻概念要按层次和作用对象区分，不要只凭词面相似作答。"
    }


def type_strategy(q):
    t = q.get("type")
    neg = is_negative(q)
    if t == "multi":
        if neg:
            return "这是多选反向题：答案不是“正确说法”，而是题干要求挑出的错误/不属于/不可能项。先把正确但不选的项放一边，再选真正违背规则的项。"
        return "这是多选正向题：不要找“唯一最佳项”，而是把所有符合题干规则的并列项都选上；未选项通常是相邻概念、层次错位或范围扩大。"
    if t == "single":
        if neg:
            return "这是单选反向题：四个选项里只有一个最符合“不属于/错误/不可能”的要求，正确说法反而不能选。"
        return "这是单选题：先用底层规则锁定正确项，再把最像的干扰项按层次、字段或术语边界排掉。"
    if t == "tf":
        return "这是判断题：不要只看关键词熟不熟，要检查整句话的主语、层次、绝对词和因果顺序是否成立。"
    return "这是填空题：先看空格数量和题干限定词，再按规则逐空填写，优先使用题库标准术语。"


def selected_unselected(q):
    amap = option_map(q)
    keys = answer_keys(q)
    selected = []
    unselected = []
    for key in sorted(amap):
        item = f"{key}. {amap[key]}"
        if key in keys:
            selected.append(item)
        else:
            unselected.append(item)
    return selected, unselected


def option_breakdown(q):
    amap = option_map(q)
    if not amap:
        return []
    keys = answer_keys(q)
    reasons = option_reason_map(reason_of(q))
    neg = is_negative(q)
    lines = []
    for key in sorted(amap):
        chosen = key in keys
        if q.get("type") == "multi" and neg:
            verdict = "要选：它正是题干要找的错误/不属于项" if chosen else "不选：它是正确或不违背题干的说法"
        else:
            verdict = "应选：符合题干规则" if chosen else "不选：和本题规则不匹配"
        detail = reasons.get(key, "")
        if detail:
            detail = re.sub(rf"^{key}\s*", "", detail).strip("：:，,。 ")
            lines.append(f"- {key}. {amap[key]}：{verdict}；{detail}。")
        else:
            lines.append(f"- {key}. {amap[key]}：{verdict}。")
    return lines


def fill_steps(q, profile):
    ans = q.get("answer")
    answers = ans if isinstance(ans, list) else [ans]
    stem = q.get("stem", "")
    lines = []
    lines.append(f"- 先看限定：{sentence_trim(strip_numbering(stem), 78)}")
    lines.append(f"- 套用规则：{sentence_trim(profile['check'], 88)}")
    if len(answers) > 1:
        for i, item in enumerate(answers, 1):
            lines.append(f"- 第 {i} 空填 `{item}`：它对应题干中的第 {i} 个限定或并列概念。")
    else:
        lines.append(f"- 标准答案填 `{answers[0]}`：它正好对应题干限定的概念/字段/数值。")

    rich = stem + " " + " ".join(str(x) for x in answers)
    if any(x in rich for x in ["kHz", "Hz", "bit", "bps", "Mbit", "RTT", "时延", "码元", "PCM", "带宽"]):
        lines.append("- 遇到计算量先统一单位，再写公式，最后代入；不要把 bit、Byte、Baud 混在一起。")
    if any(x in rich for x in ["IP", "掩码", "B类", "C类", "CIDR", "255", "127"]):
        lines.append("- 地址题按“确定网络位 -> 主机位清零/全一 -> 得出网络/广播/主机范围”的顺序推。")
    if any(x in rich for x in ["曼彻斯特", "编码", "图"]):
        lines.append("- 图形编码题要先按码元切格，再按跳变方向逐位读，最后把每一位连起来。")
    return lines


def reasoning_steps(q, profile):
    t = q.get("type")
    eye = eye_of(q)
    reason = reason_of(q)
    trap = trap_of(q)
    lines = [f"- 第一步抓题眼：`{eye}`，它决定本题不是泛泛复习整章，而是考这个具体规则。"]
    lines.append(f"- 第二步定规则：{profile['check']}")
    if t == "blank":
        lines.append(f"- 第三步填答案：**{answer_text(q)}**。{reason}")
        lines.append("- 详细的逐空依据看下面“空格拆解”，先保证标准词形和单位别写错。")
    elif t == "tf":
        ans = answer_text(q)
        lines.append(f"- 第三步判整句：本题判断为 **{ans}**。{reason}")
        if ans == "错误":
            lines.append("- 改成正确说法时，要保留题干中正确的对象，只改错位的层次、因果、范围或绝对词。")
    elif t in ("single", "multi"):
        lines.append(f"- 第三步看选项：答案是 **{answer_text(q)}**。{reason}")
        if t == "multi":
            selected, unselected = selected_unselected(q)
            if selected:
                lines.append(f"- 应选项是一组并列成立的说法：{'；'.join(selected)}。")
            if unselected:
                lines.append(f"- 不选项的共同问题是层次、范围或术语不符合本题：{'；'.join(unselected)}。")
    lines.append(f"- 最后防坑：{trap}")
    return lines


def make_quick(q):
    profile = topic_profile(q)
    t = q.get("type")
    lines = [
        f"题眼：{eye_of(q)}",
        f"先定规则：{type_strategy(q)}",
        f"做题理由：{sentence_trim(reason_of(q), 170)}",
    ]
    if t == "multi":
        selected, unselected = selected_unselected(q)
        if selected:
            lines.append(f"应选组：{'；'.join(selected)}")
        if unselected:
            lines.append(f"排除组：{'；'.join(unselected)}")
        lines.append(f"为什么是多选：{multi_reason(q)}")
    elif t == "single":
        lines.append(f"正确项：{answer_text(q)}")
        unselected = selected_unselected(q)[1]
        if unselected:
            lines.append(f"排除方向：{'；'.join(unselected)} 不是本题规则对应的答案。")
    elif t == "tf":
        lines.append(f"判断结论：{answer_text(q)}")
        if answer_text(q) == "错误":
            lines.append("改正方向：把题干中错位的时间顺序、协议层次、范围或绝对说法改掉才成立。")
    else:
        lines.append(f"标准填法：{answer_text(q)}")
        if isinstance(q.get("answer"), list) and len(q.get("answer")) > 1:
            lines.append("逐空思路：每个空对应题干中的一个并列限定，按顺序填写。")
    lines.append(f"易错：{sentence_trim(trap_of(q), 120)}")
    lines.append(f"底层抓手：{sentence_trim(profile['model'], 120)}")
    return "\n".join(lines)


def multi_reason(q):
    keys = answer_keys(q)
    total = len(option_map(q))
    if is_negative(q):
        return "因为题干要求找错误/不属于项，答案里的每一项都分别违反了底层规则；正确说法虽然看起来熟，也不能选。"
    if len(keys) == total and total > 0:
        return "因为四个选项都从不同侧面符合题干，没有必须排除的干扰项；全选题最容易因为“觉得应该错一个”而少选。"
    if len(keys) > 1:
        return "因为这些正确项是同一概念的组成部分、并列特征或同一机制的不同条件，少选会漏掉一个成立侧面。"
    return "虽然题型是多选，但本题只有一个选项真正符合规则，其余都是相邻概念或范围错位。"


def make_knowledge(q):
    profile = topic_profile(q)
    lines = [
        f"本题考什么：{q.get('chapter')} / {q.get('knowledge')}，具体考 `{eye_of(q)}`。",
        f"题眼怎么抓：{type_strategy(q)}",
        f"底层模型：{profile['model']}",
        "本题怎么一步步做：",
    ]
    lines.extend(reasoning_steps(q, profile))

    if q.get("type") in ("single", "multi"):
        lines.append("选项拆解：")
        lines.extend(option_breakdown(q))
    elif q.get("type") == "tf":
        lines.append("判断句拆解：")
        lines.append(f"- 主语/对象：{sentence_trim(strip_numbering(q.get('stem', '')), 70)}")
        lines.append(f"- 结论：{answer_text(q)}。{sentence_trim(reason_of(q), 130)}")
        if answer_text(q) == "错误":
            lines.append("- 复习时要练“改错”：能说出它错在哪个词，才算真正会做判断题。")
    else:
        lines.append("空格拆解：")
        lines.extend(fill_steps(q, profile))

    lines.extend([
        f"相邻概念边界：{profile['boundary']}",
        f"小白复述：这题我先抓 `{eye_of(q)}`，再按“{sentence_trim(profile['check'], 48)}”判断，所以答案是 **{answer_text(q)}**。",
    ])
    return "\n".join(lines)


def make_full_explanation(q):
    return f"【快速做题】\n{q['quickExplanation']}\n\n【知识点详解】\n{q['knowledgeDetail']}"


def main():
    if not BACKUP.exists():
        shutil.copy2(QUESTIONS, BACKUP)
    source = BACKUP if BACKUP.exists() else QUESTIONS
    questions = json.loads(source.read_text(encoding="utf-8"))

    for q in questions:
        apply_metadata_fix(q)
        q["quickExplanation"] = make_quick(q)
        q["knowledgeDetail"] = make_knowledge(q)
        q["explanation"] = make_full_explanation(q)

    QUESTIONS.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    type_counts = {}
    chapter_counts = {}
    for q in questions:
        type_counts[q.get("typeName")] = type_counts.get(q.get("typeName"), 0) + 1
        chapter_counts[q.get("chapter")] = chapter_counts.get(q.get("chapter"), 0) + 1

    repeated_tail = sum("小白复述模板" in (q.get("knowledgeDetail", "") + q.get("quickExplanation", "")) for q in questions)
    avg_quick = sum(len(q.get("quickExplanation", "")) for q in questions) / len(questions)
    avg_detail = sum(len(q.get("knowledgeDetail", "")) for q in questions) / len(questions)
    missing = [
        label_of(q)
        for q in questions
        if not q.get("quickExplanation") or not q.get("knowledgeDetail") or not q.get("explanation")
    ]

    REPORT.write_text(
        "# v2.6 个性化解析增强报告\n\n"
        f"- 题目总数：{len(questions)}\n"
        f"- 题型分布：{type_counts}\n"
        f"- 章节分布：{chapter_counts}\n"
        f"- 缺失解析：{missing or '无'}\n"
        f"- quickExplanation 平均长度：{avg_quick:.1f}\n"
        f"- knowledgeDetail 平均长度：{avg_detail:.1f}\n"
        f"- 旧模板尾句残留：{repeated_tail}\n"
        f"- 备份文件：{BACKUP}\n\n"
        "## 新结构\n\n"
        "- 快速做题：题眼、先定规则、做题理由、应选/排除/填法、易错、底层抓手。\n"
        "- 知识点详解：本题考什么、题眼怎么抓、必要底层模型、本题步骤、选项/空格/判断句拆解、相邻概念边界、小白复述。\n",
        encoding="utf-8",
    )

    print(f"updated {len(questions)} questions")
    print(f"backup: {BACKUP}")
    print(f"report: {REPORT}")
    print(f"missing: {len(missing)}")
    print(f"old template tail: {repeated_tail}")


if __name__ == "__main__":
    main()
