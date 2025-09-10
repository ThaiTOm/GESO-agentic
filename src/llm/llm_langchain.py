# custom_llm.py

from typing import Any, List, Optional, ClassVar

from google.generativeai.types import GenerateContentResponse
from langchain_core.callbacks.manager import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

# Import your service pool and its type from your llm_caller file
from .llm_call import service_pool, GeminiServicePool
import os
from config import settings

os.environ["LANGSMITH_TRACING_V2"] = settings.LANGSMITH_TRACING_V2
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT

class CustomGeminiChatModel(BaseChatModel):
    """
    A custom LangChain ChatModel that uses our GeminiServicePool for API calls.

    This class correctly implements both synchronous (_generate) and
    asynchronous (_agenerate) methods, making it fully compatible with
    LangChain's .invoke() and .ainvoke() methods, as well as LangGraph.
    """
    # Use ClassVar to tell Pydantic that this is a class-level variable,
    # not a configurable model field. This resolves the Pydantic error.
    service_pool: ClassVar[GeminiServicePool] = service_pool

    @property
    def _llm_type(self) -> str:
        """A required property for all custom LLM classes."""
        return "custom_gemini_chat_model"

    def _create_chat_result(self, response: GenerateContentResponse) -> ChatResult:
        """
        A helper method to convert the Gemini API response into the ChatResult
        object that LangChain expects. This is used by both sync and async methods.
        """
        # 1. Extract token usage from the response metadata for LangSmith tracking
        token_usage = {
            "prompt_tokens": response.usage_metadata.prompt_token_count,
            "completion_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count,
        }

        # 2. Create the ChatGeneration object
        generation = ChatGeneration(
            message=AIMessage(content=response.text),
            generation_info={"model_name": self.service_pool.services[0].model_name},
        )

        # 3. Prepare the final llm_output dictionary
        llm_output = {
            "token_usage": token_usage,
            "model_name": self.service_pool.services[0].model_name,
        }

        # 4. Return the fully-formed ChatResult
        return ChatResult(generations=[generation], llm_output=llm_output)

    def _generate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> ChatResult:
        """
        The SYNCHRONOUS implementation for the chat model.
        This is called when you use .invoke()
        """
        # Convert LangChain messages to a simple string prompt for our service pool
        prompt = "\n".join([msg.content for msg in messages])

        # Call the synchronous method on our service pool
        response = self.service_pool.route_call_sync(
            prompt=prompt,
            max_output_tokens=kwargs.get("max_output_tokens", 1024),
            temperature=kwargs.get("temperature", 0.0)
        )

        if not response:
            raise RuntimeError("API call to Gemini failed in synchronous mode.")

        return self._create_chat_result(response)

    async def _agenerate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> ChatResult:
        """
        The ASYNCHRONOUS implementation for the chat model.
        This is called when you use .ainvoke() (used by LangGraph).
        """
        # Convert LangChain messages to a simple string prompt
        prompt = "\n".join([msg.content for msg in messages])

        # Call the asynchronous method on our service pool
        response = await self.service_pool.route_call_async(
            prompt=prompt,
            max_output_tokens=kwargs.get("max_output_tokens", 1024),
            temperature=kwargs.get("temperature", 0.0)
        )

        if not response:
            raise RuntimeError("API call to Gemini failed in asynchronous mode.")

        return self._create_chat_result(response)


cloud_llm_service = CustomGeminiChatModel()