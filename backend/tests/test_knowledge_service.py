import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.services.knowledge_service import build_category_tree


def category(name: str, parent_id: uuid.UUID | None = None):
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        parent_id=parent_id,
        domain="history",
        description=None,
        sort_order=0,
        is_active=True,
        created_at=now,
        updated_at=now,
        scenarios=[],
    )


def test_build_category_tree_keeps_arbitrary_depth() -> None:
    root = category("历史")
    dynasty = category("宋代", root.id)
    topic = category("政策", dynasty.id)

    tree = build_category_tree([root, dynasty, topic])

    assert tree[0]["name"] == "历史"
    assert tree[0]["children"][0]["name"] == "宋代"
    assert tree[0]["children"][0]["children"][0]["name"] == "政策"
