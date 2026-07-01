import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = ROOT / "app" / "src" / "main" / "assets" / "xi_thought_questions.json"
REPORT_PATH = ROOT / "explanation_work" / "xi_knowledge_explanation_report.md"

BANNED_PHRASES = [
    "答题抓手",
    "复习抓手",
    "题眼",
    "绑定",
    "复习定位",
    "先判断",
    "应该关注",
    "方向相关",
    "层级不对",
    "正好补上",
    "本题要找",
    "不是让你",
    "熟悉口号",
    "核心短语分层写全",
    "写感想",
    "不要泛泛",
    "先看题干",
    "题干关键词",
    "标准答案不对应",
    "可能也是",
    "某章",
    "本题考",
    "原句中的规范表述",
    "原句中的固定概念",
    "含义由完整句子限定",
    "完整表述落在",
    "放回完整表述中理解",
]

TERM_NOTES = [
    ("实现中华民族伟大复兴", "实现中华民族伟大复兴是近代以来中华民族最伟大的梦想，是党团结带领人民长期奋斗的历史主题，指向国家富强、民族振兴、人民幸福。"),
    ("中国式现代化", "中国式现代化是中国共产党领导的社会主义现代化，用中国自己的制度、道路和发展方式推进民族复兴，不等同于照搬西方现代化模式。"),
    ("习近平新时代中国特色社会主义思想", "习近平新时代中国特色社会主义思想是新时代党的创新理论成果，系统回答新时代坚持和发展什么样的中国特色社会主义、怎样坚持和发展中国特色社会主义等重大时代课题。"),
    ("中国特色社会主义", "中国特色社会主义是改革开放以来党的全部理论和实践的主题，包括道路、理论、制度、文化四个基本支撑。"),
    ("科学社会主义", "科学社会主义揭示社会主义代替资本主义的历史趋势，是中国特色社会主义的理论源头；中国特色社会主义是在中国具体条件下坚持和发展科学社会主义。"),
    ("马克思主义", "马克思主义是立党立国、兴党兴国的根本指导思想，中国化时代化的马克思主义要同中国具体实际、中华优秀传统文化结合。"),
    ("马克思主义中国化时代化", "马克思主义中国化时代化就是把马克思主义基本原理同中国具体实际、同中华优秀传统文化相结合，使理论能够回答中国问题、时代问题。"),
    ("两个结合", "“两个结合”指把马克思主义基本原理同中国具体实际相结合、同中华优秀传统文化相结合，是推进理论创新的根本途径。"),
    ("六个必须坚持", "“六个必须坚持”是习近平新时代中国特色社会主义思想的世界观和方法论，包括人民至上、自信自立、守正创新、问题导向、系统观念、胸怀天下。"),
    ("十个明确", "“十个明确”是习近平新时代中国特色社会主义思想的主体内容，集中体现这一思想体系的主要观点和基本精神，起到“四梁八柱”的统摄作用。"),
    ("十四个坚持", "“十四个坚持”是新时代坚持和发展中国特色社会主义的基本方略，偏重实践层面的路线、原则和要求。"),
    ("十三个方面", "“十三个方面成就”概括新时代党和国家事业取得的历史性成就、发生的历史性变革，属于成就维度。"),
    ("两个确立", "“两个确立”指确立习近平同志党中央的核心、全党的核心地位，确立习近平新时代中国特色社会主义思想的指导地位。"),
    ("两个维护", "“两个维护”指坚决维护习近平总书记党中央的核心、全党的核心地位，坚决维护党中央权威和集中统一领导。"),
    ("四个自信", "“四个自信”是道路自信、理论自信、制度自信、文化自信，说明坚持中国特色社会主义的信心来源。"),
    ("五位一体", "“五位一体”总体布局包括经济建设、政治建设、文化建设、社会建设、生态文明建设，说明中国特色社会主义事业的总体展开面。"),
    ("四个全面", "“四个全面”战略布局包括全面建设社会主义现代化国家、全面深化改革、全面依法治国、全面从严治党。"),
    ("三个务必", "“三个务必”是党的二十大提出的政治要求：不忘初心、牢记使命，谦虚谨慎、艰苦奋斗，敢于斗争、善于斗争。"),
    ("五个必由之路", "“五个必由之路”概括新时代奋斗经验：坚持党的全面领导、中国特色社会主义、团结奋斗、贯彻新发展理念、全面从严治党。"),
    ("党的十九大", "党的十九大把习近平新时代中国特色社会主义思想确立为党必须长期坚持的指导思想，并写入党章。"),
    ("党的二十大", "党的二十大围绕全面建设社会主义现代化国家、全面推进中华民族伟大复兴作出战略部署。"),
    ("党的十八届三中全会", "党的十八届三中全会对全面深化改革作出系统部署，明确全面深化改革的总目标是完善和发展中国特色社会主义制度、推进国家治理体系和治理能力现代化。"),
    ("党的十八届四中全会", "党的十八届四中全会专题研究全面依法治国，提出建设中国特色社会主义法治体系、建设社会主义法治国家。"),
    ("党的十九届六中全会", "党的十九届六中全会通过党的第三个历史决议，突出总结党的百年奋斗重大成就和历史经验。"),
    ("人民至上", "人民至上是根本价值立场，要求发展为了人民、发展依靠人民、发展成果由人民共享。"),
    ("人民当家作主", "人民当家作主是社会主义民主政治的本质和核心，强调国家权力属于人民，人民通过制度化渠道管理国家和社会事务。"),
    ("全过程人民民主", "全过程人民民主贯通民主选举、民主协商、民主决策、民主管理、民主监督，强调民主不是只在投票时存在，而是覆盖治理全过程。"),
    ("以人民为中心", "以人民为中心是发展思想和价值取向，把人民对美好生活的向往作为奋斗目标。"),
    ("人民", "人民是历史的创造者，是决定党和国家前途命运的根本力量，也是党执政的最大底气和最深厚根基。"),
    ("人民立场", "人民立场是中国共产党的根本政治立场，决定党的性质、宗旨和价值取向。"),
    ("人民民主专政", "人民民主专政是我国国体，体现对人民实行民主、对敌对势力实行专政的统一。"),
    ("人民代表大会制度", "人民代表大会制度是我国根本政治制度，是人民当家作主的重要制度载体。"),
    ("协商民主", "协商民主是在决策前和决策实施中开展充分协商，体现有事好商量、众人的事情由众人商量。"),
    ("统一战线", "统一战线的关键在团结一切可以团结的力量，坚持党的领导是统一战线最核心最根本的问题。"),
    ("党的领导", "党的领导是中国特色社会主义最本质的特征和中国特色社会主义制度的最大优势，是推进各项事业的根本保证。"),
    ("中国共产党领导", "中国共产党领导是中国特色社会主义最本质的特征，也是中国式现代化区别于其他现代化道路的根本政治保证。"),
    ("党中央权威和集中统一领导", "党中央权威和集中统一领导是党的领导的最高原则，保证全党全国行动统一、步调一致。"),
    ("民主集中制", "民主集中制是党的根本组织原则和领导制度，强调充分发扬民主与正确集中相统一。"),
    ("全面从严治党", "全面从严治党是新时代党的建设鲜明主题，核心是把严的基调、严的措施、严的氛围长期坚持下去。"),
    ("党的自我革命", "党的自我革命是党跳出治乱兴衰历史周期率的第二个答案，强调党依靠自身力量清除病灶、保持先进性和纯洁性。"),
    ("勇于自我革命", "勇于自我革命是中国共产党区别于其他政党的显著标志，体现党敢于直面问题、修正错误。"),
    ("反腐败", "反腐败是最彻底的自我革命，关系党能否保持肌体健康、赢得人民信任。"),
    ("零容忍", "零容忍是反腐败的鲜明态度，表示对腐败问题发现一起查处一起，不搞例外和变通。"),
    ("关键少数", "“关键少数”主要指领导干部，抓住领导干部就抓住了全面从严治党、依法治国和作风建设的关键。"),
    ("党的政治建设", "党的政治建设是党的根本性建设，决定党的建设方向和效果。"),
    ("党的思想建设", "党的思想建设用党的创新理论武装全党，解决理想信念、理论认同和政治忠诚问题。"),
    ("党的作风", "党的作风关系党同人民群众的血肉联系，作风问题本质上是党性问题。"),
    ("改革开放", "改革开放是决定当代中国命运的关键一招，也是坚持和发展中国特色社会主义、实现民族复兴的必由之路。"),
    ("全面深化改革", "全面深化改革重在破除体制机制障碍，目标是完善和发展中国特色社会主义制度、推进国家治理体系和治理能力现代化。"),
    ("全面深化改革开放", "全面深化改革开放把改革和开放贯通起来，通过制度创新和高水平开放激发发展动力。"),
    ("新发展理念", "新发展理念包括创新、协调、绿色、开放、共享，是引领高质量发展的指挥棒。"),
    ("高质量发展", "高质量发展是全面建设社会主义现代化国家的首要任务，强调质量、效率、动力变革，不是单纯追求速度。"),
    ("创新", "创新是引领发展的第一动力，在现代化建设全局中居于核心位置。"),
    ("协调", "协调解决发展不平衡问题，强调区域、城乡、经济社会等方面整体推进。"),
    ("绿色", "绿色发展解决人与自然和谐共生问题，要求把生态环境作为发展的内在约束。"),
    ("开放", "开放发展解决内外联动问题，强调利用国内国际两个市场、两种资源。"),
    ("共享", "共享发展解决社会公平正义问题，要求发展成果更多更公平惠及全体人民。"),
    ("供给侧结构性改革", "供给侧结构性改革从生产供给端提高质量和效率，重点是去产能、去库存、去杠杆、降成本、补短板。"),
    ("新发展格局", "新发展格局以国内大循环为主体、国内国际双循环相互促进，立足扩大内需和高水平开放。"),
    ("教育", "教育是国之大计、党之大计，是基础性、先导性事业，承担培养人才、支撑科技和现代化建设的功能。"),
    ("科技", "科技自立自强是国家强盛之基、安全之要，是高质量发展的关键支撑。"),
    ("人才", "人才是第一资源，是创新活动中最活跃、最积极的因素。"),
    ("人才强国战略", "人才强国战略强调把人才作为国家竞争和民族复兴的战略资源，形成规模宏大、结构合理、素质优良的人才队伍。"),
    ("依法治国", "全面依法治国是国家治理的一场深刻革命，核心是建设中国特色社会主义法治体系、建设社会主义法治国家。"),
    ("中国特色社会主义法治体系", "中国特色社会主义法治体系是全面依法治国的总抓手，包括法律规范、法治实施、法治监督、法治保障和党内法规体系。"),
    ("社会主义法治国家", "社会主义法治国家强调国家治理各方面纳入法治轨道，实现科学立法、严格执法、公正司法、全民守法。"),
    ("宪法", "宪法是国家的根本法，是治国安邦的总章程，在法律规范体系中具有最高法律地位、法律权威和法律效力。"),
    ("科学立法", "科学立法是良法善治的前提，要求立法符合规律、反映人民意志、解决实际问题。"),
    ("严格执法", "严格执法要求行政机关依法全面履职，是法治政府建设的关键环节。"),
    ("公正司法", "公正司法是维护社会公平正义的最后一道防线，要求司法活动独立公正、程序正当、结果公正。"),
    ("全民守法", "全民守法强调全体社会成员尊法学法守法用法，是法治社会建设的基础。"),
    ("党内法规体系", "党内法规体系纳入中国特色社会主义法治体系，体现依规治党和依法治国的有机统一。"),
    ("文化自信", "文化自信是更基础、更广泛、更深厚的自信，是道路自信、理论自信、制度自信的文化根基。"),
    ("中华优秀传统文化", "中华优秀传统文化是中华民族的突出优势，是中国特色社会主义植根的文化土壤。"),
    ("创造性转化", "创造性转化是把传统文化中仍有价值的内容转化成适合当代社会的表达和形式。"),
    ("创新性发展", "创新性发展是在传统文化基础上结合时代条件形成新的内容、新的表达和新的实践。"),
    ("社会主义核心价值观", "社会主义核心价值观凝结全体人民共同价值追求，是凝魂聚气、强基固本的基础工程。"),
    ("核心价值观", "核心价值观是一个民族、一个国家最持久、最深层的力量，决定文化性质和方向。"),
    ("伟大建党精神", "伟大建党精神包括坚持真理、坚守理想，践行初心、担当使命，不怕牺牲、英勇斗争，对党忠诚、不负人民，是中国共产党精神谱系的源头。"),
    ("中国精神", "中国精神以爱国主义为核心的民族精神和以改革创新为核心的时代精神为主要内容。"),
    ("增进民生福祉", "增进民生福祉是发展的根本目的，民生建设通常围绕就业、收入、教育、医疗、社保、住房等展开。"),
    ("共同富裕", "共同富裕是社会主义的本质要求，是中国式现代化的重要特征，不等于同步富裕、同时富裕或平均主义。"),
    ("就业", "就业是最基本的民生，关系群众收入、社会稳定和人的发展。"),
    ("社会治理", "社会治理强调党委领导、政府负责、民主协商、社会协同、公众参与、法治保障、科技支撑，目标是共建共治共享。"),
    ("生态文明", "生态文明建设处理人与自然关系，强调绿水青山就是金山银山，推动人与自然和谐共生。"),
    ("人与自然和谐共生", "人与自然和谐共生是中国式现代化的重要特征，要求发展不能以破坏生态环境为代价。"),
    ("绿水青山就是金山银山", "“绿水青山就是金山银山”说明生态环境本身就是生产力，保护生态就是保护发展潜力。"),
    ("国家安全", "国家安全是民族复兴的根基，社会稳定是国家强盛的前提。"),
    ("总体国家安全观", "总体国家安全观强调统筹发展和安全，统筹传统安全和非传统安全，构建大安全格局。"),
    ("政治安全", "政治安全是国家安全的根本，核心是政权安全和制度安全。"),
    ("人民安全", "人民安全是国家安全的宗旨，说明维护安全最终是为了保护人民利益。"),
    ("经济安全", "经济安全是国家安全的基础，关系产业链供应链、金融、粮食、能源等关键领域稳定。"),
    ("党对人民军队的绝对领导", "党对人民军队的绝对领导是人民军队的建军之本、强军之魂。"),
    ("听党指挥", "听党指挥是强军之魂，保证人民军队始终在党的绝对领导下行动。"),
    ("能打胜仗", "能打胜仗是强军之要，强调军队必须具备打赢现代战争的能力。"),
    ("作风优良", "作风优良是强军之基，体现人民军队的性质、宗旨和纪律优势。"),
    ("政治建军", "政治建军是人民军队建设的根本原则，突出党对军队的绝对领导和政治工作生命线地位。"),
    ("改革强军", "改革强军通过体制编制、力量结构和政策制度改革提升军队现代化水平。"),
    ("一国两制", "“一国两制”是在一个中国前提下，国家主体坚持社会主义，香港、澳门、台湾在统一后可以保持原有资本主义制度和生活方式长期不变。"),
    ("一个中国原则", "一个中国原则是两岸关系的政治基础，承认大陆和台湾同属一个中国。"),
    ("九二共识", "“九二共识”的核心是坚持一个中国原则，是两岸双方开展对话协商的重要政治基础。"),
    ("和平发展", "和平发展道路强调中国通过维护世界和平发展自己，又通过自身发展维护世界和平。"),
    ("合作共赢", "合作共赢主张各国在合作中兼顾彼此利益，反对零和博弈。"),
    ("人类命运共同体", "人类命运共同体主张各国命运相连，建设持久和平、普遍安全、共同繁荣、开放包容、清洁美丽的世界。"),
    ("推动构建人类命运共同体", "推动构建人类命运共同体是新时代中国外交的鲜明旗帜，体现中国对世界和平与发展的方案。"),
    ("推动中国与世界携手并进", "推动中国与世界携手并进强调中国发展离不开世界、世界发展也需要中国贡献，属于开放合作和胸怀天下的外交视角。"),
    ("跨越中等收入陷阱", "跨越中等收入陷阱属于发展质量问题，核心在转变发展方式、提高创新能力、扩大中等收入群体和推进共同富裕。"),
    ("一带一路", "“一带一路”是开放合作平台，重点在政策沟通、设施联通、贸易畅通、资金融通、民心相通。"),
    ("共商共建共享", "共商共建共享是全球治理观和“一带一路”建设的重要原则，强调各方共同参与、共同建设、共同受益。"),
    ("公正合理", "公正合理强调全球治理规则和秩序要体现公平正义，反对霸权和强权。"),
    ("互商互谅", "互商互谅强调通过协商沟通处理国际分歧，体现共商精神。"),
    ("同舟共济", "同舟共济强调面对全球性挑战时各国命运相连，需要合作应对。"),
    ("互利共赢", "互利共赢强调合作不能是一方获利，而要兼顾各方发展利益。"),
    ("自我净化", "自我净化强调清除党内不良因素和消极腐败现象，使党的肌体保持健康。"),
    ("自我完善", "自我完善强调补短板、强弱项，不断健全党的组织、制度和工作机制。"),
    ("自我革新", "自我革新强调以改革创新精神推进党的建设，破除不适应事业发展的思想和体制机制。"),
    ("自我提高", "自我提高强调提升党的领导能力、执政能力和拒腐防变能力。"),
    ("民法", "民法调整平等主体之间的人身关系和财产关系，是保护民事权利、规范民事活动的基本法律部门。"),
    ("刑法", "刑法规定犯罪和刑罚，用来惩治犯罪、保护国家和人民利益。"),
    ("行政诉讼法", "行政诉讼法规定公民、法人或者其他组织认为行政机关行为违法时，如何通过诉讼获得司法救济。"),
    ("团结联合", "团结联合是统一战线的重要功能，强调把不同阶层、群体和力量凝聚起来共同奋斗。"),
    ("工人阶级", "工人阶级是我国的领导阶级，中国共产党是中国工人阶级的先锋队，同时是中国人民和中华民族的先锋队。"),
    ("知识分子", "知识分子是工人阶级的一部分，是推动科技、教育、文化和现代化建设的重要力量。"),
    ("人民监督", "人民监督强调人民通过制度化渠道监督权力运行，防止权力脱离人民。"),
    ("社会主义制度", "社会主义制度以人民当家作主、公有制主体地位和共同富裕方向为重要特征。"),
    ("社会主义现代化", "社会主义现代化强调在社会主义制度基础上推进工业化、信息化、城镇化、农业现代化和国家治理现代化。"),
    ("历史方位", "历史方位指一个国家或事业所处的发展阶段和时代坐标；中国特色社会主义进入新时代，就是我国发展新的历史方位。"),
    ("十月革命", "十月革命把马克思列宁主义传播到中国，使中国先进分子看到通过社会主义道路实现民族解放的新希望。"),
    ("道路自信", "道路自信是对中国特色社会主义道路正确性和生命力的自信。"),
    ("理论自信", "理论自信是对中国特色社会主义理论体系科学性和指导力的自信。"),
    ("制度自信", "制度自信是对中国特色社会主义制度优势和治理效能的自信。"),
    ("文化自信", "文化自信是对中华优秀传统文化、革命文化和社会主义先进文化生命力的自信。"),
    ("独立自主", "独立自主是中华民族精神之魂，也是中国共产党立党立国的重要原则，强调中国的问题必须由中国人民自己作主张、自己来处理。"),
    ("团结奋斗", "团结奋斗是中国共产党和中国人民最显著的精神标识，强调把共同目标转化为共同努力。"),
    ("国家富强", "国家富强是中国梦的国家层面目标，强调综合国力和现代化水平提升。"),
    ("民族振兴", "民族振兴是中国梦的民族层面目标，强调中华民族从站起来、富起来走向强起来。"),
    ("人民幸福", "人民幸福是中国梦的人民层面目标，强调人民生活改善、权利保障和全面发展。"),
]

