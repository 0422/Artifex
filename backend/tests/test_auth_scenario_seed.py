from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserProfile
from app.schemas.auth import RegisterRequest
from app.services import auth_service


@pytest.mark.asyncio
async def test_register_user_no_longer_creates_default_scenarios() -> None:
    """2026-09-30 注册不再预置默认场景。

    场景改由知识库统一承载（雅思共享真题库 + 用户自建），
    对话页初始为空由用户自己选。此测试守住这条，防止默认场景回归。
    """
    db = MagicMock(spec=AsyncSession)
    payload = RegisterRequest(
        email="new-user@example.com",
        password="password123",
        nickname="New User",
    )

    with (
        patch.object(auth_service, "get_user_by_email", AsyncMock(return_value=None)),
        patch.object(auth_service, "hash_password", return_value="hashed"),
    ):
        user = await auth_service.register_user(db, payload)

    # 只写 User 与 UserProfile 两条，不再追加任何 ScenarioCard
    assert db.add.call_count == 2
    written = [item.args[0] for item in db.add.call_args_list]
    assert any(isinstance(item, User) for item in written)
    assert any(isinstance(item, UserProfile) for item in written)
    assert not any(type(item).__name__ == "ScenarioCard" for item in written)

    assert user.email == payload.email
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(user)


def test_scenario_service_no_longer_exposes_seed_helpers() -> None:
    """SEED_SCENARIOS / create_seed_scenarios 已注释移除，不应再对外暴露。"""
    from app.services import scenario_service

    assert not hasattr(scenario_service, "SEED_SCENARIOS")
    assert not hasattr(scenario_service, "create_seed_scenarios")
