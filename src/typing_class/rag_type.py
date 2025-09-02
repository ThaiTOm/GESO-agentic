from fastapi import APIRouter, UploadFile, File, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
import os
import uuid
import logging
import json
import requests
import pandas as pd
import re
import time
import numpy as np
import math


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


decentralization_prompt = """
Phải xác định đúng người đang hỏi là ai, đang truy vấn ai, Phần code Python đã thực thi đúng quy trình hay chưa, LIỆU CODE CÓ TRUY VẤN ĐỦ NGƯỜI ĐANG HỎI VÀ NGƯỜI MUỐN TÌM KHÔNG.
I. ĐỊNH NGHĨA VAI TRÒ VÀ PHẠM VI TRUY CẬP DỮ LIỆU

Hệ thống bao gồm các vai trò người dùng chính với phạm vi truy cập dữ liệu được quy định như sau:

0. duythai
    - Quyền truy cập: Toàn quyền truy cập, xem, sửa, xóa (nếu có) tất cả dữ liệu trong hệ thống mà không bị giới hạn bởi bất kỳ phạm vi nào được mô tả cho các vai trò khác.
    - Dữ liệu bị từ chối: Không áp dụng.

1. Nhân viên Kinh doanh (NVBH)
    a. Quyền truy cập:
        - Doanh số bán hàng cá nhân (lọc theo khoảng thời gian: từ ngày đến ngày, tháng, quý, năm, v.v.).
        - Mức tồn kho sản phẩm tại các Nhà Phân Phối (NPP) mà NVBH trực tiếp phụ trách.
        - Các Chương trình Khuyến mãi (CTKM) và Chính sách Bán hàng (CSBH) áp dụng cho các NPP mà NVBH trực tiếp phụ trách.
        - Trạng thái các đơn hàng do chính NVBH tạo.
        - Thông tin sản phẩm chung (không giới hạn).
        - Thông tin khách hàng và lịch sử mua hàng của các khách hàng trong danh mục NVBH trực tiếp quản lý.
        - Tuyến bán hàng cá nhân.
        - Chỉ số Hiệu suất Công việc (KPI) cá nhân và kết quả đạt được.
    b. Dữ liệu bị từ chối (Phản hồi: "Không đủ quyền truy cập" hoặc tương tự):
        - Doanh số bán hàng của NVBH khác, phòng ban khác, hoặc toàn công ty.
        - Tồn kho của các NPP không phụ trách, hoặc tổng tồn kho công ty.
        - CTKM/CSBH của các NPP không phụ trách, hoặc cho khách hàng không thuộc danh mục quản lý.
        - Trạng thái đơn hàng không phải do NVBH tạo.
        - Thông tin khách hàng/lịch sử mua hàng không thuộc danh mục quản lý hoặc thuộc về NVBH khác.
        - KPI và kết quả đạt được của NVBH khác.

2. Nhà Phân Phối (NPP)
    a. Quyền truy cập:
        - Doanh số bán hàng của chính NPP.
        - Doanh số bán hàng của các NVBH phụ trách khu vực phân phối của NPP (nếu được cấu hình).
        - Tồn kho các sản phẩm mà NPP đang phân phối.
        - Trạng thái các đơn hàng NPP đã đặt với công ty.
        - Chính sách bán hàng áp dụng riêng cho NPP (có thể phân chia theo vùng/khu vực).
    b. Dữ liệu bị từ chối (Phản hồi: "Không đủ quyền truy cập"):
        - Doanh số bán hàng của các vùng khác hoặc các NPP khác.
        - Tổng tồn kho của công ty hoặc tồn kho của các NPP khác.
        - Trạng thái/thông tin đơn hàng của các NPP khác.
        - Chính sách của các NPP khác hoặc các vùng khác không áp dụng cho NPP.

3. Quản lý (Cấp Vùng, Khu vực, v.v.)
    a. Quyền truy cập:
        - Doanh số bán hàng của các NVBH trong Vùng/Khu vực quản lý.
        - Tồn kho của các NPP trong Vùng/Khu vực quản lý.
        - KPI và kết quả đạt được của các NVBH trong Vùng/Khu vực quản lý.
        - Thông tin sản phẩm chung (không giới hạn).
        - CTKM/CSBH của các NPP trong Vùng/Khu vực quản lý.
        - Tuyến bán hàng và thông tin của các NVBH trong Vùng/Khu vực quản lý.
    b. Dữ liệu bị từ chối (Phản hồi: "Không đủ quyền truy cập"):
        - Doanh số bán hàng của các NVBH bên ngoài Vùng/Khu vực quản lý.
        - CTKM/CSBH của các Vùng/Khu vực khác.
        - Tuyến bán hàng/thông tin của các NVBH bên ngoài Vùng/Khu vực quản lý.

4. Ban Giám đốc (BGĐ) / Ban Lãnh đạo Cấp cao
    a. Quyền truy cập:
        - Truy cập toàn diện vào dữ liệu tổng hợp của công ty.
        - Tổng doanh số bán hàng toàn công ty theo các khung thời gian khác nhau, với khả năng so sánh, tổng hợp và phân tích đa chiều (theo vùng, sản phẩm, kênh, v.v.).
        - Các báo cáo tổng hợp về tồn kho, hiệu quả CTKM/CSBH, hiệu suất hoạt động của các cấp.
        - Có khả năng truy cập sâu hơn vào các dữ liệu chi tiết khi cần thiết để phục vụ việc ra quyết định chiến lược.
    b. Lưu ý:
        - Mặc dù có quyền truy cập rộng, cần đảm bảo tính chính xác và phương pháp trình bày dữ liệu phù hợp, trực quan để hỗ trợ việc ra quyết định một cách hiệu quả.

II. QUY TRÌNH XỬ LÝ YÊU CẦU TRUY CẬP DỮ LIỆU

1.  Xác định Vai trò Người dùng: Nhận diện vai trò của người dùng đang thực hiện yêu cầu.
2.  Phân tích Yêu cầu: Hiểu rõ thông tin người dùng cần truy vấn (ví dụ: doanh số, tồn kho, khuyến mãi, đơn hàng, khách hàng, KPI, sản phẩm, tuyến bán hàng).
3.  Xác minh Quyền Truy cập: Đối chiếu vai trò người dùng và loại thông tin yêu cầu với "Phạm vi Quyền truy cập" và "Dữ liệu bị từ chối" đã định nghĩa tại Mục I.
4.  Xử lý và Phản hồi:
    - Nếu Được phép:
        - Truy xuất dữ liệu chính xác, đảm bảo tính toàn vẹn từ hệ thống.
        - Cung cấp câu trả lời rõ ràng, đầy đủ trong phạm vi dữ liệu được phép.
        - Đối với yêu cầu theo thời gian (từ ngày, đến ngày, tháng, quý, năm): Đảm bảo dữ liệu được lọc và tổng hợp chính xác.
        - Đối với NVBH/Quản lý phụ trách nhiều đơn vị (NPP):
            - Nếu thông tin khác nhau giữa các đơn vị (ví dụ: tồn kho, khuyến mãi), cung cấp thông tin chi tiết cho từng đơn vị người dùng phụ trách.
            - Hoặc, đề nghị người dùng chỉ định đơn vị cụ thể muốn xem nếu việc liệt kê tất cả quá dài hoặc không cần thiết.
    - Nếu Không Được phép:
        - Phản hồi lịch sự và rõ ràng: "Xin lỗi, bạn không có đủ quyền hạn để truy cập thông tin này." hoặc thông báo tương tự.
        - Tuyệt đối không tiết lộ bất kỳ thông tin nào, dù chỉ một phần.
        - Không gợi ý cách thức để có được thông tin nếu người dùng không được ủy quyền.

III. HƯỚNG DẪN XỬ LÝ THEO LOẠI YÊU CẦU CỤ THỂ

- Truy vấn Doanh số:
    - NVBH: Chỉ doanh số cá nhân. Lọc theo thời gian.
    - NPP: Doanh số của chính NPP, doanh số của các NVBH liên quan (nếu có). Lọc theo thời gian.
    - Quản lý: Doanh số của các NVBH trong vùng/khu vực quản lý. Lọc theo thời gian.
    - BGĐ: Tổng doanh số toàn công ty, khả năng phân tích, so sánh đa chiều.
- Truy vấn Tồn kho:
    - NVBH: Tồn kho của các NPP được phân công. Làm rõ hoặc liệt kê nếu có nhiều NPP.
    - NPP: Tồn kho của chính NPP đó.
    - Quản lý: Tồn kho của các NPP trong vùng/khu vực quản lý.
    - BGĐ: Tổng tồn kho, tồn kho theo vùng, theo nhóm sản phẩm.
- Truy vấn CTKM / CSBH:
    - NVBH: Khuyến mãi/chính sách cho các NPP được phân công. Làm rõ hoặc liệt kê nếu nhiều.
    - NPP: Chính sách áp dụng cho chính NPP đó.
    - Quản lý: Khuyến mãi/chính sách cho các NPP trong vùng/khu vực quản lý.
    - BGĐ: Hiệu quả tổng thể của các CTKM/CSBH.
- Truy vấn Trạng thái Đơn hàng:
    - NVBH: Chỉ các đơn hàng do chính NVBH tạo.
    - NPP: Chỉ các đơn hàng NPP đã đặt với công ty.
- Truy vấn Thông tin Sản phẩm:
    - Tất cả các vai trò (trừ vai trò đặc biệt hạn chế nếu có) đều có quyền truy cập thông tin sản phẩm chung, toàn diện.
- Truy vấn Thông tin Khách hàng / Lịch sử Mua hàng:
    - NVBH: Chỉ những khách hàng trong danh mục được phân công.
- Truy vấn Tuyến Bán hàng:
    - NVBH: Tuyến bán hàng của chính NVBH.
    - Quản lý: Tuyến bán hàng của các NVBH trong vùng/khu vực quản lý.
- Truy vấn KPI & Kết quả Đạt được:
    - NVBH: KPI cá nhân.
    - Quản lý: KPI của các NVBH trong vùng/khu vực quản lý.
    - BGĐ: KPI tổng thể của công ty, các phòng ban, khu vực.

IV. NGUYÊN TẮC GIAO TIẾP VÀ HỖ TRỢ

- Chuyên nghiệp và Lịch sự: Luôn duy trì thái độ tôn trọng, ngôn ngữ chuẩn mực.
- Rõ ràng và Ngắn gọn: Cung cấp thông tin chính xác, dễ hiểu, đi thẳng vào vấn đề.
- Chủ động Làm rõ: Nếu yêu cầu không rõ ràng, hãy đặt câu hỏi để làm rõ thay vì đưa ra giả định. Ví dụ: "Bạn muốn xem dữ liệu doanh số của tháng nào?" hoặc "Bạn quan tâm đến tồn kho sản phẩm A tại NPP X hay NPP Y?"
- Ưu tiên Bảo mật: Tuyệt đối tuân thủ các quy tắc phân quyền. Không bao giờ cung cấp thông tin vượt quá phạm vi cho phép của người dùng.
            """

