# graph_builder.py
from typing import Literal
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from typing_class.rag_type import QueryRequest
from typing_class.graph_type import OrchestratorState
from graph.call_api_routes import call_rag_api, call_analysis_api, call_database_retrieval_api
from context_engine.rag_prompt import DECENTRALIZATION_PROMPT

from types import SimpleNamespace

# Your custom, model-agnostic LLM caller
from llm.llm_langchain import cloud_llm_service

llm = cloud_llm_service

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
    ### MODIFIED: Added 'retrieval_from_database' to the list of available tools ###
    tool_name: Literal["retrieval_from_database", "rag", "analysis"] = Field(description="The name of the tool to use.")
    aggregation_level: Literal["monthly", "quarterly"] = Field(
        description="The aggregation level for analysis, ONLY if the tool is 'analysis'.",
        default="quarterly"
    )

# --- Node Definitions for the Graph ---

async def update_history_and_summarize_node(state: OrchestratorState) -> dict:
    """
    Node 5: Updates the chat history and generates a new conversation summary.
    This runs just before the graph ends, preparing the state for the next turn.
    """
    print("--- NODE: Update History & Summarize ---")

    # 1. Get current state values, providing defaults
    user_query = state.get("query", "")
    final_response = state.get("final_response", "")
    # Your history is a list of dicts, so we handle it as such
    chat_history = state.get("chat_history", [])
    current_summary = state.get("conversation_summary", "Đây là lượt đầu tiên của cuộc trò chuyện.")

    # Ensure final_response is a string for the history
    if isinstance(final_response, dict):
        response_text = final_response.get("answer", str(final_response))
    else:
        response_text = str(final_response)

    # 2. Append the latest exchange to the chat history as dictionaries
    # This matches your `OrchestratorState` type hint: `list[dict]`
    chat_history.append({"role": "user", "content": user_query})
    chat_history.append({"role": "assistant", "content": response_text})

    # 3. Create a prompt to update the summary
    summary_prompt = ChatPromptTemplate.from_template(
        """
        Bạn là một trợ lý tóm tắt cuộc trò chuyện.
        Dựa trên bản tóm tắt trước đó và cuộc trao đổi mới nhất giữa người dùng và AI, hãy tạo ra một bản tóm tắt mới, súc tích và cập nhật.
        Hãy giữ lại những thông tin quan trọng từ bản tóm tắt cũ và tích hợp thêm thông tin mới.

        Bản tóm tắt trước đó:
        "{current_summary}"

        Cuộc trao đổi mới nhất:
        - Người dùng: "{user_query}"
        - AI: "{new_response}"

        Bản tóm tắt mới cập nhật:
        """
    )

    summarizer_chain = summary_prompt | llm | StrOutputParser()

    # 4. Invoke the chain to get the new summary
    new_summary = await summarizer_chain.ainvoke({
        "current_summary": current_summary,
        "user_query": user_query,
        "new_response": response_text
    })

    print(f"--- NEW SUMMARY: {new_summary} ---")

    # 5. Return the updated history and summary to be saved in the state
    return {
        "chat_history": chat_history,
        "conversation_summary": new_summary
    }


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
    # decision = await get_structured_llm_output(prompt, AuthorizationDecision, cloud=True)


    ## Bỏ qua decision
    decision = SimpleNamespace()
    decision.authorized = "Yes"
    decision.reason = "duythai"


    if not decision:
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
    # --- NEW: Get the summary from the state ---
    conversation_summary = state.get("conversation_summary", "Đây là lượt đầu tiên của cuộc trò chuyện.")

    parser = PydanticOutputParser(pydantic_object=ToolRouterDecision)

    prompt_template = ChatPromptTemplate.from_template(
        """
        You are an expert tool router. The user query has already been approved for access.
        Your job is to decide which tool to use from the following options.

        --- CONVERSATION CONTEXT (SUMMARY) ---
        {conversation_summary}
        --- END OF CONTEXT ---

        Based on the context above and the new user query below, choose the most appropriate tool.

        Tool Options:
        1. `retrieval_from_database`: Dùng để truy vấn các thông tin cụ thể, có tính thực tế và đã tồn tại trong cơ sở dữ liệu có cấu trúc. Công cụ này trả lời các câu hỏi về tài chính, báo cáo, và các thông tin như: doanh thu, số lượng, chi tiết khách hàng, thông tin sản phẩm, ngành hàng. Các câu hỏi thường bắt đầu bằng "Bao nhiêu...?", "Là gì...?", "Ai...?", "Liệt kê...", "Tìm...".
        Từ khóa: Cái gì, Bao nhiêu, Bao nhiêu, Tìm, Hiển thị, Liệt kê, Nhận, Chi tiết, Giá, Đếm, Tổng, Tổng cộng.
        Dấu hiệu nhận biết: số lượng, tổng, đếm, giá, chi tiết, thông tin, khách hàng, sản phẩm, ngành hàng, kênh bán hàng (hỏi về một con số hoặc danh sách cụ thể tại một thời điểm).

        2. `rag`: Dùng cho các câu hỏi về tài liệu, thông tin chung, chính sách (CTKM/CSBH), thông tin sản phẩm, v.v.
        Từ khóa: Chính sách, Tóm tắt, Giải thích, Chi tiết về, Cách thực hiện, Hướng dẫn, Mô tả, Thông tin về.
        Dấu hiệu nhận biết: chính sách, quy định, hướng dẫn, tóm tắt, giải thích, mô tả, thông tin về (nội dung văn bản).

        3. `analysis`: dùng để phân tích những báo cáo tài chính của doanh nghiệp, những mảng kinh doanh, dự đoán, phân tích doanh số, 
        chỉ báo cho người dùng (theo tháng, quý, năm), các xu hướng và nhận định cho sản phẩm, thị trường hoặc báo cáo nào đó.

        **New User Query: "{query}"**

        {format_instructions}
        """
    )

    router_chain = prompt_template | llm | parser

    decision = await router_chain.ainvoke({
        "query": query,
        "conversation_summary": conversation_summary,
        "format_instructions": parser.get_format_instructions()
    })
    # print(decision)

    if not decision:
        return {"tool_to_use": "none", "tool_input": {}}

    tool_name = decision.tool_name
    print(f"--- ROUTER DECISION: Tool='{tool_name}' ---")

    tool_input = {}
    query = f"***summarize conversation***: {conversation_summary}, **user_query**: {query}"
    ### MODIFIED: Added logic to handle the new tool and prepare its input ###
    if tool_name in ["rag", "retrieval_from_database"]:
        # Both RAG and DB retrieval can use a similar input structure
        tool_input = QueryRequest(
            query=query,
            top_k=state.get("top_k", 10),
            include_sources=state.get("include_sources", True),
            chat_history=[],
            prompt_from_user=state.get("prompt_from_user", ""),
            cloud_call=state.get("cloud_call", True),
            voice=state.get("voice", False)
        ).dict()
        print("The tool input is ", tool_input)
    elif tool_name == "analysis":
        # Prepare the input for the Analysis API
        tool_input = {"aggregation_level": decision.aggregation_level}

    return {"tool_to_use": tool_name, "tool_input": tool_input}


