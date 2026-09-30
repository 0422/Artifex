import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import KnowledgeCategory
from app.models.scenario import ScenarioCard
from app.schemas.knowledge import KnowledgeCategoryCreate, KnowledgeCategoryUpdate

DEFAULT_CATEGORY_TREE = (
    ("语言", "language", ("英语", "日语", "韩语")),
    ("历史", "history", ("中国古代", "中国近现代", "世界历史")),
    ("政治", "politics", ("政治制度", "政治思想", "国际关系")),
    ("艺术", "art", ("绘画", "建筑", "表演艺术")),
    ("电影", "film", ("类型研究", "导演与作品", "视听语言")),
)


# 2026-09-30 雅思口语真题库为全局共享：user_id 为空的行是官方题库，所有人可见但不可改。
# 「本人私有 + 官方共享」两类都要返回，但不能把别的用户的私有数据漏出去。
def owned_or_shared(user_id: uuid.UUID | None):
    return or_(
        KnowledgeCategory.user_id == user_id, KnowledgeCategory.user_id.is_(None)
    )


async def ensure_default_categories(db: AsyncSession, user_id: uuid.UUID) -> None:
    existing = await db.scalar(
        select(KnowledgeCategory.id)
        .where(KnowledgeCategory.user_id == user_id)
        .limit(1)
    )
    if existing is not None:
        return

    roots: dict[str, KnowledgeCategory] = {}
    for order, (name, domain, _) in enumerate(DEFAULT_CATEGORY_TREE):
        root = KnowledgeCategory(
            user_id=user_id,
            name=name,
            domain=domain,
            sort_order=order,
        )
        roots[domain] = root
        db.add(root)
    await db.flush()

    japanese_category: KnowledgeCategory | None = None
    for _, domain, children in DEFAULT_CATEGORY_TREE:
        for order, name in enumerate(children):
            category = KnowledgeCategory(
                user_id=user_id,
                parent_id=roots[domain].id,
                name=name,
                domain=domain,
                sort_order=order,
            )
            db.add(category)
            if domain == "language" and name == "日语":
                japanese_category = category
    await db.flush()
    if japanese_category is not None:
        result = await db.execute(
            select(ScenarioCard).where(
                ScenarioCard.user_id == user_id,
                ScenarioCard.domain == "language",
            )
        )
        for scenario in result.scalars().all():
            scenario.categories.append(japanese_category)
    await db.commit()


async def list_categories(
    db: AsyncSession, user_id: uuid.UUID
) -> list[KnowledgeCategory]:
    await ensure_default_categories(db, user_id)
    # 2026-09-30 官方共享库（user_id IS NULL）与本人私有分类一并返回，供三级雅思树浏览。
    # scenarios 的 loader 必须带同样的可见性条件，否则 build_category_tree 的 card_count
    # 会把其他用户的私有场景也算进去，出现「侧边栏 12 张、网格只有 3 张」。
    result = await db.execute(
        select(KnowledgeCategory)
        .where(owned_or_shared(user_id), KnowledgeCategory.is_active.is_(True))
        .options(
            # 两个条件必须合进同一个 and_()：同一 relationship 上挂两个
            # selectinload 会互相覆盖。已归档场景仍留着 M2M link，
            # 不过滤 is_active 就会出现"侧边栏 12 张、点进去 3 张"。
            selectinload(
                KnowledgeCategory.scenarios.and_(
                    ScenarioCard.is_active.is_(True),
                    or_(
                        ScenarioCard.user_id == user_id,
                        ScenarioCard.user_id.is_(None),
                    ),
                )
            )
        )
        .order_by(KnowledgeCategory.sort_order, KnowledgeCategory.created_at)
    )
    return list(result.scalars().all())


