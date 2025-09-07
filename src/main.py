# orchestrator_main.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from utils.logging_config import *
from typing_class.graph_type import OrchestratorRequest, OrchestratorResponse
from graph.main_graph import build_graph
from config import settings
import os

os.environ["LANGSMITH_TRACING_V2"] = settings.LANGSMITH_TRACING_V2
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
# --- FastAPI Application Setup ---

app = FastAPI(
    title="Policy-Aware Orchestrator Agent",
    description="Orchestrates calls to backend RAG and Data Analysis services after enforcing access policies.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware (assuming you have this file)
app.add_middleware(LoggingMiddleware)

# Compile the LangGraph application once at startup.
# This is efficient as the graph structure doesn't change.
langgraph_app = build_graph()

# --- API Endpoint Definition ---

@app.post("/orchestrate", response_model=OrchestratorResponse)
async def orchestrate_query(request: OrchestratorRequest):
    """
    Receives a natural language query and user info, uses LangGraph to enforce security policy,
    routes to the correct backend service, and returns the result.
    """
    # Invoke the graph asynchronously and wait for the final state

    final_state = await langgraph_app.ainvoke(request)

    # --- Handle the Final State ---

    # IMPORTANT: Check the result of the authorization step.
    # If the user was not authorized, the graph will have ended early.
    if not final_state.get("is_authorized"):
        # Return an HTTP 403 Forbidden error to the client.
        # This is the correct and secure way to handle unauthorized access.
        raise HTTPException(
            status_code=403,
            detail=f"Access Denied: {final_state.get('authorization_reason', 'You do not have permission for this request.')}"
        )

    # If the user was authorized, the graph ran to completion.
    # Return the final response from the tool.
    return OrchestratorResponse(response=final_state.get("final_response"))

# To run this server from your terminal:
# uvicorn main:app --host 0.0.0.0 --port 8001 --reload