async def api_caller_node(state: OrchestratorState) -> dict:
    """
    Node 3: The worker. Executes the API call to the selected backend service.
    """
    print("--- NODE: API Caller ---")
    tool_to_use = state['tool_to_use']
    tool_input = state['tool_input']

    response = {}
    ### MODIFIED: Added the `elif` block for the new tool ###
    if tool_to_use == "rag":
        response = await call_rag_api(tool_input, api_key=state["api_key"])
    elif tool_to_use == "retrieval_from_database":
        response = await call_database_retrieval_api(tool_input, api_key=state["api_key"])
    elif tool_to_use == "analysis":
        response = await call_analysis_api(aggregation_level=tool_input.get("aggregation_level", "quarterly"),
                                           query=state['query'])


    # if tool_to_use != "analysis":
    #     user_query = state["query"]
    #     summary_prompt = f"""
    #         Bạn là một trợ lý được tạo bởi công ty GESO, câu trả lời của bạn phải chuyên nghiệp, tích cực và
    #         lễ phép với người dùng.
    #         **Câu hỏi của người dùng:** "{user_query}"
    #         **Câu trả lời của bạn:** "{response}"
    #         """
    #     from llm.llm_call import get_raw_llm_output
    #     summary_result = await get_raw_llm_output(summary_prompt, cloud=True, max_tokens=512)
    #     if summary_result:
    #         response = summary_result
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
    """
    print("--- NODE: Summarize and Filter Analysis ---")
    full_response = state['final_response']
    user_query = state['query']
    technical_summary = full_response.get("text_summary_for_llm")
    human_friendly_summary = technical_summary

    if technical_summary:
        summary_prompt = ChatPromptTemplate.from_template(
            """
            Bạn là một nhà phân tích kinh doanh hữu ích. Hãy tóm tắt báo cáo kỹ thuật sau thành một đoạn văn rõ ràng, dễ hiểu cho người dùng doanh nghiệp.
            Tập trung vào những thông tin chi tiết chính, và chỉ cung cấp thông tin theo câu hỏi của người dùng.
            Không sử dụng markdown. Hãy cung cấp một bản tóm tắt đơn giản, bằng ngôn ngữ tự nhiên.
    
            **Câu hỏi của người dùng:** "{user_query}"
    
            Technical Report:
            {technical_report}
            """
        )
        summarizer_chain = (
                summary_prompt
                | llm.bind(max_output_tokens=512)  # Pass parameters here!
                | StrOutputParser()
        )

        # 3. Invoke the chain with the necessary inputs
        summary_result = await summarizer_chain.ainvoke({
            "user_query": user_query,
            "technical_report": technical_summary
        })

        if summary_result:
            human_friendly_summary = summary_result

    original_plots = full_response.get("plots_for_client", {})
    filtered_plots = original_plots

    if original_plots:
        available_segments = list(original_plots.keys())

        # 1. Instantiate the parser for the RelevantPlotsDecision model.
        plot_parser = PydanticOutputParser(pydantic_object=RelevantPlotsDecision)

        # 2. Modify the prompt template to include the format instructions placeholder.
        filter_prompt_template = ChatPromptTemplate.from_template(
            """
            You are an intelligent data filter. Your job is to identify which of the available data segments are relevant to the user's query.
            User's Original Query: "{user_query}"
            Available Segments: {available_segments}
            Based on the user's query, which of the "Available Segments" should be shown?
            - If the user asks a general question like "analyze the trends", then all segments are relevant.
            - If the user specifically mentions one or more segments (e.g., "how is BÁNH TƯƠI and Kẹo doing?"), then only those are relevant.

            {format_instructions}
            """
        )

        # 3. Create the new chain using the parser.
        plot_filter_chain = filter_prompt_template | llm | plot_parser

        # 4. Invoke the chain, passing the format instructions from the parser.
        decision = await plot_filter_chain.ainvoke({
            "user_query": user_query,
            "available_segments": available_segments,
            "format_instructions": plot_parser.get_format_instructions()
        })

        # The rest of your logic remains unchanged as it will work correctly
        # once the 'decision' object is successfully parsed.
        if decision and decision.relevant_segments:
            print(f"--- FILTER DECISION: Keeping segments {decision.relevant_segments} ---")
            filtered_plots = {
                segment: original_plots[segment]
                for segment in decision.relevant_segments
                if segment in original_plots
            }
        else:
            print("--- FILTER DECISION: LLM failed to identify segments, keeping all plots as a fallback. ---")

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
        # This will correctly handle "rag" and the new "retrieval_from_database"
        print(f"--- DECISION: Tool was '{state.get('tool_to_use')}', ending graph ---")
        return "end"


# --- Graph Assembly ---
def build_graph():
    """
    This function assembles all the nodes and edges into a runnable LangGraph application.
    """
    workflow = StateGraph(OrchestratorState)

    # 1. Add all the nodes to the graph
    workflow.add_node("authorization_checker", authorization_node)
    workflow.add_node("tool_router", tool_router_node)
    workflow.add_node("api_caller", api_caller_node)
    workflow.add_node("summarizer", summarize_and_filter_analysis_node)
    # --- NEW: Add the history/summary node ---
    workflow.add_node("history_summarizer", update_history_and_summarize_node)

    # 2. Set the entry point
    workflow.set_entry_point("authorization_checker")

    # 3. Define the first branch (authorization)
    workflow.add_conditional_edges(
        "authorization_checker",
        check_authorization,
        {
            "authorized": "tool_router",
            "unauthorized": END, # Unauthorized queries don't need a history update
        }
    )

    # 4. Define the path from router to API caller
    workflow.add_edge("tool_router", "api_caller")

    # 5. Define the second branch (after the API call)
    workflow.add_conditional_edges(
        "api_caller",
        should_summarize_analysis,
        {
            "summarize": "summarizer",
            # --- MODIFIED: Route to history_summarizer instead of END ---
            "end": "history_summarizer",
        }
    )

    # 6. After the 'analysis' summarizer runs, go to the history node
    # --- MODIFIED: Route to history_summarizer instead of END ---
    workflow.add_edge("summarizer", "history_summarizer")

    # 7. The history/summary node is the new final step before the graph finishes for the turn
    # --- NEW ---
    workflow.add_edge("history_summarizer", END)

    # Compile and return the graph
    graph = workflow.compile()
    return graph