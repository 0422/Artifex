from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import RegisterRequest
from app.services import auth_service


@pytest.mark.asyncio
async def test_register_user_creates_seed_scenarios_in_same_transaction() -> None:
    db = MagicMock(spec=AsyncSession)
    payload = RegisterRequest(
        email="new-user@example.com",
        password="password123",
        nickname="New User",
    )

    with (
        patch.object(auth_service, "get_user_by_email", AsyncMock(return_value=None)),
        patch.object(auth_service, "hash_password", return_value="hashed"),
        patch.object(
            auth_service, "create_seed_scenarios", AsyncMock()
        ) as create_seeds,
    ):
        user = await auth_service.register_user(db, payload)

    create_seeds.assert_awaited_once_with(db, user.id)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(user)
