"""DeepSeek 兼容 LLM。

CrewAI 的 OpenAICompatibleCompletion 在 response_model（即 output_pydantic /
output_json）存在时，会调用 OpenAI 专属的
``client.beta.chat.completions.parse(..., response_format=<PydanticModel>)``。

DeepSeek 的 OpenAI 兼容接口不支持这种 ``json_schema`` 形式的
``response_format``，会报错：
    "This response_format type is unavailable now"

这里通过子类覆盖 ``_handle_completion``，当存在 response_model 时改用普通的
``chat.completions.create(response_format={"type": "json_object"})``，
再用 ``_validate_structured_output`` 手动把返回的 JSON 文本解析为对应的
Pydantic 模型。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel

from crewai.llms.providers.openai_compatible.completion import (
    OpenAICompatibleCompletion,
)

logger = logging.getLogger(__name__)


class DeepSeekCompatibleLLM(OpenAICompatibleCompletion):
    """OpenAICompatibleCompletion 的子类，规避 DeepSeek 不支持的 beta.parse 接口。"""

    def _handle_completion(
        self,
        params: dict[str, Any],
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> str | Any:
        if response_model is None:
            return super()._handle_completion(
                params=params,
                available_functions=available_functions,
                from_task=from_task,
                from_agent=from_agent,
                response_model=None,
            )

        # 不使用 beta.chat.completions.parse，改为普通 completion + JSON 模式
        json_params = {
            k: v for k, v in params.items() if k != "response_format"
        }
        json_params["response_format"] = {"type": "json_object"}

        response = self._get_sync_client().chat.completions.create(**json_params)

        usage = self._extract_openai_token_usage(response)
        self._track_token_usage_internal(usage)

        message = response.choices[0].message
        content = message.content or ""

        try:
            data = json.loads(content)
            parsed = response_model.model_validate(data)
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to parse DeepSeek JSON response: %s", e)
            parsed = self._validate_structured_output(content, response_model)

        finish_reason, response_id = self._extract_chat_finish_reason_and_id(response)
        self._emit_call_completed_event(
            response=parsed.model_dump_json()
            if isinstance(parsed, BaseModel)
            else str(parsed),
            call_type=self._llm_call_type_for_emit(),
            from_task=from_task,
            from_agent=from_agent,
            messages=params["messages"],
            usage=usage,
            finish_reason=finish_reason,
            response_id=response_id,
        )
        return parsed

    @staticmethod
    def _llm_call_type_for_emit():
        from crewai.llms.base_llm import LLMCallType

        return LLMCallType.LLM_CALL


def get_deepseek_llm(model: str = "deepseek-chat", **kwargs: Any) -> DeepSeekCompatibleLLM:
    """构造一个使用 DeepSeek 的 LLM 实例（避免 crewai 的 LLM 工厂走 beta.parse 路径）。"""
    return DeepSeekCompatibleLLM(model=model, provider="deepseek", **kwargs)
