import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from app.models.enums import ScenarioDifficulty, ScenarioLanguage
from app.schemas.report import SessionReport


class AuthenticateMessage(BaseModel):
    type: Literal["authenticate"]
    token: str = Field(min_length=1, max_length=4096)


class StartSessionMessage(BaseModel):
    type: Literal["start_session"]
    scenario_id: uuid.UUID
    difficulty: ScenarioDifficulty | None = None


class TextMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: Literal["text_message"]
    content: str = Field(min_length=1, max_length=4000)


class EndSessionMessage(BaseModel):
    type: Literal["end_session"]


ChatCommand = Annotated[
    StartSessionMessage | TextMessage | EndSessionMessage,
    Field(discriminator="type"),
]
chat_command_adapter: TypeAdapter[ChatCommand] = TypeAdapter(ChatCommand)


class AuthenticatedEvent(BaseModel):
    type: Literal["authenticated"] = "authenticated"
    user_id: uuid.UUID


class SessionStartedEvent(BaseModel):
    type: Literal["session_started"] = "session_started"
    session_id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_title: str
    language: ScenarioLanguage
    difficulty: ScenarioDifficulty
    started_at: datetime


class AiResponseEvent(BaseModel):
    type: Literal["ai_response"] = "ai_response"
    message_id: uuid.UUID
    content: str
    created_at: datetime
    degraded: bool = False


class ChatCorrection(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    original: str = Field(min_length=1, max_length=4000)
    corrected: str = Field(min_length=1, max_length=4000)
    severity: Literal["minor", "major"]
    explanation: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def require_actual_change(self) -> "ChatCorrection":
        if self.original == self.corrected:
            raise ValueError("纠错前后内容不能相同")
        return self


class ChatTurnOutput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reply: str = Field(min_length=1, max_length=4000)
    correction: ChatCorrection | None = None


class CorrectionEvent(ChatCorrection):
    type: Literal["correction"] = "correction"
    message_id: uuid.UUID


class SessionEndedEvent(BaseModel):
    type: Literal["session_ended"] = "session_ended"
    session_id: uuid.UUID
    duration_seconds: int
    ended_at: datetime


class ReportGeneratingEvent(BaseModel):
    type: Literal["report_generating"] = "report_generating"
    session_id: uuid.UUID


class SessionReportEvent(BaseModel):
    type: Literal["session_report"] = "session_report"
    session_id: uuid.UUID
    report: SessionReport


class ChatErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    recoverable: bool = True
