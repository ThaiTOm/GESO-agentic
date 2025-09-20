# llm_langchain.py

from typing import Any, List, Optional, ClassVar

from google.generativeai.types import GenerateContentResponse
from langchain_core.callbacks.manager import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from pydantic import Field
from typing import Any, List, Optional, ClassVar, Dict # <-- Add Dict
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage # <-- Add more message types

from .llm_call import service_pool, LLMServicePool

def _convert_lc_messages_to_openai_format(messages: List[BaseMessage]) -> List[Dict[str, str]]:
    """Converts a list of LangChain messages to the OpenAI API dictionary format."""
    openai_messages = []
    for message in messages:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, SystemMessage):
            role = "system"
        else:
            # Skip or handle other message types if necessary
            continue
        openai_messages.append({"role": role, "content": message.content})
    return openai_messages

class CustomLLMChatModel(BaseChatModel):
    """
    A custom LangChain ChatModel that uses our LLMServicePool for API calls.
    It can be configured to use different providers like 'gemini' or 'local'.
    """
    provider: str = Field(default="gemini")
    service_pool: ClassVar[LLMServicePool] = service_pool

    @property
    def _llm_type(self) -> str:
        return "custom_llm_chat_model"

    # --- REVERTED THIS METHOD ---
    def _create_chat_result(self, response: Any) -> ChatResult:
        """
        Helper to convert API responses into a ChatResult.
        It handles both Gemini's rich response and our local mock response.
        """
        token_usage = {}
        model_name = ""

        if hasattr(response, 'usage_metadata'):
            # This is a Gemini response with token counts
            token_usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count,
            }
            model_name = self.service_pool.services['gemini'][0].model_name
        else:
            # This is our simple response from the LocalService (no token counts)
            token_usage = {
                "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0
            }
            model_name = response.model_name

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
        # --- MODIFICATION ---
        # For Gemini, we still need the flattened prompt.
        # For Local, we need the structured messages.
        if self.provider == "local":
            # Pass the structured messages directly
            request_data = _convert_lc_messages_to_openai_format(messages)
        else: # provider is gemini
            # Flatten for Gemini API
            request_data = "\n".join([msg.content for msg in messages])

        response = self.service_pool.route_call_sync(
            provider=self.provider,
            request_data=request_data, # Use a generic name
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
        # --- MODIFICATION ---
        if self.provider == "local":
            request_data = _convert_lc_messages_to_openai_format(messages)
        else: # provider is gemini
            request_data = "\n".join([msg.content for msg in messages])

        response = await self.service_pool.route_call_async(
            provider=self.provider,
            request_data=request_data, # Use a generic name
            max_output_tokens=kwargs.get("max_output_tokens", 1024),
            temperature=kwargs.get("temperature", 0.0)
        )

        if not response:
            raise RuntimeError(f"API call to provider '{self.provider}' failed in asynchronous mode.")

        return self._create_chat_result(response)


# --- Instances (Unchanged) ---
gemini_llm_service = CustomLLMChatModel(provider="gemini")

local_llm_service = CustomLLMChatModel(provider="local")