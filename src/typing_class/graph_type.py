from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Union, TypedDict, Literal
from datetime import datetime


# The state is a dictionary that tracks data as it moves through the graph.
class OrchestratorState(TypedDict):
    query: str
    user_role: str
    user_id: str
    api_key: str
    is_authorized: bool
    authorization_reason: str
    tool_to_use: Literal["rag", "analysis", "none"]
    tool_input: dict
    final_response: Any

    top_k: int
    include_sources: bool
    chat_history: list[dict]
    prompt_from_user: str
    cloud_call: bool
    voice: bool


class OrchestratorRequest(BaseModel):
    query: str = ""
    user_role: str = "duythai"
    user_id: str = "duythai"
    api_key: str = ""
    final_response: Any = ""
    top_k: int = 10
    include_sources: bool = True
    chat_history: list[dict] = []
    prompt_from_user: str = ""
    cloud_call: bool = True
    voice: bool = False


class OrchestratorResponse(BaseModel):
    response: Any
