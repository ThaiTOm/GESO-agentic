import json

from fastapi import Form, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Union
from datetime import datetime


class Chatbot(BaseModel):
    chatbot_id: str
    name: str
    description: Optional[str] = None
    chatbot_api_key: Optional[str] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class ChatbotListResponse(BaseModel):
    status: str
    chatbots: List[Chatbot]

class Document(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    chunk_text: str
    chunk_num: int
    page_num: Optional[int] = None
    uploaded_at: Optional[datetime] = None

class DocumentListResponse(BaseModel):
    status: str
    chatbot_id: str
    documents: List[Document]

class ProcessingResponse(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    num_chunks: int
    # metadata: Dict[str, Any]
    status: str
    message: str

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 20
    include_sources: Optional[bool] = True
    chat_history: Optional[List[Dict[str, Any]]] = None
    prompt_from_user: Optional[str] = ""
    cloud_call: Optional[bool] = False
    voice: Optional[bool] = False
    user_id: str = "duythai"
    user_role: str = 'duythai'


class ToolRequest(BaseModel):
    query: str
    top_k: Optional[int] = 20
    include_sources: Optional[bool] = True
    chat_history: Optional[List[Dict[str, Any]]] = None
    prompt_from_user: str
    cloud_call: Optional[bool] = False
    tool_usage: str = None

class QueryResponse(BaseModel):
    query: str
    answer: str
    context: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    # metadata: Dict[str, Any]
    voice: Optional[str] = None


class ChatbotCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

class ChatbotResponse(BaseModel):
    status: str
    message: str
    chatbot: Chatbot

class SearchRequest(BaseModel):
    chatbot_name: str
    query: str
    limit: Optional[int] = 10

class VectorSearchRequest(BaseModel):
    chatbot_name: str
    vector: List[float]
    limit: Optional[int] = 10

class HybridSearchRequest(BaseModel):
    chatbot_name: str
    query: str
    vector: List[float]
    limit: Optional[int] = 10

class MultiSearchRequest(BaseModel):
    searches: List[Dict[str, Any]]
    class Config:
        schema_extra = {
            "example": {
                "searches": [
                    {
                        "collection": "chatbot_master",
                        "q": "nội dung cần tìm",
                        "query_by": "text",
                        "limit": 10
                    },
                    {
                        "collection": "chatbot_slave",
                        "q": "từ khóa khác",
                        "query_by": "text",
                        "limit": 5
                    }
                ]
            }
        }

# Add these model classes
class SuggestQuestionsRequest(BaseModel):
    previous_response: str
    file_name: str
    context: str
    chatbot_name: Optional[str] = None
    query: Optional[str] = None
    cloud_call: Optional[bool] = False

class SuggestQuestionsResponse(BaseModel):
    suggested_questions: List[str]

class ChatbotInfoRequest(BaseModel):
    api_key: str

class ChatbotInfoResponse(BaseModel):
    chatbot_name: str
    status: str = "success"

class ToolInfoResponse(BaseModel):
    """
    Response model for the tools endpoint.

    Attributes:
        total_tools: The total number of available tools
        tools: A list of tool information dictionaries
        status: The status of the request
    """
    total_tools: int
    tools: List[Dict[str, str]]
    status: str = "success"

class Tool(BaseModel):
    """
    Defines a tool that can be used by an agent.

    Attributes:
        name: The name of the tool
        prompt: The prompt to be used with the tool
        link: The URL endpoint for sending/receiving output
        input_schema: The expected input schema for the tool
        output_schema: The expected output schema from the tool
        description: Optional description of what the tool does
    """
    name: str
    prompt: str
    link: str
    explain: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    description: Optional[str] = None

class ToolOutput(BaseModel):
    """
    Defines the output from a tool execution.

    Attributes:
        tool_name: The name of the tool that was executed
        output: The output data from the tool
        status: The status of the tool execution
        error: Optional error message if the tool execution failed
    """
    tool_name: str
    output: Any
    status: str = "success"
    error: Optional[str] = None

class RowRule(BaseModel):
    id: int
    column: str
    filterType: str
    value: str

class PermissionConfig(BaseModel):
    botName: str
    dataSourceIdentifier: str
    users: List[str]
    columnPermissions: Dict[str, Dict[str, str]]
    rowRules: Dict[str, List[RowRule]]

def parse_permissions(permissions_str: str = Form(..., description="A JSON string containing the authorization rules.")) -> PermissionConfig:
    """
    Parses the JSON string from the form data into a PermissionConfig model.
    Raises HTTPException if parsing or validation fails.
    """
    try:
        permissions_data = json.loads(permissions_str)
        return PermissionConfig(**permissions_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in the 'permissions' field.")
    except Exception as e: # Catches Pydantic validation errors
        raise HTTPException(status_code=422, detail=f"Invalid permission data: {e}")
