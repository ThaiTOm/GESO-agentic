import httpx
import os
from typing import Dict, Any
from config import settings
from typing_class.rag_type import QueryRequest

BASE_API_URL = settings.API_URL

client = httpx.AsyncClient()

async def call_database_retrieval_api(request_data: QueryRequest, api_key: str) -> dict:
    print(f"--- Calling Query API for query: {request_data['query']} ---")
    url = f"{BASE_API_URL}/query_rag"

    # .dict() serializes the Pydantic model to a dictionary for the JSON payload
    headers = {"api-key": api_key}

    try:
        response = await client.post(url, json=request_data, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return {"error": f"An error occurred while calling the RAG API: {str(e)}"}

async def call_rag_api(request_data: QueryRequest, api_key: str) -> Dict[str, Any]:
    print(f"--- Calling RAG API for query: {request_data['query']} ---")
    url = f"{BASE_API_URL}/typesense/query_ver_thai"

    # .dict() serializes the Pydantic model to a dictionary for the JSON payload
    headers = {"api-key": api_key}

    try:
        response = await client.post(url, json=request_data, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return {"error": f"An error occurred while calling the RAG API: {str(e)}"}


async def call_analysis_api(aggregation_level: str, query) -> Dict[str, Any]:
    """Makes a GET request to your Analysis endpoint."""
    print(f"--- Calling Analysis API with aggregation: {aggregation_level} ---")
    url = f"{BASE_API_URL}/analysis"
    params = {"aggregation_level": aggregation_level, "query": query}

    try:
        response = await client.get(url, params=params, timeout=60.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return {"error": f"An error occurred while calling the Analysis API: {str(e)}"}