OPTION_CONTEXT_NOTES = {
    "前提": "在“一国两制”中，“一国”决定国家主权统一，是实行“两制”的前提；没有一个中国这个前提，就谈不上在同一国家内部实行两种制度。",
    "基础": "在“一国两制”中，“一国”规定国家主权和领土完整，是“两制”存在的基础；两种制度只能在一个中国框架内运行。",
    "条件": "“条件”只是一般说法，不能准确表达“一国”对“两制”的根本规定性。",
    "目标": "“目标”回答最终要达到什么结果，而“一国”在“一国两制”中回答的是制度成立的前提和基础。",
    "坚持真理": "伟大建党精神中的“坚持真理”指坚持马克思主义真理，保持理论信仰和政治方向。",
    "坚守理想": "伟大建党精神中的“坚守理想”指坚守共产主义远大理想和中国特色社会主义共同理想。",
    "践行初心": "伟大建党精神中的“践行初心”指把为中国人民谋幸福、为中华民族谋复兴落实到行动中。",
    "担当使命": "伟大建党精神中的“担当使命”指承担民族独立、人民解放、国家富强、人民幸福的历史任务。",
    "不怕牺牲": "伟大建党精神中的“不怕牺牲”体现共产党人为理想信念甘于付出的斗争品格。",
    "英勇斗争": "伟大建党精神中的“英勇斗争”体现面对困难、压迫和风险时敢于斗争、敢于胜利。",
    "对党忠诚": "伟大建党精神中的“对党忠诚”强调政治忠诚和组织忠诚。",
    "不负人民": "伟大建党精神中的“不负人民”强调党的一切奋斗都以人民利益为根本归宿。",
}


def clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def compact(text, limit=120):
    text = clean(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip("，。；、：,. ") + "..."


def option_text(option):
    return re.sub(r"^[A-Z][\.\u3001\uff0e]\s*", "", str(option.get("text", ""))).strip()


def selected_options(question):
    keys = set(str(question.get("answer", "")))
    return [option for option in question.get("options", []) if option.get("key") in keys]


def answer_phrase(question):
    if question["type"] not in ("single", "multi"):
        return str(question.get("answer", ""))
    return "、".join(option_text(option) for option in selected_options(question))


def strip_quotes(text):
    return clean(text).strip("“”\"' ")


def split_terms(text):
    text = strip_quotes(text)
    if not text:
        return []
    if re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日|\d+年", text):
        return [text]
    if "、" not in text and "；" not in text:
        return [text]
    parts = [part.strip() for part in re.split(r"[、；;]", text) if part.strip()]
    if len(parts) <= 1:
        return [text]
    return parts


def note_for_term(term, stem="", chapter=""):
    term = strip_quotes(term)
    stem = str(stem or "")
    if term in OPTION_CONTEXT_NOTES:
        return OPTION_CONTEXT_NOTES[term]
    if re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日", term):
        if term == "2021年7月1日" and "100周年" in stem:
            return "2021年7月1日对应庆祝中国共产党成立100周年大会，会上庄严宣告全面建成小康社会、历史性解决绝对贫困问题。"
        return f"{term}是时间节点，必须和原句中的会议、宣告或目标完成事件对应。"
    if re.fullmatch(r"\d+年", term):
        return f"{term}是时间长度或阶段节点，含义要和原句描述的历史进程对应。"
    if "、" in term or "；" in term:
        pieces = split_terms(term)
        if 1 < len(pieces) <= 10:
            notes = [note_for_term(piece, stem, chapter) for piece in pieces]
            return "；".join(notes)
    for needle, note in TERM_NOTES:
        plain_needle = strip_quotes(needle)
        if plain_needle and (plain_needle == term or plain_needle in term or term in plain_needle):
            return note
    match = re.match(r"坚持以(.+?)为(.+?)(加强|推进|推动|增强|走|打造|引领|维护|塑造)(.+)", term)
    if match:
        base, role, action, rest = match.groups()
        return f"{term}这类表述由三层组成：“以{base}为{role}”说明依据或定位，“{action}{rest}”说明具体任务。"
    if term.startswith("坚持"):
        return f"{term}是一条政治原则或工作要求，重点在“坚持”的对象本身，它规定相关工作的方向和边界。"
    if "制度" in term:
        return f"{term}属于制度安排，回答用什么制度保证治理和运行。"
    if "体系" in term:
        return f"{term}属于体系建设，强调多个环节、多个制度要素形成整体。"
    if "建设" in term:
        return f"{term}属于建设任务，回答要建成什么、朝什么方向推进。"
    if "发展" in term:
        return f"{term}属于发展类概念，回答发展方向、发展动力或发展目标。"
    return ""


def completed_sentence(question, phrase):
    stem = str(question.get("stem", ""))
    result = stem.replace("（ ）", phrase).replace("( )", phrase)
    result = result.replace("（  ）", phrase).replace("（   ）", phrase)
    return clean(result)


def option_line(question, option, selected, correct_phrase):
    key = option["key"]
    text = option_text(option)
    note = note_for_term(text, question["stem"], question["chapter"])
    if key in selected:
        prefix = "应选" if question["type"] == "single" else "选"
        return f"- {key}：{prefix}。{note}" if note else f"- {key}：{prefix}。{text}就是这句知识点中的答案。"
    if re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日|\d+年", text):
        return f"- {key}：不选。{note}本题原句对应的是“{correct_phrase}”。"
    return f"- {key}：不选。{note}" if note else f"- {key}：不选。{text}不是这句知识点中的答案。"


def rewrite_choice(question):
    answer = "".join(sorted(set(str(question["answer"])), key="ABCDEFGHIJKLMNOPQRSTUVWXYZ".index))
    question["answer"] = answer
    phrase = answer_phrase(question)
    completed = completed_sentence(question, phrase)
    note = note_for_term(phrase, question["stem"], question["chapter"])
    selected = set(answer)

    quick = [
        f"知识点：{completed}",
        "选项辨析：",
    ]
    if note:
        quick.insert(1, note)
    for option in question.get("options", []):
        quick.append(option_line(question, option, selected, phrase))

    detail = [
        "知识点详解：",
        f"完整命题：{completed}",
    ]
    if note:
        detail.append(f"概念含义：{note}")
    wrong_options = [option for option in question.get("options", []) if option["key"] not in selected]
    if wrong_options:
        explained_wrong_options = [
            option for option in wrong_options
            if note_for_term(option_text(option), question["stem"], question["chapter"])
        ]
        if explained_wrong_options:
            detail.append("易混辨析：")
        for option in explained_wrong_options:
            text = option_text(option)
            detail.append(f"- {text}：{note_for_term(text, question['stem'], question['chapter'])}")
    else:
        detail.append("并列要点：")
        for term in split_terms(phrase):
            detail.append(f"- {term}：{note_for_term(term, question['stem'], question['chapter'])}")

    question["quickExplanation"] = "\n".join(quick)
    question["knowledgeDetail"] = "\n".join(detail)
    question["explanation"] = f"【快速做题】\n{question['quickExplanation']}\n\n【知识点详解】\n{question['knowledgeDetail']}"


def split_essay_points(answer):
    answer = clean(answer)
    if not answer:
        return []
    parts = [part.strip(" 。；") for part in re.split(r"[；;]\s*", answer) if part.strip(" 。；")]
    if len(parts) <= 1:
        parts = [part.strip(" 。") for part in re.split(r"(?<=[。])", answer) if part.strip(" 。")]
    return parts or [answer]


def point_explanation(point):
    point = clean(point)
    match = re.match(r"坚持以(.+?)为(.+?)(加强|推进|推动|增强|走|打造|引领|维护|塑造)(.+)", point)
    if match:
        base, role, action, rest = match.groups()
        return f"{point}：其中“{base}”是依据或着力点，“{role}”说明这一点的定位，“{action}{rest}”是要完成的任务。"
    if "是" in point and len(point) <= 80:
        left, right = point.split("是", 1)
        return f"{point}：这句话把“{left}”和“{right}”直接对应起来，是需要记住的判断句。"
    terms = split_terms(point)
    if len(terms) > 1 and len(terms) <= 8:
        return f"{point}：这一点由{len(terms)}个并列关键词构成，分别是{', '.join(terms)}。"
    return f"{point}。"


def rewrite_essay(question):
    points = split_essay_points(question.get("answer", ""))
    quick = [
        f"知识点：{question['stem']}共有 {len(points)} 个要点。",
        "要点展开：",
    ]
    for index, point in enumerate(points, 1):
        quick.append(f"{index}. {point}。")

    detail = [
        "知识点详解：",
    ]
    for index, point in enumerate(points, 1):
        detail.append(f"{index}. {point_explanation(point)}")

    question["quickExplanation"] = "\n".join(quick)
    question["knowledgeDetail"] = "\n".join(detail)
    question["explanation"] = f"【快速做题】\n{question['quickExplanation']}\n\n【知识点详解】\n{question['knowledgeDetail']}"


def validate(questions):
    issues = []
    ids = [question["id"] for question in questions]
    if ids != list(range(1, len(questions) + 1)):
        issues.append("id 不连续")
    labels = Counter(question["label"] for question in questions)
    for label, count in labels.items():
        if count > 1:
            issues.append(f"重复 label: {label}")
    for question in questions:
        text = json.dumps(question, ensure_ascii=False)
        if "�" in text or "????" in text:
            issues.append(f"{question['label']} 存在乱码")
        body = question.get("quickExplanation", "") + "\n" + question.get("knowledgeDetail", "")
        for phrase in BANNED_PHRASES:
            if phrase in body:
                issues.append(f"{question['label']} 命中禁用短语: {phrase}")
        if "知识点：" not in question.get("quickExplanation", ""):
            issues.append(f"{question['label']} 缺少知识点")
        if question["type"] in ("single", "multi"):
            keys = {option["key"] for option in question.get("options", [])}
            if any(key not in keys for key in question["answer"]):
                issues.append(f"{question['label']} 答案不在选项内")
            for option in question.get("options", []):
                if f"- {option['key']}：" not in question.get("quickExplanation", ""):
                    issues.append(f"{question['label']} 缺少选项 {option['key']} 辨析")
            for line in question.get("quickExplanation", "").splitlines():
                if re.fullmatch(r"- [A-Z]：(不选|应选|选)。", line.strip()):
                    issues.append(f"{question['label']} 选项辨析为空: {line.strip()}")
    return issues


def repeated_line_report(questions):
    counter = Counter()
    for question in questions:
        for line in question.get("quickExplanation", "").splitlines():
            line = clean(line)
            if len(line) >= 22:
                counter[line] += 1
    return [(line, count) for line, count in counter.most_common(20) if count > 3]


def write_report(questions, issues, output):
    type_counts = Counter(question["typeName"] for question in questions)
    chapter_counts = Counter(question["chapter"] for question in questions)
    repeated = repeated_line_report(questions)
    samples = ["习-单-001", "习-单-004", "习-单-050", "习-单-154", "习-多-100", "习-多-129", "习-简-030"]
    by_label = {question["label"]: question for question in questions}
    lines = [
        "# 习近平思想知识点型解析修复报告",
        "",
        "## 修复口径",
        "",
        "- 删除 `答题抓手`、`复习抓手`、`题眼`、`绑定`、`层级不对` 等提醒式话术。",
        "- 黄色高亮开头改为 `知识点：`，直接给完整命题和概念含义。",
        "- 选择题保留选项辨析，但每项尽量说明概念本身，不再反复说“关注题干”。",
        "- 简答题按答案要点展开，并给每个要点的含义说明。",
        "",
        "## 质检结果",
        "",
        f"- 题量：{len(questions)}",
        f"- 题型：{dict(type_counts)}",
        f"- 章节数：{len(chapter_counts)}",
        f"- 问题数：{len(issues)}",
        f"- 重复长句数：{len(repeated)}",
    ]
    if repeated:
        lines.append("")
        lines.append("## 仍有重复长句")
        for line, count in repeated[:20]:
            lines.append(f"- {count} 次：{line}")
    if issues:
        lines.append("")
        lines.append("## 问题")
        for issue in issues[:100]:
            lines.append(f"- {issue}")
    lines.append("")
    lines.append("## 样例")
    for label in samples:
        question = by_label.get(label)
        if not question:
            continue
        lines.extend([
            "",
            f"### {label}",
            "",
            question["stem"],
            "",
            question["quickExplanation"],
        ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(QUESTIONS_PATH))
    parser.add_argument("--output", default=str(QUESTIONS_PATH))
    parser.add_argument("--report", default=str(REPORT_PATH))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    questions = json.loads(Path(args.input).read_text(encoding="utf-8"))
    for question in questions:
        if question["type"] in ("single", "multi"):
            rewrite_choice(question)
        elif question["type"] == "essay":
            rewrite_essay(question)

    issues = validate(questions)
    write_report(questions, issues, Path(args.report))
    if issues:
        raise SystemExit("Validation failed: " + "; ".join(issues[:10]))
    if not args.check:
        Path(args.output).write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"questions={len(questions)} issues={len(issues)} report={args.report}")


if __name__ == "__main__":
    main()
