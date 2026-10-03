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
