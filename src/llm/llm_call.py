# llm_call.py

import asyncio
import httpx
import json
import logging
import threading
from typing import List, Optional
from types import SimpleNamespace  # <--- NEW: For creating mock response objects

# Google Gemini imports
import google.generativeai as genai
from google.generativeai import GenerationConfig
from google.generativeai.types import GenerateContentResponse, AsyncGenerateContentResponse

from config import settings

# --- Configuration ---
# Use separate clients for sync and async to avoid issues
async_http_client = httpx.AsyncClient(timeout=60.0)
sync_http_client = httpx.Client(timeout=60.0)  # <--- NEW: Sync client for local calls


# --- Core LLM Service Classes ---

class GeminiService:
    """
    Represents a single worker for the Gemini API using one API key.
    (This class remains unchanged)
    """

    def __init__(self, api_key: str, model_name: str, max_concurrent_requests: int):
        self.api_key = api_key
        self.model_name = model_name
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.active_requests = 0
        self.service_id = f"Service(key=...{api_key[-4:]})"
        self.model = genai.GenerativeModel(self.model_name)
        logging.info(
            f"{self.service_id} initialized with model '{model_name}' "
            f"and a concurrency limit of {max_concurrent_requests}."
        )

    async def call_api_async(self, prompt: str, max_output_tokens: int, temperature: float) -> Optional[
        AsyncGenerateContentResponse]:
        """Makes an ASYNCHRONOUS API call to Gemini."""
        async with self.semaphore:
            self.active_requests += 1
            logging.info(f"{self.service_id} | Starting async request. Active requests: {self.active_requests}")
            try:
                genai.configure(api_key=self.api_key)
                generation_config = GenerationConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                )
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=generation_config
                )
                logging.info(f"{self.service_id} | Async request finished successfully.")
                return response
            except Exception as e:
                logging.error(f"{self.service_id} | Error calling Google Gemini API (async): {e}")
                return None
            finally:
                self.active_requests -= 1

    def call_api_sync(self, prompt: str, max_output_tokens: int, temperature: float) -> Optional[
        GenerateContentResponse]:
        """Makes a SYNCHRONOUS API call to Gemini."""
        logging.info(f"{self.service_id} | Starting sync request.")
        try:
            genai.configure(api_key=self.api_key)
            generation_config = GenerationConfig(
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            )
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            logging.info(f"{self.service_id} | Sync request finished successfully.")
            return response
        except Exception as e:
            logging.error(f"{self.service_id} | Error calling Google Gemini API (sync): {e}")
            return None


# --- NEW: Service class for the local model ---
class LocalService:
    """
    Represents a worker for a local TGI/Ollama-compatible model endpoint.
    It mimics the GeminiService interface for seamless integration into the pool.
    """

    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url
        self.model_name = model_name
        self.service_id = f"LocalService(url={base_url})"
        logging.info(f"{self.service_id} initialized for model '{model_name}'.")

    def _create_mock_response(self, text_content: str) -> SimpleNamespace:
        """
        Creates a mock response object that has a `.text` attribute,
        similar to Gemini's response, so the LangChain model can process it.
        We also add model_name for consistent generation_info.
        """
        return SimpleNamespace(text=text_content, model_name=self.model_name)

    async def call_api_async(self, prompt: str, max_output_tokens: int, temperature: float) -> Optional[
        SimpleNamespace]:
        """Makes an ASYNCHRONOUS API call to the local model."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": max_output_tokens,
            "temperature": temperature, "stream": False
        }
        headers = {"Content-Type": "application/json"}
        logging.info(f"{self.service_id} | Starting async request.")
        try:
            response = await async_http_client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            text_result = data.get("choices", [{}])[0].get("text", "")
            logging.info(f"{self.service_id} | Async request finished successfully.")
            return self._create_mock_response(text_result)
        except Exception as e:
            logging.error(f"{self.service_id} | Error calling local model API (async): {e}")
            return None

    def call_api_sync(self, prompt: str, max_output_tokens: int, temperature: float) -> Optional[SimpleNamespace]:
        """Makes a SYNCHRONOUS API call to the local model."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        logging.info(f"{self.service_id} | Starting sync request.")
        try:
            response = sync_http_client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            text_result = data.get("choices", [{}])[0].get("text", "")
            logging.info(f"{self.service_id} | Sync request finished successfully.")
            return self._create_mock_response(text_result)
        except Exception as e:
            logging.error(f"{self.service_id} | Error calling local model API (sync): {e}")
            return None


