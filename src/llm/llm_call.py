# llm_call.py

import asyncio
import httpx
import json
import logging
import threading
from typing import List, Optional, Any, Dict
from types import SimpleNamespace

# Google Gemini imports
import google.generativeai as genai
from google.generativeai import GenerationConfig
from google.generativeai.types import GenerateContentResponse, AsyncGenerateContentResponse

from config import settings

# --- Configuration ---
# Use separate clients for sync and async to avoid issues
async_http_client = httpx.AsyncClient(timeout=60.0)
sync_http_client = httpx.Client(timeout=60.0)


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


# --- MODIFIED: Service class for local vLLM, now supporting multimodal input ---
class LocalService:
    """
    Represents a worker for a local vLLM or other OpenAI-compatible model endpoint.
    This version now correctly handles multimodal inputs (e.g., text and images).
    """
    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url
        self.model_name = model_name
        self.service_id = f"LocalService(url={base_url})"
        logging.info(f"{self.service_id} initialized for model '{model_name}'.")

    def _create_mock_response(self, text_content: str) -> SimpleNamespace:
        """Creates a simple response object with .text and .model_name attributes."""
        return SimpleNamespace(text=text_content, model_name=self.model_name)

    # --- CHANGED: Updated type hint and docstring for multimodal support ---
    async def call_api_async(self, messages: List[Dict[str, Any]], max_output_tokens: int, temperature: float) -> Optional[SimpleNamespace]:
        """
        Makes an ASYNCHRONOUS API call to the local model's CHAT endpoint.
        Supports both text-only and multimodal (text+image) messages.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_output_tokens, "temperature": temperature, "stream": False
        }
        headers = {"Content-Type": "application/json"}
        endpoint_url = f"{self.base_url}/v1/chat/completions"
        logging.info(f"{self.service_id} | Starting async request to {endpoint_url} with payload: {json.dumps(payload, indent=2)}")
        try:
            response = await async_http_client.post(endpoint_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            text_result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logging.info(f"{self.service_id} | Async request finished successfully.")
            return self._create_mock_response(text_result)
        except Exception as e:
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 422:
                 logging.error(f"{self.service_id} | 422 Unprocessable Entity. Server response: {e.response.text}")
            logging.error(f"{self.service_id} | Error calling local model API (async): {e}")
            return None

    # --- CHANGED: Updated type hint and docstring for multimodal support ---
    def call_api_sync(self, messages: List[Dict[str, Any]], max_output_tokens: int, temperature: float) -> Optional[SimpleNamespace]:
        """
        Makes a SYNCHRONOUS API call to the local model's CHAT endpoint.
        Supports both text-only and multimodal (text+image) messages.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_output_tokens, "temperature": temperature, "stream": False
        }
        headers = {"Content-Type": "application/json"}
        endpoint_url = f"{self.base_url}/v1/chat/completions"
        logging.info(f"{self.service_id} | Starting sync request to {endpoint_url} with payload: {json.dumps(payload, indent=2)}")
        try:
            response = sync_http_client.post(endpoint_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            text_result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logging.info(f"{self.service_id} | Sync request finished successfully.")
            return self._create_mock_response(text_result)
        except Exception as e:
            if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 422:
                 logging.error(f"{self.service_id} | 422 Unprocessable Entity. Server response: {e.response.text}")
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
        self.services = {}
        self.selection_lock = threading.Lock()

        if gemini_api_keys:
            self.services['gemini'] = [
                GeminiService(api_key, gemini_model, max_concurrent_per_key)
                for api_key in gemini_api_keys
            ]
            self.gemini_next_service_index = 0
            logging.info(
                f"LLMServicePool initialized with {len(self.services['gemini'])} Gemini services."
            )

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

    async def route_call_async(self, provider: str, request_data: Any, max_output_tokens: int, temperature: float):
        """Routes an ASYNC call to the specified provider."""
        if provider == "gemini":
            selected_service = self._get_next_gemini_service()
            # NOTE: Gemini's SDK has a different way of handling multimodal input.
            # This route currently expects request_data to be a simple string.
            return await selected_service.call_api_async(request_data, max_output_tokens, temperature)
        elif provider == "local":
            selected_service = self.services['local'][0]
            # Local's method now expects a list of message dicts that can be multimodal.
            return await selected_service.call_api_async(request_data, max_output_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}.")

    def route_call_sync(self, provider: str, request_data: Any, max_output_tokens: int, temperature: float):
        """Routes a SYNC call to the specified provider."""
        if provider == "gemini":
            selected_service = self._get_next_gemini_service()
            return selected_service.call_api_sync(request_data, max_output_tokens, temperature)
        elif provider == "local":
            selected_service = self.services['local'][0]
            return selected_service.call_api_sync(request_data, max_output_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}.")

# --- SINGLETON INSTANCE ---
service_pool = LLMServicePool(
    gemini_api_keys=settings.GEMINI_API_KEY,
    gemini_model=settings.GEMINI_MODEL_NAME,
    local_model_url=settings.MODEL_URL,
    local_model_name=settings.LOCAL_MODEL_NAME,
    max_concurrent_per_key=1
)