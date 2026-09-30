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


def test_build_category_tree_preserves_user_id() -> None:
    """2026-09-30 user_id 必须带进 dict。

    KnowledgeCategoryRead 靠它派生 is_shared；漏了它 Pydantic 会拿到 None，
    把所有分类都误判成官方共享，导致右键菜单和删除按钮对全部节点静默失效。
    """
    owner = uuid.uuid4()
    mine = category("我的分类", None)
    mine.user_id = owner
    shared = category("雅思口语", None)
    shared.user_id = None

    tree = build_category_tree([mine, shared])

    by_name = {node["name"]: node for node in tree}
    assert by_name["我的分类"]["user_id"] == owner
    assert by_name["雅思口语"]["user_id"] is None

    # 走一遍 schema，确认 is_shared 派生前依据 user_id 而非默认值
    from app.schemas.knowledge import KnowledgeCategoryTree

    validated = [KnowledgeCategoryTree.model_validate(node) for node in tree]
    shared_flag = {node.name: node.is_shared for node in validated}
    assert shared_flag["我的分类"] is False
    assert shared_flag["雅思口语"] is True
