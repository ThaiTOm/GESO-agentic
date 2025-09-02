import os
from typing import Literal, TypedDict, Annotated
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from ...config import Settings

settings = Settings()

class LLMProvider:
    """
    Một class factory để cung cấp một đối tượng LLM đã được khởi tạo
    dựa trên nhà cung cấp được chọn (cloud hoặc local).
    """

    def __init__(self, provider: settings.ProviderType, config: Settings):
        """
        Khởi tạo Provider.

        Args:
            provider: Tên của nhà cung cấp ('openai', 'gemini', 'local').
            config: Đối tượng cấu hình chứa API keys và các thông tin khác.
        """
        if not provider in ["openai", "gemini", "local"]:
            raise ValueError("Nhà cung cấp không hợp lệ. Vui lòng chọn 'openai', 'gemini', hoặc 'local'.")

        self.provider = provider
        self.config = config
        self.llm = self._create_llm()

    def _create_llm(self):
        """
        Phương thức nội bộ để tạo instance LLM dựa trên provider.
        """
        print(f"--- Đang khởi tạo mô hình từ nhà cung cấp: {self.provider} ---")
        if self.provider == "openai":
            if self.config.OPENAI_API_KEY == "not-set":
                raise ValueError("Vui lòng cung cấp OPENAI_API_KEY trong file .env")
            return ChatOpenAI(
                api_key=self.config.OPENAI_API_KEY,
                model=self.config.OPENAI_MODEL_NAME,
                temperature=0.7
            )
        elif self.provider == "gemini":
            if self.config.GEMINI_API_KEY == "not-set":
                raise ValueError("Vui lòng cung cấp GEMINI_API_KEY trong file .env")
            return ChatGoogleGenerativeAI(
                google_api_key=self.config.GEMINI_API_KEY,
                model=self.config.GEMINI_MODEL_NAME,
                temperature=0.7,
                convert_system_message_to_human=True  # Bắt buộc cho một số model Gemini
            )
        elif self.provider == "local":
            return ChatOllama(
                base_url=self.config.OLLAMA_BASE_URL,
                model=self.config.LOCAL_MODEL_NAME,
                temperature=0.7
            )

    def get_llm(self):
        """
        Trả về đối tượng LLM đã được khởi tạo.
        """
        return self.llm


from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider

class LLMModels:
    """
    Quickly set up various models:
    - GeminiModel models: requires a paid google genai key
    - AnthropicModel: requires an anthropic key
    - OpenAIModel: requires an openai key
    - GroqModel: requires a groq key
    - OpenRouter models: requires an openrouter key
    - Local models: requires a base_url and api_key
    """
    # Local models
    local_model = OpenAIModel(
        model_name="leon-se/gemma-3-12b-it-FP8-Dynamic",
        provider=OpenAIProvider(
            base_url="http://localhost:2626/v1",
            api_key="i-no-need-no-key-bruh"
        )
    )

    # Gemini models
    gemini_key = " "
    gemini_2_flash = GeminiModel('gemini-2.0-flash',
                                 provider=GoogleGLAProvider(api_key=gemini_key)
                                 )
    gemini_2_flash_lite = GeminiModel('gemini-2.0-flash-lite',
                                      provider=GoogleGLAProvider(api_key=gemini_key)
                                      )

    # OpenRouter models
    open_router_key = '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'
    or_gemini_2_flash = OpenAIModel('google/gemini-2.0-flash-001',
                                    provider=OpenAIProvider(base_url='https://openrouter.ai/api/v1',
                                                            api_key=open_router_key)
                                    )
    or_gemini_2_5_pro = OpenAIModel('google/gemini-2.5-pro-preview-03-25',
                                    provider=OpenAIProvider(base_url='https://openrouter.ai/api/v1',
                                                            api_key=open_router_key)
                                    )
    or_gemma_3_27b_paid = OpenAIModel('google/gemma-3-27b-it',
                                      provider=OpenAIProvider(base_url='https://openrouter.ai/api/v1',
                                                              api_key=open_router_key)
                                      )

    # Groq models
    groq_key = " "
    gr_llama3_70b = GroqModel('llama3-70b-8192',
                              provider=GroqProvider(api_key=groq_key)
                              )
