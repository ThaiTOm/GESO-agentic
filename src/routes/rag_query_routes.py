from fastapi import Depends, Header, APIRouter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from routes.rag_routes import get_typesense_client
from typing_class.rag_type import *
from rag_components.chatbot_manager import *
from processing.analysis_processor import select_excel_database
from rag_components.agents.data_analyst_agent import analyze_dataframe
from llm.llm_langchain import cloud_llm_service

llm = cloud_llm_service

# Initialize logger
logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/query_rag")
async def query_analyze_rag_document(request: QueryRequest, api_key: str = Header(...), typesense_client: Any = Depends(get_typesense_client)):
    collection_name = get_chatbot_name_by_api_key(typesense_client, api_key)

    excel_database, master_sheet, selected_db, db_description = await select_excel_database(
        request.query, collection_name)

    if excel_database is None:
        return {
            "answer": "Không có câu trả lời"
        }

    result_analyze = analyze_dataframe(df=excel_database, query=request.query, master_data=master_sheet)
    answer = result_analyze.get("result")

    # Pretty the answer
    prompt = ChatPromptTemplate.from_template("""
    Hãy dựa vào câu trả lời của bạn và câu hỏi của người dùng để viết lại câu trả lời cho đẹp (nếu có danh từ thì hãy viết hoa cho phù hợp), hãy chỉ đưa ra câu trả lời.        
    **Câu hỏi của người dùng:** "{query}"
    **Câu trả lời của bạn:** "{answer}"
    """)

    summarizer_chain = (
            prompt
            | llm.bind(max_output_tokens=512)  # Pass parameters here!
            | StrOutputParser()
    )

    # 3. Invoke the chain with the necessary inputs
    answer_fn = await summarizer_chain.ainvoke({
        "query": request.query,
        "answer": answer
    })

    if answer_fn is None:
        error_message = result_analyze.get("error", "Không thể phân tích dữ liệu")
        answer_fn = f"Không tìm thấy câu trả lời phù hợp cho câu hỏi của bạn."

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