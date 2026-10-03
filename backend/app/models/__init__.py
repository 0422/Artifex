from app.core.database import Base
from app.models.card import Card, ReviewLog
from app.models.chat import ChatMessage, ChatSession
from app.models.digital_human import DigitalHumanConfig
# 2026-09-30 新增边缘设备管理模块的模型，需在此注册，否则 alembic autogenerate 会漏表
from app.models.edge_device import EdgeDevice, EdgeFirmware, EdgeOtaTask
from app.models.event import LearningEvent
from app.models.knowledge import KnowledgeCategory
# 2026-10-03 新增世势洞察（M6）模块的模型，需在此注册，否则 alembic autogenerate 会漏表
from app.models.news import NewsArticle, NewsDigest, NewsSource
from app.models.scenario import ScenarioCard
from app.models.user import User, UserProfile

__all__ = [
    "Base",
    "Card",
    "ChatMessage",
    "ChatSession",
    "DigitalHumanConfig",
    "EdgeDevice",
    "EdgeFirmware",
    "EdgeOtaTask",
    "LearningEvent",
    "KnowledgeCategory",
    "NewsArticle",
    "NewsDigest",
    "NewsSource",
    "ReviewLog",
    "ScenarioCard",
    "User",
    "UserProfile",
]
