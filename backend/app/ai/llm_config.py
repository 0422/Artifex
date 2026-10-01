"""LLM 供应商配置。

2026-10-01 把 LLM 调用从 ``settings`` 单例中抽离，改为「.env 声明 + 运行时副本」两层：

* **``.env``（声明式源）**：按组声明多家供应商的请求地址 / API Key / 模型，
  ``ACTIVE_LLM_PROVIDER`` 指定当前用哪一家。定义几组，LLM Select 菜单就展示几项，
  新增一家复制一组改前缀即可，无需改代码。
* **``backend/config/llm_providers.json``（运行时副本）**：首次运行由 .env 生成，
  之后承载菜单里的切换 / 修改 / 新增。每次启动会把 .env 里新增的组合并进来，
  并同步 .env 已定义的供应商（.env 的改动优先，界面新增的供应商不受影响）。

业务代码只需 :func:`get_active`：拿当前供应商的 base_url / api_key / model。
"""

import json
import os
import re
import uuid
from pathlib import Path
from threading import RLock
from typing import Any

from dotenv import dotenv_values

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "llm_providers.json"

# .env 的两个候选位置：当前工作目录优先，其次 backend/（与 pydantic-settings 的查找方式一致）
_ENV_PATH_CANDIDATES = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]

# <前缀>_LLM_<字段>：前缀即供应商 id。菜单里新增一家只需在 .env 里多一组同前缀的变量。
_PROVIDER_ENV_RE = re.compile(r"^([A-Za-z0-9]+)_LLM_(NAME|BASE_URL|API_KEY|MODEL|NO_JSON_MODELS)$")

# 没配 <前缀>_LLM_NAME 时的兜底展示名
_DEFAULT_NAMES = {"relay": "中转站", "deepseek": "DeepSeek", "stepfun": "StepFun 阶跃星辰"}

_lock = RLock()
# (mtime, data) 缓存：文件没变就不重复读盘，改动后即时生效
_cache: tuple[float, dict[str, Any]] | None = None
# .env 取值的缓存，同样按 mtime 失效
_env_cache: tuple[float, dict[str, str]] | None = None


def _env_path() -> Path | None:
    for candidate in _ENV_PATH_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _env_values() -> dict[str, str]:
    """合并 .env 文件与真实环境变量（后者优先，便于 Docker 注入）。

    ``dotenv_values`` 保留文件书写顺序，因此菜单里的供应商顺序与 .env 一致。
    """
    global _env_cache
    path = _env_path()
    mtime = path.stat().st_mtime if path else 0.0
    with _lock:
        if _env_cache is not None and _env_cache[0] == mtime:
            return _env_cache[1]

        values: dict[str, str] = {}
        if path is not None:
            for key, value in dotenv_values(path).items():
                if value is not None and str(value).strip():
                    values[key] = str(value).strip()
        for key, value in os.environ.items():
            if value and value.strip():
                values[key] = value.strip()

        _env_cache = (mtime, values)
        return values


def _split_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in re.split(r"[,，\n]", raw) if item.strip()]


def _providers_from_env() -> list[dict[str, Any]]:
    """扫出 .env 里定义的所有供应商，顺序与 .env 书写顺序一致。"""
    grouped: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for key, value in _env_values().items():
        matched = _PROVIDER_ENV_RE.match(key)
        if not matched:
            continue
        prefix = matched.group(1).lower()
        if prefix not in grouped:
            grouped[prefix] = {}
            order.append(prefix)
        grouped[prefix][matched.group(2).lower()] = value

    providers: list[dict[str, Any]] = []
    for prefix in order:
        fields = grouped[prefix]
        no_json = set(_split_list(fields.get("no_json_models")))
        providers.append(
            {
                "id": prefix,
                "name": fields.get("name") or _DEFAULT_NAMES.get(prefix) or prefix,
                # .env 定义的供应商锁定不可删：界面删了，下次启动也会被合并回来
                "builtin": True,
                "base_url": fields.get("base_url", "").rstrip("/"),
                "api_key": fields.get("api_key", ""),
                "models": [
                    {"name": m, "json_mode": m not in no_json}
                    for m in _split_list(fields.get("model"))
                ],
            }
        )
    return providers


def _active_from_env() -> str | None:
    """``ACTIVE_LLM_PROVIDER``：.env 里指定"用哪一家"的宏。"""
    macro = _env_values().get("ACTIVE_LLM_PROVIDER", "")
    return macro.strip() or None


def _with_active_model(provider: dict[str, Any]) -> dict[str, Any]:
    """补齐 active_model：为空或不在模型列表里时，回退到第一个模型。"""
    models = provider.get("models") or []
    active = provider.get("active_model")
    names = [m.get("name") for m in models if m.get("name")]
    if active not in names:
        provider["active_model"] = names[0] if names else None
    return provider


def _env_signature(provider: dict[str, Any]) -> dict[str, Any]:
    """记录本次从 .env 同步了哪些值，下次启动用它判断 .env 是否变过。"""
    return {
        "name": provider["name"],
        "base_url": provider["base_url"],
        "api_key": provider["api_key"],
        "models": [dict(m) for m in provider["models"]],
    }


