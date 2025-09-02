# llm_caller.py
import google.generativeai as genai
import httpx
import json
import logging
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError

# Assuming this file exists and contains your settings
from config import settings

# --- Configuration ---
# This is the standard way to configure the Gemini client.
# It should be done once when the application starts.
genai.configure(api_key=settings.GEMINI_API_KEY)
MODEL_URL = settings.MODEL_URL

# Use a single async httpx client for the application's lifecycle for local calls
async_http_client = httpx.AsyncClient(timeout=60.0)

# Define a generic TypeVar for Pydantic models to improve type hinting
T = TypeVar("T", bound=BaseModel)

# --- Core Asynchronous LLM Functions ---

async def cloud_call_async(prompt: str, max_output_tokens: int, temperature: float) -> str:
    """
    Asynchronously calls the Google Gemini API using the standard SDK.
    This is the correct, "default" implementation.
    """
    try:
        # 1. Instantiate the generative model
        model = genai.GenerativeModel(settings.GEMINI_MODEL_NAME)

        # 2. Create the generation configuration
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        # 3. Call the asynchronous generation method on the model instance
        response = await model.generate_content_async(
            prompt,
            generation_config=generation_config
        )

        # 4. Return the text part of the response
        return response.text
    except Exception as e:
        logging.error(f"Error calling Google Gemini API: {e}")
        # Return an empty string to prevent crashes downstream
        return ""

async def local_call_async(prompt: str, max_tokens: int, temperature: float) -> str:
    """Asynchronous call to a local model endpoint."""
    payload = {
        # This can also be configured from your settings file
        "model": "leon-se/gemma-3-12b-it-FP8-Dynamic",
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = await async_http_client.post(MODEL_URL, headers=headers, json=payload)
        response.raise_for_status() # Raise an error for bad responses (4xx or 5xx)
        data = response.json()
        # Safely access nested dictionary keys to avoid errors
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
        response_text = await cloud_call_async(prompt, max_output_tokens=max_tokens, temperature=0.0)
    else:
        response_text = await local_call_async(prompt, max_tokens=max_tokens, temperature=0.0)
    return response_text.strip()