# llm_langchain.py

from typing import Any, List, Optional, ClassVar

# Assuming GenerateContentResponse is still needed for type hinting
from google.generativeai.types import GenerateContentResponse
from langchain_core.callbacks.manager import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from pydantic import Field  # <--- NEW: Import Field for model attributes

from config import settings
import os
# Import the new refactored pool
from .llm_call import service_pool, LLMServicePool

os.environ["LANGSMITH_TRACING_V2"] = settings.LANGSMITH_TRACING_V2
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT

# --- REFACTORED: From CustomGeminiChatModel to a more generic CustomLLMChatModel ---
class CustomLLMChatModel(BaseChatModel):
    """
    A custom LangChain ChatModel that uses our LLMServicePool for API calls.

    This model can be configured to use different providers like 'gemini' or 'local'
    that are managed by the central service pool.
    """
    # The provider to use for this instance ('gemini' or 'local')
    provider: str = Field(default="gemini")

    # Use ClassVar for the shared pool instance
    service_pool: ClassVar[LLMServicePool] = service_pool

    @property
    def _llm_type(self) -> str:
        """A required property for all custom LLM classes."""
        return "custom_llm_chat_model"

    def _create_chat_result(self, response: Any) -> ChatResult:
        """
        Helper to convert API responses (from any provider) into a ChatResult.
        It now handles both Gemini's rich response and our local mock response.
        """
        # --- MODIFIED: Handle different response structures ---
        if hasattr(response, 'usage_metadata'):
            # This is a real Gemini response
            token_usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }
            # The model name is on the service, but let's get it from the pool config for simplicity
            model_name = self.service_pool.services['gemini'][0].model_name
        else:
            # This is our mock response from the LocalService
            token_usage = {
                "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0
            }
            model_name = response.model_name  # We added this to our mock response

        generation = ChatGeneration(
            message=AIMessage(content=response.text),
            generation_info={"model_name": model_name},
        )

        llm_output = {
            "token_usage": token_usage,
            "model_name": model_name,
        }

        return ChatResult(generations=[generation], llm_output=llm_output)

    def _generate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> ChatResult:
        """SYNCHRONOUS implementation. Routes to the configured provider."""
        prompt = "\n".join([msg.content for msg in messages])

        # --- MODIFIED: Pass the instance's provider to the pool ---
        response = self.service_pool.route_call_sync(
            provider=self.provider,
            prompt=prompt,
            max_output_tokens=kwargs.get("max_output_tokens", 1024),
            temperature=kwargs.get("temperature", 0.0)
        )

        if not response:
            raise RuntimeError(f"API call to provider '{self.provider}' failed in synchronous mode.")

        return self._create_chat_result(response)

    async def _agenerate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> ChatResult:
        """ASYNCHRONOUS implementation. Routes to the configured provider."""
        prompt = "\n".join([msg.content for msg in messages])

        # --- MODIFIED: Pass the instance's provider to the pool ---
        response = await self.service_pool.route_call_async(
            provider=self.provider,
            prompt=prompt,
            max_output_tokens=kwargs.get("max_output_tokens", 1024),
            temperature=kwargs.get("temperature", 0.0)
        )

        if not response:
            raise RuntimeError(f"API call to provider '{self.provider}' failed in asynchronous mode.")

        return self._create_chat_result(response)


# An instance configured to use the Gemini provider from the pool
gemini_llm_service = CustomLLMChatModel(provider="gemini")

# An instance configured to use the Local provider from the pool
local_llm_service = CustomLLMChatModel(provider="local")