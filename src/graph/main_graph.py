# graph_builder.py

from typing import TypedDict, Any, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from typing_class.rag_type import QueryRequest
from typing_class.graph_type import OrchestratorState
from graph.call_api_routes import call_rag_api, call_analysis_api
from context_engine.rag_prompt import DECENTRALIZATION_PROMPT

# Your custom, model-agnostic LLM caller
from llm.llm_call import get_structured_llm_output


# --- Define Pydantic models for structured LLM outputs ---
# These ensure the LLM provides predictable, parsable JSON responses.

class RelevantPlotsDecision(BaseModel):
    """Defines the output for the plot filtering decision."""
    relevant_segments: list[str] = Field(
        description="A list of product segments that are directly relevant to the user's query. This list must ONLY contain values from the provided 'Available Segments'."
    )

class AuthorizationDecision(BaseModel):
    """The decision of the authorization check based on user role and query."""
    authorized: bool = Field(description="Whether the user is authorized to ask this query based on their role.")
    reason: str = Field(description="A brief explanation for the decision, especially if denied.")


class ToolRouterDecision(BaseModel):
    """The decision of which tool to use for an authorized query."""
    tool_name: Literal["rag", "analysis"] = Field(description="The name of the tool to use.")
    aggregation_level: Literal["monthly", "quarterly"] = Field(
        description="The aggregation level for analysis, ONLY if the tool is 'analysis'.",
        default="quarterly"
    )


# --- Node Definitions for the Graph ---
# Each node is a function that performs a specific step in the process.

async def authorization_node(state: OrchestratorState) -> dict:
    """
    Node 1: The security gate. Checks if the user's query is permitted based on their role.
    """
    print("--- NODE: Authorization Check ---")
    query = state['query']

    prompt = f"""
    You are a strict data access security guard. Based on the provided rules, user role, and user query, decide if the query is allowed.

    **RULES:**
    {DECENTRALIZATION_PROMPT}

    **USER INFORMATION:**
    - Role: {state.get('user_role', 'Unknown')}
    - User ID: {state.get('user_id', 'Unknown')}

    **USER QUERY:**
    "{query}"

    Is the user authorized to ask this question based on their role and the rules? Provide your decision.
    """

    # Use your custom LLM caller to get a structured response
    # You can switch between cloud=True (Gemini) and cloud=False (local) here
    decision = await get_structured_llm_output(prompt, AuthorizationDecision, cloud=True)

    if not decision:
        # Fallback in case the LLM fails to produce valid JSON
        return {
            "is_authorized": False,
            "authorization_reason": "Internal system error: Could not process the authorization request."
        }

    print(f"--- AUTHORIZATION DECISION: Authorized={decision.authorized}, Reason='{decision.reason}' ---")
    return {
        "is_authorized": decision.authorized,
        "authorization_reason": decision.reason,
    }


async def tool_router_node(state: OrchestratorState) -> dict:
    """
    Node 2: The dispatcher. If authorized, decides which tool to use.
    """
    print("--- NODE: Tool Router ---")
    query = state['query']

    prompt = f"""
    You are an expert tool router. The user query has already been approved for access.
    Your job is to decide which tool to use:
    1. `rag`: Use for questions about reports, documents, general information, policies (CTKM/CSBH), product info, etc.
    2. `analysis`: Use specifically for questions requesting trend analysis, time-series data, or explicit data aggregation (e.g., "show me the trend", "analyze sales").

    User Query: "{query}"

    Based on the query, choose the correct tool and, if choosing 'analysis', determine the aggregation level ('monthly' or 'quarterly').
    """

    decision = await get_structured_llm_output(prompt, ToolRouterDecision, cloud=True)

    if not decision:
        # Fallback if the router fails
        return {"tool_to_use": "none", "tool_input": {}}

    tool_name = decision.tool_name
    print(f"--- ROUTER DECISION: Tool='{tool_name}' ---")

    tool_input = {}
    if tool_name == "rag":
        # Prepare the input for the RAG API by creating a QueryRequest object
        tool_input = QueryRequest(
            query=query,
            top_k=state.get("top_k", 10),
            include_sources=state.get("include_sources", True),
            chat_history=state.get("chat_history", []),
            prompt_from_user=state.get("prompt_from_user", ""),
            cloud_call=state.get("cloud_call", True),
            voice=state.get("voice", False)
        ).dict()
    elif tool_name == "analysis":
        # Prepare the input for the Analysis API
        tool_input = {"aggregation_level": decision.aggregation_level}

    return {"tool_to_use": tool_name, "tool_input": tool_input}


async def api_caller_node(state: OrchestratorState) -> dict:
    """
    Node 3: The worker. Executes the API call to the selected backend service.
    """
    print(state)
    print("--- NODE: API Caller ---")
    tool_to_use = state['tool_to_use']
    tool_input = state['tool_input']

    response = {}
    if tool_to_use == "rag":
        print(tool_input)
        response = await call_rag_api(tool_input, api_key=state["api_key"])
    elif tool_to_use == "analysis":
        response = await call_analysis_api(aggregation_level=tool_input.get("aggregation_level", "quarterly"), query=state['query'])

    return {"final_response": response}


