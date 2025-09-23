import httpx
import os
from typing import Dict, Any
from config import settings
from typing_class.rag_type import QueryRequest
from typing_class.speaking import SpeakingRequest

from langchain_core.runnables import RunnableConfig


client = httpx.AsyncClient()


def _get_langsmith_tracing_headers(config: RunnableConfig) -> Dict[str, str]:
    """
    Extracts tracing headers from the RunnableConfig provided by LangGraph.
    """
    headers = {}
    # The 'run_id' in the config is the ID for the *current* execution step (this tool call).
    # We will pass it as the parent_run_id for the service we are calling.
    parent_run_id = config.get("run_id")
    if parent_run_id:
        headers["X-LangSmith-Parent-Run-Id"] = str(parent_run_id)
        print(f"Propagating LangSmith Context: ParentRunID={parent_run_id}")
    # Note: LangSmith is smart. If you provide a parent_run_id, it will automatically
    # associate the new run with the correct trace. Sending the trace_id is not strictly
    # necessary but can be done for robustness if available.
    return headers

async def call_database_retrieval_api(request_data: QueryRequest, api_key: str, config: RunnableConfig) -> dict:
    print(f"--- Calling Query API for query: {request_data['query']} ---")
    url = f"{settings.API_URL}/query_rag"

    # .dict() serializes the Pydantic model to a dictionary for the JSON payload
    headers = {"api-key": api_key}
    print(url, headers)

    tracing_headers = _get_langsmith_tracing_headers(config)
    headers.update(tracing_headers) # Merge them in

    try:
        response = await client.post(url, json=request_data, headers=headers, timeout=100.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return {"error": f"An error occurred while calling the RAG API: {str(e)}"}

async def call_rag_api(request_data: QueryRequest, api_key: str, config: RunnableConfig) -> Dict[str, Any]:
    print(f"--- Calling RAG API for query: {request_data['query']} ---")
    url = f"{settings.API_URL}/typesense/query_ver_thai"

    # .dict() serializes the Pydantic model to a dictionary for the JSON payload
    headers = {"api-key": api_key}
    tracing_headers = _get_langsmith_tracing_headers(config)
    headers.update(tracing_headers)

    print(url, headers)
    try:
        response = await client.post(url, json=request_data, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return {"error": f"An error occurred while calling the RAG API: {str(e)}"}

async def call_analysis_api(aggregation_level: str, query, config: RunnableConfig) -> Dict[str, Any]:
    """Makes a GET request to your Analysis endpoint."""
    print(f"--- Calling Analysis API with aggregation: {aggregation_level} ---")
    url = f"{settings.API_URL}/analysis"
    params = {"aggregation_level": aggregation_level, "query": query}
    headers = _get_langsmith_tracing_headers(config)

    try:
        response = await client.get(url, params=params, headers=headers, timeout=100.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        return {"error": f"An error occurred while calling the Analysis API: {str(e)}"}