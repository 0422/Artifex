import enum


class Domain(str, enum.Enum):
    LANGUAGE = "language"
    HUMANITIES = "humanities"
    SKILL = "skill"


class CardType(str, enum.Enum):
    VOCABULARY = "vocabulary"
    CONCEPT = "concept"
    TECHNIQUE = "technique"


class CaptureSourceType(str, enum.Enum):
    TEXT = "text"
    URL = "url"
    PDF = "pdf"


class CaptureStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConceptRelationType(str, enum.Enum):
    PREREQUISITE = "prerequisite"
    ANALOGY = "analogy"
    CONTRAST = "contrast"
    EXTENDS = "extends"


class ChatSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class ChatMessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class LearningEventType(str, enum.Enum):
    CARD_REVIEW = "card_review"
    CONCEPT_DISCOVERY = "concept_discovery"
    CONVERSATION_PRACTICE = "conversation_practice"
    OUTPUT_CHALLENGE = "output_challenge"


class LearningPathStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PathMilestoneStatus(str, enum.Enum):
    COMPLETED = "completed"
    CURRENT = "current"
    LOCKED = "locked"
