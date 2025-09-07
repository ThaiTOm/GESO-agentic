# llm_call.py
import asyncio
# --- MODIFIED: Import both sync and async response types for proper hinting ---
from google.generativeai.types import GenerateContentResponse, AsyncGenerateContentResponse

import google.generativeai as genai
import httpx
import json
import logging
import threading
from typing import Type, TypeVar, List, Optional

from google.generativeai import GenerationConfig
from pydantic import BaseModel, ValidationError
from config import settings

# --- Configuration ---
MODEL_URL = settings.MODEL_URL
async_http_client = httpx.AsyncClient(timeout=60.0)
T = TypeVar("T", bound=BaseModel)

# --- Core LLM Service and Pool Classes ---

class GeminiService:
    """
    Represents a single worker for the Gemini API using one API key.
    Now includes both synchronous and asynchronous calling methods.
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

    async def call_api_async(self, prompt: str, max_output_tokens: int, temperature: float) -> Optional[AsyncGenerateContentResponse]:
        """
        Acquires a semaphore lock and makes an ASYNCHRONOUS API call.
        """
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

    def call_api_sync(self, prompt: str, max_output_tokens: int, temperature: float) -> Optional[GenerateContentResponse]:
        """
        Makes a SYNCHRONOUS API call. This is required for LangChain's _generate method.
        """
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


class GeminiServicePool:
    """
    Manages a pool of GeminiService instances and routes requests.
    Uses a round-robin strategy to cycle through services for each call.
    """

    def __init__(self, api_keys: List[str], model_name: str, max_concurrent_per_key: int):
        if not api_keys:
            raise ValueError("API keys list cannot be empty.")
        self.services = [
            GeminiService(api_key, model_name, max_concurrent_per_key)
            for api_key in api_keys
        ]
        # --- NEW: State for round-robin selection ---
        self.next_service_index = 0
        # A lock to prevent race conditions when multiple concurrent calls try to get the next service
        self.selection_lock = threading.Lock()
        logging.info(
            f"GeminiServicePool initialized with {len(self.services)} services "
            f"using a round-robin routing strategy."
        )

    # --- NEW: Round-robin selection logic ---
    def _get_next_service_round_robin(self) -> GeminiService:
        """
        Atomically gets the next service in the list in a round-robin fashion.
        This method is thread-safe.
        """
        with self.selection_lock:
            # Select the service at the current index
            service = self.services[self.next_service_index]
            # Increment the index for the next call, wrapping around if necessary
            self.next_service_index = (self.next_service_index + 1) % len(self.services)
            logging.info(f"Routing to {service.service_id}. Next index will be {self.next_service_index}.")
            return service

    # --- REMOVED: No longer needed ---
    # def _get_least_busy_service(self) -> GeminiService:
    #     """Finds the service with the minimum number of active async requests."""
    #     return min(self.services, key=lambda service: service.active_requests)

    # --- MODIFIED: Use the new round-robin strategy ---
    async def route_call_async(self, prompt: str, max_output_tokens: int, temperature: float) -> Optional[AsyncGenerateContentResponse]:
        """
        Selects the next service using round-robin and delegates the ASYNC API call to it.
        """
        selected_service = self._get_next_service_round_robin()
        return await selected_service.call_api_async(prompt, max_output_tokens, temperature)

    # --- MODIFIED: Use the new round-robin strategy ---
    def route_call_sync(self, prompt: str, max_output_tokens: int, temperature: float) -> Optional[GenerateContentResponse]:
        """
        Selects the next service using round-robin and delegates the SYNC API call to it.
        """
        selected_service = self._get_next_service_round_robin()
        return selected_service.call_api_sync(prompt, max_output_tokens, temperature)


# --- SINGLETON INSTANCE ---
# This is the single pool instance that your LangChain model will use.
service_pool = GeminiServicePool(
    api_keys=settings.GEMINI_API_KEY,
    model_name=settings.GEMINI_MODEL_NAME,
    max_concurrent_per_key=1
)

# --- DEPRECATED FUNCTIONS ---
# The functions below are now replaced by your CustomGeminiChatModel and LCEL chains.
# They are kept here for reference but should no longer be used in your graph.

# async def cloud_call_async(prompt: str, max_output_tokens: int = 100, temperature: float = 0.7):
#     """DEPRECATED: Use CustomGeminiChatModel.ainvoke() instead."""
#     response = await service_pool.route_call_async(prompt, max_output_tokens, temperature)
#     return response.text if response else ""

async def local_call_async(prompt: str, max_tokens: int, temperature: float) -> str:
    """
    Asynchronous call to a local model endpoint.
    NOTE: This should also be wrapped in its own LangChain model (e.g., using ChatOpenAI
    with a custom api_base) for full integration.
    """
    # ... (implementation is fine) ...
    payload = {
        "model": "leon-se/gemma-3-12b-it-FP8-Dynamic", "prompt": prompt,
        "max_tokens": max_tokens, "temperature": temperature, "stream": False
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = await async_http_client.post(MODEL_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("text", "")
    except httpx.RequestError as e:
        logging.error(f"Error calling local model API: {e}")
        return ""
    except (json.JSONDecodeError, IndexError) as e:
        logging.error(f"Error parsing response from local model API: {e}")
        return ""

async def get_structured_llm_output(
    prompt: str,
    pydantic_model: Type[T],
    cloud: bool = False,
    max_tokens: int = 1024
) -> T | None:
    """
    Calls an LLM, asks for JSON output, and parses it into a Pydantic model.
    This function replaces the need for proprietary features like `with_structured_output`.
    """
    # Append instructions to the prompt to ensure JSON output
    json_prompt = f"""
    {prompt}

    Provide your response exclusively in a valid JSON format that adheres to the following Pydantic schema. Do not include any explanatory text, comments, or markdown formatting like ```json.

    JSON Schema:
    {pydantic_model.schema_json(indent=2)}
    """

    # Call the selected LLM (either cloud or local)
    if cloud:
        response_text = await cloud_call_async(json_prompt, max_output_tokens=max_tokens, temperature=0.0)
    else:
        response_text = await local_call_async(json_prompt, max_tokens=max_tokens, temperature=0.0)

    if not response_text:
        logging.error("LLM returned an empty response.")
        return None

    # Attempt to parse the LLM's string response into the Pydantic model
    try:
        # Clean the response in case the model wraps it in markdown code fences
        cleaned_text = response_text.strip().removeprefix("```json").removesuffix("```").strip()
        # Load the cleaned text into a Python dictionary
        data = json.loads(cleaned_text)
        # Validate and create the Pydantic model instance
        return pydantic_model(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        # Log detailed errors for easier debugging
        logging.error(f"Failed to parse LLM output into {pydantic_model.__name__}. Error: {e}")
        logging.error(f"Raw LLM Output that caused the error:\n---\n{response_text}\n---")
        return None


async def get_raw_llm_output(prompt: str, cloud: bool = False, max_tokens: int = 1024) -> str:
    if cloud:
        response_text = await cloud_call_async(prompt, max_output_tokens=max_tokens, temperature=0.0).text
    else:
        response_text = await local_call_async(prompt, max_tokens=max_tokens, temperature=0.0)
    return response_text.strip()