def _seed_from_env() -> dict[str, Any]:
    """首次运行：完全按 .env 生成配置。"""
    providers = [_with_active_model(p) for p in _providers_from_env()]
    macro = _active_from_env()
    active = (
        macro
        if macro and any(p["id"] == macro for p in providers)
        else (providers[0]["id"] if providers else None)
    )
    for provider in providers:
        provider["env_synced"] = _env_signature(provider)
    return {"active_provider_id": active, "active_from_env": macro, "providers": providers}


def _merge_env(data: dict[str, Any]) -> dict[str, Any] | None:
    """把 .env 对齐进运行时配置；无需改动时返回 None。

    * .env 有、JSON 没有 -> 追加（在 .env 加一组，菜单就多一项）
    * .env 的值与上次同步不一致 -> 以 .env 为准覆盖（改 .env 优先于界面修改）
    * .env 没变 -> 保留界面上的修改
    * ``ACTIVE_LLM_PROVIDER`` 变了 -> 重新应用该宏
    """
    changed = False

    for env_provider in _providers_from_env():
        existing = next((p for p in data["providers"] if p["id"] == env_provider["id"]), None)
        if existing is None:
            env_provider["env_synced"] = _env_signature(env_provider)
            data["providers"].append(_with_active_model(env_provider))
            changed = True
            continue

        if existing.get("env_synced") != _env_signature(env_provider):
            existing.update(
                {
                    "name": env_provider["name"],
                    "base_url": env_provider["base_url"],
                    "api_key": env_provider["api_key"],
                    "models": [dict(m) for m in env_provider["models"]],
                    "env_synced": _env_signature(env_provider),
                }
            )
            _with_active_model(existing)
            changed = True

    macro = _active_from_env()
    if (
        macro
        and macro != data.get("active_from_env")
        and any(p["id"] == macro for p in data["providers"])
    ):
        data["active_provider_id"] = macro
        data["active_from_env"] = macro
        changed = True

    return data if changed else None


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    """把读到的 JSON 修整成可信结构，容忍手工编辑留下的缺字段。"""
    providers = []
    for raw in data.get("providers") or []:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        provider = {
            "id": str(raw["id"]),
            "name": str(raw.get("name") or raw["id"]),
            "builtin": bool(raw.get("builtin", False)),
            "base_url": str(raw.get("base_url") or "").rstrip("/"),
            "api_key": str(raw.get("api_key") or ""),
            "models": [
                {"name": str(m["name"]), "json_mode": bool(m.get("json_mode", True))}
                for m in (raw.get("models") or [])
                if isinstance(m, dict) and m.get("name")
            ],
        }
        provider["active_model"] = raw.get("active_model")
        if "env_synced" in raw:
            provider["env_synced"] = raw["env_synced"]
        providers.append(_with_active_model(provider))

    active_id = data.get("active_provider_id")
    if not any(p["id"] == active_id for p in providers):
        active_id = providers[0]["id"] if providers else None
    return {
        "active_provider_id": active_id,
        "active_from_env": data.get("active_from_env"),
        "providers": providers,
    }


def _env_mtime() -> float:
    path = _env_path()
    return path.stat().st_mtime if path else 0.0


def _save(data: dict[str, Any]) -> None:
    """原子写入：先写临时文件再替换，避免半截 JSON 被下次读取。"""
    global _cache
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CONFIG_PATH)
    # 缓存键必须同时含 .env 与 JSON 两个 mtime：只按 JSON 的 mtime 判断，
    # 用户改了 .env 而 JSON 没变时会命中旧缓存，界面一直显示旧值。
    _cache = ((CONFIG_PATH.stat().st_mtime, _env_mtime()), data)


def _load() -> dict[str, Any]:
    global _cache
    config_mtime = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else None

    with _lock:
        if _cache is not None and _cache[0] == (config_mtime, _env_mtime()):
            return _cache[1]

        if config_mtime is None:
            data = _seed_from_env()
            _save(data)
            return data

        try:
            data = _normalize(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, AttributeError, TypeError):
            data = _seed_from_env()
            _save(data)
            return data

        merged = _merge_env(data)
        if merged is None:
            _cache = ((config_mtime, _env_mtime()), data)
            return data
        _save(merged)
        return merged


def _mask(api_key: str) -> str:
    """脱敏展示：只留前后各 4 位，中间按长度打星。"""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"


def _active_model_of(data: dict[str, Any], provider_id: str | None) -> str | None:
    if provider_id is None:
        return None
    for p in data["providers"]:
        if p["id"] == provider_id:
            return p["active_model"]
    return None


