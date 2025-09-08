from fastapi import Depends, Header, APIRouter

from routes.rag_routes import get_typesense_client
from typing_class.rag_type import *
from rag_components.chatbot_manager import *
from processing.document_processor import select_excel_database
from rag_components.agents.data_analyst_agent import analyze_dataframe
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

    if answer is None:
        error_message = result_analyze.get("error", "Không thể phân tích dữ liệu")
        answer = f"Không tìm thấy câu trả lời phù hợp cho câu hỏi của bạn."

    return {
        "query": request.query,
        "answer": answer,
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