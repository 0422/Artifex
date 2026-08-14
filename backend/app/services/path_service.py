"""Path 模块业务逻辑（P0-5 基础学习路径生成）。

子模块（对应技术架构 §3.2.6）：
  Onboarding Engine → Starting Point Analyzer → Path Generator → Adaptive Adjuster
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai import llm
from app.models.enums import Domain, LearningPathStatus, PathMilestoneStatus
from app.models.path import LearningPath, PathMilestone
from app.models.user import UserProfile
from app.schemas.path import OnboardingQuestion

# 5 分钟引导的固定问题集（Onboarding Engine）
ONBOARDING_QUESTIONS: list[OnboardingQuestion] = [
    OnboardingQuestion(key="domain", question="你想学习哪个领域？", hint="外语 / 人文社科 / 技能"),
    OnboardingQuestion(key="goal", question="你的学习目标是什么？", hint="例如：日语 N3、读懂政治哲学原著、弹会一首曲子"),
    OnboardingQuestion(key="level", question="你目前的水平如何？", hint="零基础 / 入门 / 中级 / 进阶"),
    OnboardingQuestion(key="daily_minutes", question="每天大概能投入多少分钟？", hint="例如：20 分钟"),
    OnboardingQuestion(key="motivation", question="是什么驱动你学习这个？", hint="兴趣 / 工作 / 考试 / 其他"),
]


def get_onboarding_questions() -> list[OnboardingQuestion]:
    return ONBOARDING_QUESTIONS


async def complete_onboarding(
    db: AsyncSession,
    user_id: uuid.UUID,
    domain: Domain,
    answers: dict,
) -> LearningPath:
    """完成引导：调 LLM 生成起点报告 + 初始路径，落库，并标记 onboarding_completed。"""
    # 把 domain 也带进 LLM 输入
    payload = {"domain": domain.value, **answers}
    result = await llm.generate_learning_path(payload)

    report = result.get("starting_point_report", {})
    path_data = result.get("path", {})

    path = LearningPath(
        user_id=user_id,
        domain=domain,
        title=path_data.get("title", "我的学习路径"),
        starting_point_report=report,
        status=LearningPathStatus.ACTIVE,
    )
    db.add(path)
    await db.flush()

    milestones = path_data.get("milestones", [])
    for idx, m in enumerate(milestones):
        title = (m.get("title") or "").strip()
        if not title:
            continue
        # 第一个里程碑设为 current，其余 locked
        status = PathMilestoneStatus.CURRENT if idx == 0 else PathMilestoneStatus.LOCKED
        db.add(
            PathMilestone(
                path_id=path.id,
                order_index=idx,
                title=title,
                description=(m.get("description") or "").strip(),
                status=status,
            )
        )

    # 标记该用户已完成引导
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = profile_result.scalar_one_or_none()
    if profile is not None:
        profile.onboarding_completed = True

    await db.commit()
    return await get_path_by_id(db, path.id)


async def get_path_by_id(db: AsyncSession, path_id: uuid.UUID) -> LearningPath | None:
    stmt = (
        select(LearningPath)
        .where(LearningPath.id == path_id)
        .options(selectinload(LearningPath.milestones))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_current_path(db: AsyncSession, user_id: uuid.UUID) -> LearningPath | None:
    """返回用户最新的 active 路径。"""
    stmt = (
        select(LearningPath)
        .where(LearningPath.user_id == user_id)
        .where(LearningPath.status == LearningPathStatus.ACTIVE)
        .options(selectinload(LearningPath.milestones))
        .order_by(LearningPath.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
