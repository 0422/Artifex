from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReportText = Annotated[str, Field(min_length=1, max_length=2000)]


class WeakPoint(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: Literal["vocabulary", "grammar", "expression", "pragmatics"]
    tag: str = Field(pattern=r"^(vocab|grammar|expression|pragmatics):[a-z0-9_-]+$")
    description: str = Field(min_length=1, max_length=1000)
    example: str = Field(min_length=1, max_length=1000)
    suggestion: str = Field(min_length=1, max_length=1000)


class SessionReportOutput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    summary: str = Field(min_length=1, max_length=3000)
    weak_points: list[WeakPoint] = Field(default_factory=list, max_length=5)
    suggestions: list[ReportText] = Field(min_length=1, max_length=5)
    performance_score: int = Field(ge=0, le=100)
    no_prominent_issues: bool = False

    @model_validator(mode="after")
    def normalize_issue_flag(self) -> "SessionReportOutput":
        if len(self.weak_points) < 3:
            self.no_prominent_issues = True
        return self


class SessionReport(BaseModel):
    summary: str
    weak_points: list[WeakPoint] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    performance_score: int | None = Field(default=None, ge=0, le=100)
    no_prominent_issues: bool = False
    degraded: bool = False
    insufficient_data: bool = False
