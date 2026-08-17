from app.schemas.report import SessionReportOutput


def test_report_with_fewer_than_three_weak_points_marks_no_prominent_issues() -> None:
    report = SessionReportOutput.model_validate(
        {
            "summary": "完成了点餐练习。",
            "weak_points": [
                {
                    "category": "grammar",
                    "tag": "grammar:counter-cups",
                    "description": "饮料量词使用不准确。",
                    "example": "水を一つください。",
                    "suggestion": "练习杯、瓶等饮料量词。",
                }
            ],
            "suggestions": ["继续完成两轮点餐练习。"],
            "performance_score": 80,
            "no_prominent_issues": False,
        }
    )

    assert report.no_prominent_issues is True


def test_report_accepts_stable_ascii_aggregation_tag() -> None:
    report = SessionReportOutput.model_validate(
        {
            "summary": "表达完整。",
            "weak_points": [],
            "suggestions": ["保持练习。"],
            "performance_score": 90,
        }
    )

    assert report.performance_score == 90
