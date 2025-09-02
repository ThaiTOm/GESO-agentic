from datetime import timezone
from fastapi import Depends, Query, APIRouter, HTTPException, UploadFile, File, Header
from utils import helper_rag
from typing_class.rag_type import *
from database.typesense_declare import get_typesense_instance_service
from rag_components.chatbot_manager import *

# Initialize logger
logger = logging.getLogger(__name__)
router = APIRouter()


# Helper dependency to get Typesense client
def get_typesense_client():
    client = get_typesense_instance_service()
    if not client:
        raise HTTPException(status_code=503, detail="TypesenseClient not initialized")
    return client

# ===================================================
# [Group 1] Chatbot management endpoints
# ===================================================

@router.get("/typesense/chatbot/all")
async def get_all_chatbots(typesense_client: Any = Depends(get_typesense_client)):
    """Lấy danh sách tất cả các chatbot từ collection 'chatbot_info'"""
    try:
        chatbots_data = list_all_chatbots(typesense_client)
        chatbots = [Chatbot(**data) for data in chatbots_data]
        return {"status": "success", "chatbots": chatbots}
    except Exception as e:
        logger.error(f"API Error retrieving chatbots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve chatbots.")


@router.post("/typesense/chatbot/create", response_model=ChatbotResponse)
async def create_chatbot_endpoint(request: ChatbotCreateRequest, typesense_client: Any = Depends(get_typesense_client)):
    """Tạo chatbot mới"""
    try:
        meta = typesense_client.create_chatbot(request.name, request.description or "")
        chatbot_obj = Chatbot(
            chatbot_id=meta.get("id"), name=meta.get("name"), description=meta.get("description", ""),
            chatbot_api_key=meta.get("api_key"), created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        return {"status": "success", "message": "Chatbot created successfully", "chatbot": chatbot_obj}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/typesense/chatbot/delete/{chatbot_name}")
async def delete_chatbot_endpoint(chatbot_name: str, typesense_client: Any = Depends(get_typesense_client)):
    """Xóa chatbot"""
    try:
        result = typesense_client.delete_chatbot(chatbot_name)
        return {"status": "success", "message": f"Chatbot '{chatbot_name}' deleted successfully", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===================================================
# [Group 2] Document management endpoints
# ===================================================

@router.get("/typesense/document/{chatbot_name}", response_model=DocumentListResponse)
async def get_chatbot_documents(
    chatbot_name: str,
    limit: int = Query(100, ge=1, le=250), # FIX: Add pagination
    offset: int = Query(0, ge=0),
    typesense_client: Any = Depends(get_typesense_client)
):
    """Lấy danh sách document trong collection của chatbot."""
    try:
        result = typesense_client.client.collections[chatbot_name].documents.search({
            "q": "*", "query_by": "text", "limit": limit, "offset": offset
        })

        documents = [
            Document(
                document_id=doc.get("id"),
                file_name=doc.get("title"),
                file_type=doc.get("file_type", "unknown"), # FIX: Use stored file type
                chunk_text=doc.get("text"),
                chunk_num=doc.get("chunk_num", 0)
            )
            for hit in result.get("hits", []) if (doc := hit.get("document"))
        ]
        return {"status": "success", "chatbot_id": chatbot_name, "documents": documents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents for chatbot {chatbot_name}: {e}")


@router.post("/typesense/document/upload/{chatbot_name}", response_model=ProcessingResponse)
async def process_pdf_endpoint(chatbot_name: str, file: UploadFile = File(...), typesense_client: Any = Depends(get_typesense_client)):
    """Upload và xử lý file PDF, index vào collection của chatbot."""
    try:
        result = await helper_rag.process_and_index_pdf(chatbot_name, file, typesense_client)
        return {
            "status": "success",
            "message": "PDF processed and indexed successfully",
            "document_id": result["document_id"],
            "file_name": result["file_name"],
            "num_chunks": result["num_chunks"],
            "file_type": "pdf"
        }
    except helper_rag.DocumentProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="An unexpected error occurred during file processing.")

# ===================================================
# [Group 3] Search and Tools endpoints
# ===================================================

@router.post("/typesense/query_ver_thai")
async def query_documents_endpoint(request: QueryRequest, api_key: str = Header(...), typesense_client: Any = Depends(get_typesense_client)):
    """Endpoint thực hiện RAG query, trả về câu trả lời từ LLM."""
    response_data = await helper_rag.process_rag_query(request, api_key, typesense_client)
    return response_data


@router.post("/typesense/suggest_questions", response_model=SuggestQuestionsResponse)
async def suggest_follow_up_questions_endpoint(request: SuggestQuestionsRequest):
    """Tạo 3 câu hỏi gợi ý dựa trên câu trả lời và ngữ cảnh trước đó."""
    return await helper_rag.generate_suggested_questions(request)


@router.post("/typesense/get_chatbot_info", response_model=ChatbotInfoResponse)
async def get_chatbot_info(request: ChatbotInfoRequest, typesense_client: Any = Depends(get_typesense_client)):
    """Lấy tên chatbot từ API key."""
    try:
        chatbot_name = helper_rag.get_chatbot_name_by_api_key(typesense_client, request.api_key)
        return {"chatbot_name": chatbot_name}
    except helper_rag.InvalidAPIKeyError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="An internal error occurred.")