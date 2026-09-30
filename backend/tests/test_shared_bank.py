"""全局共享库的可见性与只读保护测试。

雅思口语真题以 user_id=None 的行存放，所有用户可见但不可改；
用户自建场景仍只对自己可见。这里守住两条边界：
  1. 不能把别人的私有场景漏给自己
  2. 不能让自己改到官方共享内容
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.elements import BindParameter, BooleanClauseList
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScenarioDifficulty, ScenarioLanguage
from app.models.knowledge import KnowledgeCategory
from app.schemas.scenario import ScenarioUpdate
from app.services import knowledge_service, scenario_service


def flatten(clause) -> list:
    """把嵌套的 AND/OR 条件树摊平为叶子列表，便于结构化断言。"""
    if isinstance(clause, BooleanClauseList):
        leaves: list = []
        for inner in clause.clauses:
            leaves.extend(flatten(inner))
        return leaves
    return [clause]


def has_null_check(clause) -> bool:
    """条件里是否存在 ``user_id IS NULL``（官方共享行）。"""
    return any(
        getattr(leaf, "operator", None).__name__ == "is_" or "IS NULL" in str(leaf)
        for leaf in flatten(clause)
    )


def bind_values(clause) -> list:
    """取出条件树里所有绑定参数的值。

    2026-09-30 之前的写法是比对 leaf.operator.__name__ == 'eq' 再读 leaf.right.value，
    实测不可靠（whereclause 经过 SQLAlchemy 包装后 right 不一定是 BindParameter）。
    直接收集 BindParameter 的值最稳，也能覆盖 == 与 IN 等多种比较。
    """
    return [
        leaf.value
        for leaf in flatten(clause)
        if isinstance(leaf, BindParameter)
    ]


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def make_scenario(*, shared: bool, user_id=None, **overrides) -> SimpleNamespace:
    """构造一个够用的场景桩对象；categories 预置为 list 以免 lazy load。"""
    fields = dict(
        id=uuid.uuid4(),
        user_id=None if shared else user_id,
        title=overrides.pop("title", "真题"),
        description="一行一题\n第二题",
        language=ScenarioLanguage.EN,
        difficulty=ScenarioDifficulty.B1,
        domain="language",
        scenario_mode="guided_discussion",
        estimated_minutes=None,
        tags=[],
        ielts_part=1,
        cue_card=None,
        is_active=True,
        categories=[],
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


# ---------------------------------------------------------------------------
# 可见性条件
# ---------------------------------------------------------------------------


def test_visible_scenarios_covers_shared_and_own() -> None:
    """条件必须同时覆盖官方共享与本人私有，两项都不能少。"""
    mine = uuid.uuid4()
    clause = scenario_service._visible_scenarios(mine)

    assert has_null_check(clause), "缺少 user_id IS NULL（共享行会被漏掉）"
    assert mine in bind_values(clause), "缺少本人归属条件"


def test_visible_categories_covers_shared() -> None:
    clause = scenario_service._visible_categories(uuid.uuid4())
    assert has_null_check(clause)


@pytest.mark.asyncio
async def test_list_scenarios_where_clause_excludes_other_users(db: MagicMock) -> None:
    """list_scenarios 的 WHERE 必须是「本人 or NULL」，不能是全表。"""
    mine = uuid.uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    await scenario_service.list_scenarios(db, mine)

    stmt = db.execute.await_args.args[0]
    assert has_null_check(stmt.whereclause), "共享真题取不到"
    assert mine in bind_values(stmt.whereclause), "本人私有场景取不到"
    # 条件里只应出现本人的 id，不能把别人的 id 带进来
    assert [v for v in bind_values(stmt.whereclause) if v != mine] == []


# ---------------------------------------------------------------------------
# 递归取题：点「Part 1」要带出底下所有类别的真题
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_category_descendants_include_shared_subcategories(
    db: MagicMock,
) -> None:
    """雅思三级树里 Part 1 和它的类别全是共享行，递归必须带上它们。"""
    user_id = uuid.uuid4()
    ielts_root = uuid.uuid4()
    part1 = uuid.uuid4()
    leaf = uuid.uuid4()

    result = MagicMock()
    result.all.return_value = [
        (ielts_root, None),   # 雅思口语（共享）
        (part1, ielts_root),  # Part 1（共享）
        (leaf, part1),        # 个人喜好类（共享）
        (uuid.uuid4(), None),  # 语言（本人）
    ]
    db.execute = AsyncMock(return_value=result)

    ids = await scenario_service._category_and_descendant_ids(db, ielts_root, user_id)

    assert part1 in ids and leaf in ids


# ---------------------------------------------------------------------------
# 写保护：共享行只读
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_scenario_rejects_shared(db: MagicMock) -> None:
    shared = make_scenario(shared=True)
    payload = ScenarioUpdate(title="我想改官方题名")

    with pytest.raises(scenario_service.SharedReadOnlyError):
        await scenario_service.update_scenario(db, shared, payload)

    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_scenario_rejects_shared(db: MagicMock) -> None:
    shared = make_scenario(shared=True)

    with pytest.raises(scenario_service.SharedReadOnlyError):
        await scenario_service.deactivate_scenario(db, shared)

    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_scenario_allows_own(db: MagicMock) -> None:
    mine = make_scenario(shared=False, user_id=uuid.uuid4())

    await scenario_service.deactivate_scenario(db, mine)

    assert mine.is_active is False
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_scenario_allows_own(db: MagicMock) -> None:
    me = uuid.uuid4()
    mine = make_scenario(shared=False, user_id=me)
    # 必须用真实 ORM 对象：scenario.categories 赋值会触发 backref 事件，
    # SimpleNamespace 没有 _sa_instance_state 会直接 AttributeError
    category = KnowledgeCategory(id=uuid.uuid4(), name="个人喜好类", is_active=True)

    result = MagicMock()
    result.scalars.return_value.all.return_value = [category]
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    # category_ids 必须真的传：不传时 service 不会碰 categories，也就无从验证挂载
    payload = ScenarioUpdate(ielts_part=2, cue_card="You should say: ...", category_ids=[category.id])

    await scenario_service.update_scenario(db, mine, payload)

    assert mine.ielts_part == 2
    assert mine.cue_card == "You should say: ..."
    assert mine.categories == [category]


@pytest.mark.asyncio
async def test_archive_category_rejects_shared(db: MagicMock) -> None:
    shared = SimpleNamespace(id=uuid.uuid4(), user_id=None, is_active=True)

    with pytest.raises(knowledge_service.SharedReadOnlyError):
        await knowledge_service.archive_category(db, shared)

    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_archive_category_cascades_to_descendants(db: MagicMock) -> None:
    """只归档根会让子分类浮到侧边栏顶层，必须整棵子树一起归档。"""
    root_id = uuid.uuid4()
    part1_id = uuid.uuid4()
    leaf_id = uuid.uuid4()
    mine = uuid.uuid4()

    root = SimpleNamespace(id=root_id, user_id=mine, is_active=True, parent_id=None)
    part1 = SimpleNamespace(id=part1_id, user_id=mine, is_active=True, parent_id=root_id)
    leaf = SimpleNamespace(id=leaf_id, user_id=mine, is_active=True, parent_id=part1_id)

    # BFS 每一层查一次子节点：第 1 次 root→part1，第 2 次 part1→leaf，第 3 次空
    levels = [[part1], [leaf], []]

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalars.return_value.all.return_value = (
            levels[fake_execute.calls] if fake_execute.calls < len(levels) else []
        )
        fake_execute.calls += 1  # type: ignore[attr-defined]
        return result

    fake_execute.calls = 0  # type: ignore[attr-defined]
    db.execute = AsyncMock(side_effect=fake_execute)

    await knowledge_service.archive_category(db, root)

    assert root.is_active is False
    assert part1.is_active is False and leaf.is_active is False
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_archive_category_leaves_shared_children_alone(db: MagicMock) -> None:
    """用户自建分类下若挂着官方共享子节点，不该被连带归档。"""
    root_id = uuid.uuid4()
    shared_child_id = uuid.uuid4()
    mine = uuid.uuid4()

    root = SimpleNamespace(id=root_id, user_id=mine, is_active=True, parent_id=None)
    shared_child = SimpleNamespace(
        id=shared_child_id, user_id=None, is_active=True, parent_id=root_id
    )

    async def fake_execute(stmt):
        result = MagicMock()
        result.scalars.return_value.all.return_value = [shared_child]
        return result

    db.execute = AsyncMock(side_effect=fake_execute)

    await knowledge_service.archive_category(db, root)

    assert root.is_active is False
    # 官方共享节点保持 active，不能被普通用户删掉
    assert shared_child.is_active is True


@pytest.mark.asyncio
async def test_update_category_rejects_shared(db: MagicMock) -> None:
    shared = SimpleNamespace(id=uuid.uuid4(), user_id=None)
    payload = knowledge_service.KnowledgeCategoryUpdate(name="想改名")

    with pytest.raises(knowledge_service.SharedReadOnlyError):
        await knowledge_service.update_category(db, shared, payload)

    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# 在共享分类下自建场景：这是要被允许的行为
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_scenario_can_link_to_shared_category(db: MagicMock) -> None:
    """用户把一个自建场景挂到官方共享的「个人喜好类」下，必须成功。"""
    from app.models.enums import ScenarioLanguage

    user_id = uuid.uuid4()
    # 2026-09-30 必须用真实 ORM 对象：给 scenario.categories 赋值会触发
    # backref 事件，SimpleNamespace 缺 _sa_instance_state 会炸
    shared_category = KnowledgeCategory(id=uuid.uuid4(), name="个人喜好类", is_active=True)

    result = MagicMock()
    result.scalars.return_value.all.return_value = [shared_category]
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    payload = SimpleNamespace(
        model_dump=lambda: {
            "title": "我的薄弱点",
            "description": "我老是把时态搞混",
            "language": ScenarioLanguage.EN,
            "difficulty": ScenarioDifficulty.B1,
            "domain": "language",
            "scenario_mode": "guided_discussion",
            "estimated_minutes": None,
            "tags": [],
            "ielts_part": 1,
            "cue_card": None,
            "category_ids": [shared_category.id],
        }
    )

    await scenario_service.create_scenario(db, user_id, payload)

    # 场景归属本人，挂在共享分类下
    added = db.add.call_args.args[0]
    assert added.user_id == user_id
    assert added.categories == [shared_category]
