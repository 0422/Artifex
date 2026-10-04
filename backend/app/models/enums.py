import enum


class Domain(str, enum.Enum):
    LANGUAGE = "language"
    HUMANITIES = "humanities"
    SKILL = "skill"


class CardType(str, enum.Enum):
    VOCABULARY = "vocabulary"
    CONCEPT = "concept"
    TECHNIQUE = "technique"


# 2026-10-01 内容捕获/知识图谱/学习路径功能下线，
# CaptureSourceType、CaptureStatus、ConceptRelationType、
# LearningPathStatus、PathMilestoneStatus 五个枚举随模型一并删除


class ChatSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class ChatMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ScenarioLanguage(str, enum.Enum):
    EN = "en"
    JA = "ja"
    ZH = "zh"


class ScenarioDifficulty(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"
    N5 = "N5"
    N4 = "N4"
    N3 = "N3"
    N2 = "N2"
    N1 = "N1"


class LearningEventType(str, enum.Enum):
    CARD_REVIEW = "card_review"
    CONCEPT_DISCOVERY = "concept_discovery"
    CONVERSATION_PRACTICE = "conversation_practice"
    OUTPUT_CHALLENGE = "output_challenge"


# 2026-09-30 新增边缘设备管理模块：设备在线状态。unknown = 档案刚建、尚未扫描过。
class EdgeDeviceStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


# 2026-09-30 新增边缘设备管理模块：OTA 任务生命周期。canceled 由用户手动取消，
# failed 覆盖设备不支持 OTA / 设备不可达 / 校验不通过等各类失败。
class EdgeOtaTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


# 2026-10-03 新增世势洞察（M6）模块：新闻板块划分，news_sources / news_articles /
# news_digests 三张表共用。新增板块时在此追加即可；列上用的是 native_enum=False
# 的 varchar，不需要动 PG 枚举类型。
class NewsDomain(str, enum.Enum):
    AI = "ai"
    TECH = "tech"
    FINANCE = "finance"
    EDUCATION = "education"
    WORLD = "world"
    GENERAL = "general"


# 2026-10-03 新增摘星阁（M7）模块：星星的来源。manual=页面手写、import=批量导入，
# 这两个是 v1 实际会写入的值；news/chat 为跨模块转存预留（世势洞察日报、
# 情境对话消息「存为星」），列上是普通 varchar，新增来源不改表结构。
class StarSource(str, enum.Enum):
    MANUAL = "manual"
    IMPORT = "import"
    NEWS = "news"
    CHAT = "chat"


# 2026-10-03 新增摘星阁（M7）模块：时间范围筛选。
# 边界按固定 UTC+8 计算（与 news_service.FIXED_TZ 同一约定，避免 Windows 上
# zoneinfo 缺 tz 数据库抛错），earlier 表示「早于 30 天」的沉底老星。
class StarRange(str, enum.Enum):
    ALL = "all"
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    EARLIER = "earlier"


# 2026-10-03 新增摘星阁（M7）模块：星图排序。
# recent    新收录的在前（默认）。写下来的那一刻离得最近，先看见刚抓的念头。
# revisited 最近"回味"过的在前。last_grabbed_at 为空（从没被抓过）的沉到最后，
#           顺序为 NULLS LAST——PG 里 desc 默认把 NULL 排最前，那会让从没读过的星
#           霸占整个"最常回味"视图，与这个排序想解决的问题正好相反。
class StarSort(str, enum.Enum):
    RECENT = "recent"
    REVISITED = "revisited"
