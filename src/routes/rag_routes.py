from datetime import timezone
import pandas as pd
from fastapi import Depends, Query, APIRouter, UploadFile, File, Header
from pydantic import ValidationError

from database.redis_connection import flush_redis_database
from processing.analysis_processor import _read_excel_file_data
from processing.query_retrieval_processor import get_classifier_pipeline
from utils import helper_rag
from typing_class.rag_type import *
from database.typesense_declare import get_typesense_instance_service
from rag_components.chatbot_manager import *
from config import settings
import aiofiles
import os

from utils.helper import parse_master_sheet, standardize_text

shared_pipeline = get_classifier_pipeline()

from typing_class.rag_type import PermissionConfig

# Initialize logger
logger = logging.getLogger(__name__)
router = APIRouter()

# flush_redis_database()

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
        os.makedirs(os.path.join(settings.UPLOAD_DIR, meta.get("name")), exist_ok=True)
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
        documents.extend([
            Document(
                document_id=temp,
                file_name=temp,
                file_type="excel",  # FIX: Use stored file type
                chunk_text="none",
                chunk_num=1
            )
            for temp in os.listdir(os.path.join(settings.UPLOAD_DIR, chatbot_name))
        ])
        return {"status": "success", "chatbot_id": chatbot_name, "documents": documents}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error retrieving documents for chatbot {chatbot_name}: {e}")


