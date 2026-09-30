"""雅思口语真题库导入脚本。

把种子 JSON 里的真题写进**全局共享库**（`user_id` 为空的行），所有用户可见但不可改。
分类树与场景都按自然键 upsert，重跑不会产生重复数据。

用法：
    python -m app.scripts.import_ielts_speaking                       # 用默认 seeds/ielts_speaking.json
    python -m app.scripts.import_ielts_speaking --source seeds/x.json
    python -m app.scripts.import_ielts_speaking --dry-run             # 只报告将写入多少行
    python -m app.scripts.import_ielts_speaking --skip 娱乐             # 跳过指定类别

题库 JSON 结构见 seeds/ielts_speaking.json：
    {
      "part1": {"个人喜好类": [{"title": "...", "questions": "一行一题", "difficulty": "B1"}]},
      "part2": {"人物":       [{"title": "...", "cue_card": "You should say: ..."}]},
      "part3": {"人物":       [{"title": "...", "questions": "一行一题"}]}
    }
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.enums import ScenarioDifficulty
from app.models.knowledge import KnowledgeCategory
from app.models.scenario import ScenarioCard

ROOT_NAME = "雅思口语"
PART_NAMES = {1: "Part 1", 2: "Part 2", 3: "Part 3"}
# 2026-09-30 暂定的默认难度映射，逐题可在 JSON 里用 difficulty 覆盖
DEFAULT_DIFFICULTY = {1: "B1", 2: "B2", 3: "C1"}
DEFAULT_SEED = "seeds/ielts_speaking.json"


def load_bank(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"题库文件不存在：{path}")
    bank = json.loads(path.read_text(encoding="utf-8"))
    for key in ("part1", "part2", "part3"):
        if not isinstance(bank.get(key), dict):
            raise SystemExit(f"题库缺少 {key} 段落或格式不对")
    return bank


async def _get_or_create_category(
    db, *, parent_id, name: str, domain: str, sort_order: int
) -> KnowledgeCategory:
    """共享分类按 (父节点, 名称)  upsert。"""
    stmt = select(KnowledgeCategory).where(
        KnowledgeCategory.user_id.is_(None),
        KnowledgeCategory.parent_id == parent_id,
        KnowledgeCategory.name == name,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        if not existing.is_active:
            existing.is_active = True  # 曾被归档过的共享分类重新启用
        return existing
    category = KnowledgeCategory(
        user_id=None,
        parent_id=parent_id,
        name=name,
        domain=domain,
        sort_order=sort_order,
        is_active=True,
    )
    db.add(category)
    await db.flush()
    return category


def _normalise_difficulty(raw: str | None, part: int) -> ScenarioDifficulty:
    value = (raw or DEFAULT_DIFFICULTY[part]).strip()
    try:
        return ScenarioDifficulty(value)
    except ValueError:
        print(f"  ! 难度 {value!r} 不在枚举内，回退到 {DEFAULT_DIFFICULTY[part]}")
        return ScenarioDifficulty(DEFAULT_DIFFICULTY[part])


async def import_bank(db, bank: dict, skip: set[str], dry_run: bool) -> dict:
    stats = {"categories": 0, "scenarios": 0, "updated": 0}

    root = await _get_or_create_category(
        db, parent_id=None, name=ROOT_NAME, domain="language", sort_order=0
    )
    stats["categories"] += 1

    for part in (1, 2, 3):
        part_node = await _get_or_create_category(
            db,
            parent_id=root.id,
            name=PART_NAMES[part],
            domain="language",
            sort_order=part,
        )
        categories = bank[f"part{part}"]
        for order, (category_name, items) in enumerate(categories.items()):
            if category_name in skip:
                print(f"  - 跳过类别 {category_name}")
                continue
            category = await _get_or_create_category(
                db,
                parent_id=part_node.id,
                name=category_name,
                domain="language",
                sort_order=order,
            )
            stats["categories"] += 1

            for item in items:
                title = (item.get("title") or "").strip()
                if not title:
                    print(f"  ! 跳过一条没有标题的题目（{category_name}）")
                    continue

                # Part 2 用题卡，Part 1/3 用按行分隔的题库
                cue_card = item.get("cue_card")
                questions = item.get("questions") or item.get("description") or ""
                description = cue_card or questions
                if not description:
                    print(f"  ! 【{title}】既无 cue_card 也无 questions，跳过")
                    continue

                difficulty = _normalise_difficulty(item.get("difficulty"), part)
                tags = list(dict.fromkeys(item.get("tags") or []))[:20]

                # selectinload 必须加：async 下访问未加载的 categories 会触发
                # lazy load，直接抛 MissingGreenlet
                stmt = (
                    select(ScenarioCard)
                    .where(
                        ScenarioCard.user_id.is_(None),
                        ScenarioCard.ielts_part == part,
                        ScenarioCard.title == title,
                    )
                    .options(selectinload(ScenarioCard.categories))
                )
                existing = (await db.execute(stmt)).scalar_one_or_none()
                if existing is not None:
                    existing.description = description
                    existing.cue_card = cue_card
                    existing.difficulty = difficulty
                    existing.tags = tags
                    existing.domain = "language"
                    existing.is_active = True
                    if category not in existing.categories:
                        existing.categories.append(category)
                    stats["updated"] += 1
                    continue

                scenario = ScenarioCard(
                    user_id=None,
                    title=title,
                    description=description,
                    language="en",
                    difficulty=difficulty,
                    domain="language",
                    # 雅思场景由 ielts_part 驱动 prompt，scenario_mode 只是占位
                    scenario_mode="guided_discussion",
                    estimated_minutes=item.get("estimated_minutes"),
                    tags=tags,
                    ielts_part=part,
                    cue_card=cue_card,
                    is_active=True,
                    categories=[category],
                )
                db.add(scenario)
                stats["scenarios"] += 1

    return stats


async def run(args: argparse.Namespace) -> int:
    bank_path = Path(args.source)
    if not bank_path.is_absolute():
        bank_path = Path(__file__).resolve().parents[2] / bank_path
    bank = load_bank(bank_path)

    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    print(f"题库文件：{bank_path}")
    print(f"目标数据库：{settings.database_url.split('@')[-1]}")
    if args.dry_run:
        print("模式：dry-run（不落库）")

    try:
        async with session_factory() as db:
            try:
                stats = await import_bank(db, bank, set(args.skip or []), args.dry_run)
                if args.dry_run:
                    await db.rollback()
                else:
                    await db.commit()
            except Exception:
                await db.rollback()
                raise
    finally:
        await engine.dispose()

    print()
    print(f"分类节点：{stats['categories']} 个（含根与 Part）")
    print(f"新增题目：{stats['scenarios']} 道")
    print(f"更新题目：{stats['updated']} 道")
    if args.dry_run:
        print("（dry-run，未写入数据库）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导入雅思口语真题库到全局共享库")
    parser.add_argument("--source", default=DEFAULT_SEED, help="题库 JSON 路径")
    parser.add_argument("--dry-run", action="store_true", help="只报告将写入的行数")
    parser.add_argument(
        "--skip", action="append", default=[], help="跳过指定类别，可重复传入"
    )
    args = parser.parse_args(argv)
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
