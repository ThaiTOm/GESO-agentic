from fastapi import Depends, Header, APIRouter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from rag_components.llm_interface import reformulate_query_with_chain
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

    reformulated_query = await reformulate_query_with_chain(
        query=request.query,
        chat_history=request.chat_history
    )

    excel_database, master_sheet, row_rules, selected_db, db_description = await select_excel_database(
        reformulated_query, collection_name)

    if excel_database is None:
        return {
            "answer": "Không có câu trả lời"
        }


    result_analyze = analyze_dataframe(df=excel_database, query=reformulated_query, master_data=master_sheet, row_rules=row_rules, user_id=request.user_id, user_role=request.user_role)
    answer = result_analyze.get("result", None)

    # Pretty the answer
    prompt = ChatPromptTemplate.from_template("""
    Bạn là một trợ lý chuyên về định dạng văn bản. Nhiệm vụ của bạn là trình bày lại câu trả lời dưới đây một cách chuyên nghiệp và dễ đọc, hãy lịch sự.

    **Yêu cầu định dạng:**
    - **In đậm:** Sử dụng in đậm cho các tiêu đề chính hoặc các thuật ngữ quan trọng.
    - **Danh sách:** Sử dụng gạch đầu dòng (-) hoặc danh sách có thứ tự (1., 2.) để liệt kê các ý.
    - **Viết hoa:** Luôn viết hoa tên riêng, tên người, tên sản phẩm, và các danh từ riêng quan trọng.
    - **Cấu trúc:** Phân chia nội dung thành các đoạn văn ngắn, có tiêu đề rõ ràng nếu cần.
    - **Lưu ý:** Tuyệt đối không sử dụng định dạng bảng.

    **Đây là câu trả lời hãy chỉ cho ra kết quả cuối cùng, không kèm thêm gì**
     - **Câu trả lời:** "{answer}"
     - **Câu hỏi của người dùng:** "{query}"
    """)

    summarizer_chain = (
            prompt
            | llm.bind(max_output_tokens=512)  # Pass parameters here!
            | StrOutputParser()
    )

    # 3. Invoke the chain with the necessary inputs
    answer_fn = await summarizer_chain.ainvoke({
        "answer": answer,
        "query": reformulated_query
    })

    if answer is None:
        answer_fn = f"Rất tiếc, tôi chưa có thông tin về vấn đề này. Vui lòng liên hệ bộ phận hỗ trợ phù hợp để được giải đáp."

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
            "rewritten_query": reformulated_query
        }
    }