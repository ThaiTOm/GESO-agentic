import base64
import os
from google import genai
from google.genai import types
import requests
import json
import logging
import time
from config import settings

env = settings
MODEL_URL = env.MODEL_URL

def cloud_call(prompt, max_output_tokens=256, temperature=0.0):
    client = genai.Client(
        api_key=env.GEMINI_API_KEY,
    )
    # check cloud call valid
    logging.debug(f"API key: {env.GEMINI_API_KEY}")

    model = env.GEMINI_MODEL_NAME
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )
    result = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    ).text
    time.sleep(2)
    return result

def local_call(prompt, max_tokens=256, temperature=0.0):
    payload = {
        "model": "leon-se/gemma-3-12b-it-FP8-Dynamic",
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False
    }

    # Headers
    headers = {
        "Content-Type": "application/json"
    }

    # Send the request
    response = requests.post(MODEL_URL, headers=headers, data=json.dumps(payload)).json()
    if "choices" in response:
        return response["choices"][0]["text"]
    else:
        return ""

async def call_llm(prompt, max_tokens=256, temperature=0.0, cloud=False):
    WHICH_MODEL = env.WHICH_MODEL
    logging.debug(f"LLM model: {WHICH_MODEL}")
    if cloud == False:
        # Call local model
        result = local_call(prompt, max_tokens=max_tokens, temperature=temperature)
        logging.debug(f"Result: {result}")
        return result

    elif cloud:
        # Call cloud model
        return cloud_call(prompt, max_output_tokens=max_tokens, temperature=temperature)
    else:
        raise ValueError("Invalid model selection. Choose 'local-serve' or 'cloud-serve'.")