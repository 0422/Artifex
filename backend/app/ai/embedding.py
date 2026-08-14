"""Embedding 服务。

当前中转站（micuapi vip_2 分组）不提供任何 embedding 模型，实测 /v1/embeddings 返回
model_not_found。因此本模块暂时留为可插拔占位：embed_text 返回 None，语义关联搜索
（Capture 的"标注已有知识关联"验收项）暂不启用。等接入可用的 embedding 渠道后，
只需实现 embed_text 即可，上层逻辑无需改动。
"""

from app.core.config import get_settings

settings = get_settings()

# 是否已接入可用的 embedding 服务
EMBEDDING_ENABLED = False


async def embed_text(text: str) -> list[float] | None:
    """把文本转成向量。未接入 embedding 服务时返回 None。"""
    if not EMBEDDING_ENABLED:
        return None
    # TODO: 接入可用 embedding 渠道后在此实现（OpenAI 兼容 /v1/embeddings 或本地模型）
    raise NotImplementedError