@router.post("/typesense/document/upload/{chatbot_name}", response_model=ProcessingResponse)
async def process_pdf_endpoint(chatbot_name: str,
                               file: UploadFile = File(...),
                               typesense_client: Any = Depends(get_typesense_client),
                               permissions_str: Optional[str] = Form(None, alias="permissions"),
                               ):
    """Upload và xử lý file PDF, index vào collection của chatbot."""
    flush_redis_database()
    if permissions_str:
        try:
            # Manually parse the JSON string
            permissions_data = json.loads(permissions_str)
            # Validate the data using the Pydantic model
            permissions = PermissionConfig(**permissions_data)

            # If we get here, everything is valid
            print(f"Received and validated permission configuration for bot: {permissions.botName}")
            print(permissions)
            # db.save_permission_config(chatbot_name, permissions.dict())

        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format in the 'permissions' field.")
        except ValidationError as e:
            # Pydantic raises a ValidationError, which we catch
            raise HTTPException(status_code=422, detail=f"Invalid permission data: {e.errors()}")

    try:
        if file.filename.split(".")[-1] == "pdf":
            result = await helper_rag.process_and_index_pdf(chatbot_name, file, typesense_client)
            return {
                "status": "success",
                "message": "PDF processed and indexed successfully",
                "document_id": result["document_id"],
                "file_name": result["file_name"],
                "num_chunks": result["num_chunks"],
                "file_type": "pdf"
            }

        chatbot_directory = os.path.join(settings.UPLOAD_DIR, chatbot_name)
        os.makedirs(chatbot_directory, exist_ok=True)
        destination_path = os.path.join(chatbot_directory, file.filename)

        try:
            async with aiofiles.open(destination_path, 'wb') as out_file:
                while content := await file.read(1024):
                    await out_file.write(content)
        except Exception as e:
            return {"error": f"Could not save file: {e}"}

        if destination_path.lower().endswith(('.xlsx', '.xls')):
            try:
                # --- 1. ĐỌC TẤT CẢ SHEET TỪ FILE GỐC ---
                # all_sheets_dfs = pd.read_excel(destination_path, sheet_name=None, engine='openpyxl')
                #
                # # Xác định tên các sheet (linh hoạt với chữ hoa/thường)
                # data_sheet_name = next((s for s in all_sheets_dfs if s.lower() == 'data'), None)
                # master_sheet_name = next((s for s in all_sheets_dfs if s.lower() == 'master'), None)
                #
                # if not data_sheet_name:
                #     # Nếu không có sheet 'data', ta giả định sheet đầu tiên là sheet dữ liệu
                #     data_sheet_name = list(all_sheets_dfs.keys())[0]
                #
                # data_df = all_sheets_dfs[data_sheet_name]
                #
                # # --- 2. XỬ LÝ SHEET DATA: THÊM CỘT CHUẨN HÓA ---
                # string_columns = data_df.select_dtypes(include=['object']).columns
                # standardized_cols_map = {}  # Lưu map từ cột gốc -> cột chuẩn hóa
                # print("Step 2: Standardizing text columns...")
                # print(f"String columns found: {list(string_columns)}")
                #
                # for col_name in string_columns:
                #     new_col_name = f"{col_name}_chuanhoa"
                #     data_df[new_col_name] = data_df[col_name].astype(str).apply(standardize_text)
                #     standardized_cols_map[col_name] = new_col_name
                #
                # print(f"Standardized columns added: {list(standardized_cols_map.values())}")
                # # Cập nhật lại DataFrame trong dictionary
                # all_sheets_dfs[data_sheet_name] = data_df
                #
                # # --- 3. XỬ LÝ SHEET MASTER: CẬP NHẬT MIÊU TẢ ---
                # if master_sheet_name and master_sheet_name in all_sheets_dfs:
                #     master_df = all_sheets_dfs[master_sheet_name]
                #     if not master_df.empty:
                #         master_col_name = master_df.columns[0]
                #         original_descriptions = parse_master_sheet(master_df, list(string_columns))
                #         print(f"Original descriptions extracted: {list(original_descriptions.keys())}")
                #
                #         new_master_content = []
                #         for line in master_df[master_col_name].dropna().astype(str):
                #             new_master_content.append(line)
                #             col_original = line.split(":")[0]
                #             if col_original in standardized_cols_map:
                #                 new_col_name = standardized_cols_map[col_original]
                #                 original_desc = original_descriptions.get(col_original, "Không có miêu tả gốc.")
                #
                #                 new_desc_lines = [
                #                     new_col_name + f": Đây là cột dữ liệu được chuẩn hóa từ cột '{col_original}'." +
                #                     "Dữ liệu đã được loại bỏ dấu, chuyển thành chữ thường và xóa khoảng trắng để phục vụ tìm kiếm." +
                #                     original_desc
                #                 ]
                #                 new_master_content.extend(new_desc_lines)
                #
                #         updated_master_df = pd.DataFrame(new_master_content, columns=[master_col_name])
                #         all_sheets_dfs[master_sheet_name] = updated_master_df

                # --- 4. XỬ LÝ SHEET PERMISSION (NẾU CÓ) ---
                permission_df = None
                if permissions_str:
                    if hasattr(permissions, 'model_dump'):
                        permissions_dict = permissions.model_dump()
                    else:
                        permissions_dict = permissions.dict()

                    if permissions_dict:
                        data_for_df = []
                        for key, value in permissions_dict.items():
                            string_value = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
                            data_for_df.append([key, string_value])
                        permission_df = pd.DataFrame(data_for_df, columns=['Permission', 'Value'])

                # --- 5. GHI TẤT CẢ CÁC SHEET ĐÃ CẬP NHẬT TRỞ LẠI FILE ---
                # Sử dụng mode='w' để ghi đè file với nội dung mới từ dictionary all_sheets_dfs
                with pd.ExcelWriter(destination_path, engine='openpyxl', mode='w') as writer:
                    # Ghi lại tất cả các sheet đã được sửa đổi (data, master) và các sheet không đổi
                    # for sheet_name, df_to_write in all_sheets_dfs.items():
                    #     df_to_write.to_excel(writer, sheet_name=sheet_name, index=False)

                    # Ghi thêm sheet 'permission' nếu nó đã được tạo
                    if permission_df is not None:
                        permission_df.to_excel(writer, sheet_name="permission", index=False)

                print("Successfully wrote all updated sheets to the file.")

                # --- 6. CÁC BƯỚC XỬ LÝ TIẾP THEO ---
                _, _, _, description, _ = _read_excel_file_data(str(destination_path))
                shared_pipeline = get_classifier_pipeline()
                shared_pipeline.add_or_update_category(destination_path, description)

            except Exception as e:
                # Thay đổi thông báo lỗi để rõ ràng hơn
                return {"error": f"An error occurred while processing the Excel file: {e}"}

        return {
            "status": "success",
            "message": "File processed, standardized, and indexed successfully",
            "document_id": "",
            "file_name": "",
            "num_chunks": 1,
            "file_type": "excel"
        }
    except helper_rag.DocumentProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during file processing. {e}")

# ===================================================
# [Group 3] Search and Tools endpoints
# ===================================================

@router.post("/typesense/query_ver_thai")
async def query_documents_endpoint(request: QueryRequest, api_key: str = Header(...), typesense_client: Any = Depends(get_typesense_client)):
    """Endpoint thực hiện RAG query, trả về câu trả lời từ LLM."""
    response_data = await helper_rag.process_rag_query(request, api_key, typesense_client)
    print(response_data["answer"])
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


@router.delete("/typesense/document/delete/{chatbotName}/{documentTitle}")
async def delete_excel_document(chatbotName:str, documentTitle:str):
    """Xóa file excel đã upload"""
    flush_redis_database()
    try:
        file_path = os.path.join(settings.UPLOAD_DIR, chatbotName, documentTitle)
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"status": "success", "message": f"File '{documentTitle}' deleted successfully from chatbot '{chatbotName}'."}
        else:
            return {"status": "error", "message": f"File '{documentTitle}' not found in chatbot '{chatbotName}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting the file: {e}")

