from fastapi import Depends, Header, APIRouter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from rag_components.llm_interface import reformulate_query_with_chain
from routes.rag_routes import get_typesense_client
from typing_class.rag_type import *
from rag_components.chatbot_manager import *
from processing.analysis_processor import select_excel_database, select_database
from rag_components.agents.data_analyst_agent import analyze_dataframe
from llm.llm_langchain import gemini_llm_service, local_llm_service
from context_engine.reformulation_prompt import reformulation_query_prompt, not_known_prompt

# Initialize logger
logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query_rag")
async def query_analyze_rag_document(request: QueryRequest, api_key: str = Header(...), typesense_client: Any = Depends(get_typesense_client)):
    collection_name = get_chatbot_name_by_api_key(typesense_client, api_key)
    database, master_sheet, row_rules, selected_db, db_description = await select_database(
        request.query, collection_name)

    if database is None:
        return {
            "answer": not_known_prompt
        }

    result_analyze = analyze_dataframe(df=database,
                                       query=request.query,
                                       master_data=master_sheet,
                                       row_rules=row_rules,
                                       user_id=request.user_id,
                                       user_role=request.user_role,
                                       selected_db=selected_db
                                       )

    answer = result_analyze.get("result", None)
    reason = result_analyze.get("reason", None)

    prompt = ChatPromptTemplate.from_template(reformulation_query_prompt)
    summarizer_chain = (
            prompt
            | local_llm_service.bind(max_output_tokens=512)  # Pass parameters here!
            | StrOutputParser()
    )

    # 3. Invoke the chain with the necessary inputs
    answer_fn = await summarizer_chain.ainvoke({
        "answer": answer,
        "query": request.query,
        "reason": reason,
        "db_description": db_description[100:]
    })

    if answer is None:
        answer_fn = not_known_prompt

    print(answer_fn)

    return {
        "query": request.query,
        "answer": answer_fn,
        "sources": [],
        "metadata": {
            "collection": collection_name,
            "mode": "excel_query",
            "file_name": selected_db,
            "database_description": db_description[:100] + "..." if len(db_description) > 100 else db_description,
            "original_query": request.query,
            "rewritten_query": request.query
        }
    }