# --- REFACTORED: From GeminiServicePool to a more generic LLMServicePool ---
class LLMServicePool:
    """
    Manages a pool of different LLM services (e.g., Gemini, Local)
    and routes requests to the appropriate provider.
    """

    def __init__(self, gemini_api_keys: List[str], gemini_model: str, local_model_url: str, local_model_name: str,
                 max_concurrent_per_key: int):
        self.services = {}  # Use a dictionary to store services by provider name
        self.selection_lock = threading.Lock()

        # Initialize Gemini services if keys are provided
        if gemini_api_keys:
            self.services['gemini'] = [
                GeminiService(api_key, gemini_model, max_concurrent_per_key)
                for api_key in gemini_api_keys
            ]
            self.gemini_next_service_index = 0
            logging.info(
                f"LLMServicePool initialized with {len(self.services['gemini'])} Gemini services."
            )

        # Initialize Local service if URL is provided
        if local_model_url:
            self.services['local'] = [LocalService(local_model_url, local_model_name)]
            logging.info(
                f"LLMServicePool initialized with 1 Local service."
            )

        if not self.services:
            raise ValueError("No services were initialized. Provide API keys or a local model URL.")

    def _get_next_gemini_service(self) -> GeminiService:
        """Atomically gets the next Gemini service in a round-robin fashion."""
        with self.selection_lock:
            service = self.services['gemini'][self.gemini_next_service_index]
            self.gemini_next_service_index = (self.gemini_next_service_index + 1) % len(self.services['gemini'])
            logging.info(f"Routing to {service.service_id}. Next index will be {self.gemini_next_service_index}.")
            return service

    async def route_call_async(self, provider: str, prompt: str, max_output_tokens: int, temperature: float):
        """Routes an ASYNC call to the specified provider."""
        if provider == "gemini":
            if 'gemini' not in self.services:
                raise ValueError("Gemini provider selected, but no Gemini services are configured.")
            selected_service = self._get_next_gemini_service()
            return await selected_service.call_api_async(prompt, max_output_tokens, temperature)
        elif provider == "local":
            if 'local' not in self.services:
                raise ValueError("Local provider selected, but no local service is configured.")
            # Local service doesn't need round-robin as there's only one endpoint
            selected_service = self.services['local'][0]
            return await selected_service.call_api_async(prompt, max_output_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}. Available providers: {list(self.services.keys())}")

    def route_call_sync(self, provider: str, prompt: str, max_output_tokens: int, temperature: float):
        """Routes a SYNC call to the specified provider."""
        if provider == "gemini":
            if 'gemini' not in self.services:
                raise ValueError("Gemini provider selected, but no Gemini services are configured.")
            selected_service = self._get_next_gemini_service()
            return selected_service.call_api_sync(prompt, max_output_tokens, temperature)
        elif provider == "local":
            if 'local' not in self.services:
                raise ValueError("Local provider selected, but no local service is configured.")
            selected_service = self.services['local'][0]
            return selected_service.call_api_sync(prompt, max_output_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}. Available providers: {list(self.services.keys())}")


# --- SINGLETON INSTANCE ---
# This single pool instance now manages ALL connections.
service_pool = LLMServicePool(
    gemini_api_keys=settings.GEMINI_API_KEY,
    gemini_model=settings.GEMINI_MODEL_NAME,
    local_model_url=settings.MODEL_URL,  # Assumes local URL is in settings.MODEL_URL
    local_model_name=settings.LOCAL_MODEL_NAME,  # Assumes local model name is in settings
    max_concurrent_per_key=1
)