def list_providers() -> dict[str, Any]:
    """给前端用的脱敏视图。"""
    data = _load()
    return {
        "active_provider_id": data["active_provider_id"],
        "active_model": _active_model_of(data, data["active_provider_id"]),
        "providers": [
            {
                "id": p["id"],
                "name": p["name"],
                "base_url": p["base_url"],
                "api_key_masked": _mask(p["api_key"]),
                "active_model": p["active_model"],
                "models": p["models"],
                "builtin": p["builtin"],
            }
            for p in data["providers"]
        ],
    }


def get_active() -> tuple[dict[str, Any], dict[str, Any]]:
    """返回 (供应商, 当前模型)，llm.py 每次调用都从这里取，切换后立即生效。"""
    data = _load()
    provider = next(
        (p for p in data["providers"] if p["id"] == data["active_provider_id"]), None
    )
    if provider is None:
        raise ValueError("尚未配置可用的 LLM 供应商，请在「LLM Select」中添加")
    model_name = provider["active_model"]
    model = next((m for m in provider["models"] if m["name"] == model_name), None)
    if model is None:
        raise ValueError(f"LLM「{provider['name']}」尚未选择模型")
    if not provider["api_key"]:
        raise ValueError(f"LLM「{provider['name']}」尚未填写 API Key")
    return provider, model


def set_active(provider_id: str, model: str | None = None) -> dict[str, Any]:
    """切换供应商，可同时指定该供应商下的模型。"""
    with _lock:
        data = _load()
        provider = next((p for p in data["providers"] if p["id"] == provider_id), None)
        if provider is None:
            raise ValueError("供应商不存在")
        data["active_provider_id"] = provider_id
        if model is not None:
            if not any(m["name"] == model for m in provider["models"]):
                raise ValueError(f"供应商「{provider['name']}」下没有模型 {model}")
            provider["active_model"] = model
        else:
            _with_active_model(provider)
        _save(data)
        return list_providers()


def add_provider(name: str, base_url: str, api_key: str, models: list[str]) -> dict[str, Any]:
    """在菜单里新增一家供应商及其模型，写回配置文件。"""
    name = name.strip()
    base_url = base_url.strip().rstrip("/")
    api_key = api_key.strip()
    model_names = [m.strip() for m in models if m and m.strip()]
    if not name or not base_url or not api_key:
        raise ValueError("名称、请求地址和 API Key 均为必填")
    if not model_names:
        raise ValueError("至少填写一个模型")

    with _lock:
        data = _load()
        if any(p["name"] == name for p in data["providers"]):
            raise ValueError(f"已存在同名供应商「{name}」")
        provider = {
            "id": f"custom-{uuid.uuid4().hex[:8]}",
            "name": name,
            "builtin": False,
            "base_url": base_url,
            "api_key": api_key,
            "models": [{"name": m, "json_mode": True} for m in model_names],
        }
        _with_active_model(provider)
        data["providers"].append(provider)
        _save(data)
        return list_providers()


def update_provider(
    provider_id: str,
    name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    models: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """修改已有供应商。参数为 None 表示该项保持原值不变。

    API Key 走"留空即不改"：后端只回掩码，前端编辑框默认空着，
    用户没填新 Key 就不能把已保存的 Key 清掉。
    """
    with _lock:
        data = _load()
        provider = next((p for p in data["providers"] if p["id"] == provider_id), None)
        if provider is None:
            raise ValueError("供应商不存在")

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("名称不能为空")
            if any(p["id"] != provider_id and p["name"] == name for p in data["providers"]):
                raise ValueError(f"已存在同名供应商「{name}」")
            provider["name"] = name

        if base_url is not None:
            base_url = base_url.strip().rstrip("/")
            if not base_url:
                raise ValueError("请求地址不能为空")
            provider["base_url"] = base_url

        if api_key:
            api_key = api_key.strip()
            if not api_key:
                raise ValueError("API Key 不能为空白字符")
            provider["api_key"] = api_key

        if models is not None:
            cleaned: list[dict[str, Any]] = []
            for item in models:
                model_name = (item.get("name") or "").strip()
                if not model_name or any(m["name"] == model_name for m in cleaned):
                    continue
                cleaned.append({"name": model_name, "json_mode": bool(item.get("json_mode", True))})
            if not cleaned:
                raise ValueError("至少保留一个模型")
            provider["models"] = cleaned

        # 若改掉了当前选中的模型，回退到第一个，避免留下指向不存在模型的 active_model
        _with_active_model(provider)
        _save(data)
        return list_providers()


def delete_provider(provider_id: str) -> dict[str, Any]:
    """删除菜单里自建的供应商；.env 定义的供应商锁定，防止删了又被合并回来。"""
    with _lock:
        data = _load()
        provider = next((p for p in data["providers"] if p["id"] == provider_id), None)
        if provider is None:
            raise ValueError("供应商不存在")
        if provider["builtin"]:
            raise ValueError(f"「{provider['name']}」由 .env 定义，不可删除；可修改或改 .env")
        data["providers"] = [p for p in data["providers"] if p["id"] != provider_id]
        if data["active_provider_id"] == provider_id:
            data["active_provider_id"] = data["providers"][0]["id"] if data["providers"] else None
        _save(data)
        return list_providers()
