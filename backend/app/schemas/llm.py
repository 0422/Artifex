from pydantic import BaseModel, ConfigDict, Field


class LLMModelRead(BaseModel):
    """模型项。json_mode 控制是否发送 response_format（思考类模型常不支持）。"""

    model_config = ConfigDict(from_attributes=True)

    name: str
    json_mode: bool = True


class LLMProviderRead(BaseModel):
    """供应商脱敏视图：api_key 只回掩码，不明文返回。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    base_url: str
    api_key_masked: str
    active_model: str | None
    models: list[LLMModelRead]
    builtin: bool


class LLMProvidersResponse(BaseModel):
    active_provider_id: str | None
    active_model: str | None
    providers: list[LLMProviderRead]


class LLMProviderCreate(BaseModel):
    """新增供应商：名称 / 请求地址 / API Key / 模型列表。"""

    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=500)
    models: list[str] = Field(min_length=1)


class LLMModelInput(BaseModel):
    """修改时的模型项，允许逐模型控制 json_mode。"""

    name: str = Field(min_length=1, max_length=200)
    json_mode: bool = True


class LLMProviderUpdate(BaseModel):
    """修改已有供应商。

    所有字段均可选，未传的保持原值。api_key 特意允许留空：后端只回掩码，
    前端编辑时 Key 输入框默认为空，留空即表示"不修改"，避免误清空已保存的 Key。
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)
    models: list[LLMModelInput] | None = None


class LLMActivateRequest(BaseModel):
    """切换供应商；model 为空时沿用该供应商当前的 active_model。"""

    model: str | None = None