# --- Conditional Logic for Branching ---

def check_authorization(state: OrchestratorState) -> Literal["authorized", "unauthorized"]:
    """
    This function directs the graph's flow after the authorization check.
    """
    if state["is_authorized"]:
        return "authorized"
    else:
        return "unauthorized"


async def summarize_and_filter_analysis_node(state: OrchestratorState) -> dict:
    """
    Node 4: Post-processes the analysis result.
    1. Summarizes the technical text for the user.
    2. Filters the plots to only show what is relevant to the user's query.
    """
    print("--- NODE: Summarize and Filter Analysis ---")

    full_response = state['final_response']
    user_query = state['query']  # We need the original query for context

    # --- Part 1: Summarize the Text (Same as before) ---
    technical_summary = full_response.get("text_summary_for_llm")
    human_friendly_summary = technical_summary  # Default to the original text

    if technical_summary:
        summary_prompt = f"""
        Bạn là một nhà phân tích kinh doanh hữu ích. Hãy tóm tắt báo cáo kỹ thuật sau thành một đoạn văn rõ ràng, dễ hiểu cho người dùng doanh nghiệp.
        Tập trung vào những thông tin chi tiết chính, và chỉ cung cấp thông tin theo câu hỏi của người dùng.
        Không sử dụng markdown. Hãy cung cấp một bản tóm tắt đơn giản, bằng ngôn ngữ tự nhiên.
        
        **Câu hỏi của người dùng:** "{user_query}"
        
        Technical Report:
        {technical_summary}
        """


        from llm.llm_call import get_raw_llm_output
        summary_result = await get_raw_llm_output(summary_prompt, cloud=True, max_tokens=512)
        if summary_result:  # Only update if the LLM gave a valid response
            human_friendly_summary = summary_result

    # --- Part 2: Filter the Plots (New Logic) ---
    original_plots = full_response.get("plots_for_client", {})
    filtered_plots = original_plots  # Default to all plots

    if original_plots:
        available_segments = list(original_plots.keys())

        filter_prompt = f"""
        You are an intelligent data filter. Your job is to identify which of the available data segments are relevant to the user's query.

        User's Original Query: "{user_query}"

        Available Segments: {available_segments}

        Based on the user's query, which of the "Available Segments" should be shown?
        - If the user asks a general question like "analyze the trends", then all segments are relevant.
        - If the user specifically mentions one or more segments (e.g., "how is BÁNH TƯƠI and Kẹo doing?"), then only those are relevant.
        """

        # Use our new Pydantic model to get a structured list
        decision = await get_structured_llm_output(filter_prompt, RelevantPlotsDecision, cloud=True)

        if decision and decision.relevant_segments:
            print(f"--- FILTER DECISION: Keeping segments {decision.relevant_segments} ---")
            # Build a new dictionary containing only the relevant plots
            filtered_plots = {
                segment: original_plots[segment]
                for segment in decision.relevant_segments
                if segment in original_plots
            }
        else:
            print("--- FILTER DECISION: LLM failed to identify segments, keeping all plots as a fallback. ---")

    # --- Part 3: Assemble the Final, Cleaned-Up Response ---

    final_cleaned_response = {
        "text_summary_for_llm": human_friendly_summary,
        "plots_for_client": filtered_plots
    }

    return {"final_response": final_cleaned_response}

def should_summarize_analysis(state: OrchestratorState) -> Literal["summarize", "end"]:
    """
    This function directs the flow after the API call. It checks if the
    analysis tool was the one that just ran.
    """
    print("--- EDGE: Checking if summarization is needed ---")
    if state.get("tool_to_use") == "analysis":
        print("--- DECISION: Route to summarizer ---")
        return "summarize"
    else:
        print("--- DECISION: End graph ---")
        return "end"

# --- Graph Assembly ---

def build_graph():
    """
    This function assembles all the nodes and edges into a runnable LangGraph application.
    """
    workflow = StateGraph(OrchestratorState)

    # 1. Add all the nodes to the graph, including the new one
    workflow.add_node("authorization_checker", authorization_node)
    workflow.add_node("tool_router", tool_router_node)
    workflow.add_node("api_caller", api_caller_node)
    workflow.add_node("summarizer", summarize_and_filter_analysis_node) # <--- ADD NEW NODE

    # 2. Set the entry point
    workflow.set_entry_point("authorization_checker")

    # 3. Define the first branch (authorization) - UNCHANGED
    workflow.add_conditional_edges(
        "authorization_checker",
        check_authorization,
        {
            "authorized": "tool_router",
            "unauthorized": END,
        }
    )

    # 4. Define the path from router to API caller - UNCHANGED
    workflow.add_edge("tool_router", "api_caller")

    # 5. Define the NEW second branch (after the API call)
    workflow.add_conditional_edges(
        "api_caller",             # <--- The source of the branch is the api_caller
        should_summarize_analysis, # <--- The new decision function
        {
            "summarize": "summarizer", # <--- If 'summarize', go to the new node
            "end": END,                # <--- If 'end', the process is finished
        }
    )

    # 6. After the summarizer runs, the process is finished
    workflow.add_edge("summarizer", END)

    # Compile and return the graph
    graph = workflow.compile()
    return graph