def build_category_tree(categories: list[KnowledgeCategory]) -> list[dict]:
    by_id = {
        category.id: {
            "id": category.id,
            "name": category.name,
            "parent_id": category.parent_id,
            "domain": category.domain,
            "description": category.description,
            "sort_order": category.sort_order,
            # 2026-09-30 user_id 必须带上：KnowledgeCategoryRead 用它派生 is_shared。
            # 漏了它 Pydantic 会拿到 None，把所有分类都误判成官方共享，
            # 于是右键菜单和删除按钮对全部节点失效。
            # 注意 is_active 是必填字段，补 user_id 时不要把它挤掉——
            # 少了它 model_validate 直接 ValidationError，整棵树 500。
            "user_id": category.user_id,
            "is_active": category.is_active,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
            "children": [],
            "card_count": len(category.scenarios),
        }
        for category in categories
    }
    roots: list[dict] = []
    for category in categories:
        node = by_id[category.id]
        if category.parent_id and category.parent_id in by_id:
            by_id[category.parent_id]["children"].append(node)
        else:
            roots.append(node)

    def aggregate_card_count(node: dict) -> int:
        descendant_count = sum(
            aggregate_card_count(child) for child in node["children"]
        )
        node["card_count"] += descendant_count
        return node["card_count"]

    for root in roots:
        aggregate_card_count(root)
    return roots


class SharedReadOnlyError(PermissionError):
    """官方共享库（user_id 为空）对所有用户只读，尝试改写时抛出。"""


async def get_category(
    db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID
) -> KnowledgeCategory | None:
    # 2026-09-30 放开到官方共享分类，否则用户在共享的「Part 1」下建不了自己的子分类。
    # 写保护由 update_category / archive_category 单独拦，不依赖这里。
    return await db.scalar(
        select(KnowledgeCategory).where(
            KnowledgeCategory.id == category_id, owned_or_shared(user_id)
        )
    )


async def create_category(
    db: AsyncSession, user_id: uuid.UUID, payload: KnowledgeCategoryCreate
) -> KnowledgeCategory:
    if payload.parent_id is not None:
        parent = await get_category(db, payload.parent_id, user_id)
        if parent is None:
            raise ValueError("父分类不存在")
    category = KnowledgeCategory(user_id=user_id, **payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession, category: KnowledgeCategory, payload: KnowledgeCategoryUpdate
) -> KnowledgeCategory:
    if category.user_id is None:
        raise SharedReadOnlyError("官方题库为只读，不可修改")
    values = payload.model_dump(exclude_unset=True)
    if "parent_id" in values:
        parent_id = values["parent_id"]
        if parent_id == category.id:
            raise ValueError("分类不能成为自己的父分类")
        if parent_id is not None:
            parent = await get_category(db, parent_id, category.user_id)
            if parent is None:
                raise ValueError("父分类不存在")
    for field, value in values.items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


async def archive_category(db: AsyncSession, category: KnowledgeCategory) -> None:
    """归档分类及其整棵子树。

    2026-09-30 必须递归：只把根标记 is_active=False 时，子分类仍是 active，
    而 build_category_tree 对"父节点不在列表里"的节点会放进 roots——
    结果是删掉「雅思口语」后，Part 1/2/3 浮到侧边栏顶层变成根分类。

    官方共享子节点（user_id 为空）跳过，不被普通用户的删除操作波及。
    """
    if category.user_id is None:
        raise SharedReadOnlyError("官方题库为只读，不可删除")

    to_archive: list[KnowledgeCategory] = [category]
    seen: set[uuid.UUID] = {category.id}
    pending: list[uuid.UUID] = [category.id]

    while pending:
        current_id = pending.pop()
        result = await db.execute(
            select(KnowledgeCategory).where(KnowledgeCategory.parent_id == current_id)
        )
        for child in result.scalars().all():
            if child.id in seen or child.user_id is None:
                continue  # 官方共享节点不随父分类一起归档
            seen.add(child.id)
            to_archive.append(child)
            pending.append(child.id)

    for node in to_archive:
        node.is_active = False
    await db.commit()
