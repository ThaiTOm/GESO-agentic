from langchain_core.prompts import ChatPromptTemplate

SUMMARY_PROMPT = ChatPromptTemplate.from_template(
        """
        Bạn là một trợ lý AI chuyên tạo ra các bản tóm tắt có cấu trúc cho các cuộc trò chuyện.
        Nhiệm vụ của bạn là phân tích cuộc trò chuyện đang diễn ra và cập nhật bản tóm tắt một cách súc tích, có tổ chức, ưu tiên các thông tin quan trọng.

        Hãy tuân thủ nghiêm ngặt định dạng đầu ra được yêu cầu dưới đây.

        Bản tóm tắt trước đó:
        ---
        {current_summary}
        ---

        Cuộc trao đổi mới nhất:
        - Người dùng: "{user_query}"
        - AI: "{new_response}"

        ---
        **HƯỚNG DẪN:**
        Dựa trên "Bản tóm tắt trước đó" và "Cuộc trao đổi mới nhất", hãy cập nhật thông tin và tạo ra một bản tóm tắt mới hoàn chỉnh theo cấu trúc sau.

        **BẢN TÓM TẮT MỚI CẬP NHẬT:**

        **1. Tóm tắt chung:**
        (Một đoạn văn ngắn gọn, khoảng 2-3 câu, tóm lược toàn bộ nội dung cuộc trò chuyện từ đầu đến giờ. Cập nhật nội dung này với thông tin mới nhất.)

        **2. Các chủ đề chính đang thảo luận:**
        - (Liệt kê các chủ đề chính đã và đang được thảo luận dưới dạng gạch đầu dòng. Giữ lại các chủ đề cũ và thêm chủ đề mới nếu có.)

        **3. Các thực thể & thông tin quan trọng:**
        - **Con người:** (Liệt kê tên những người được đề cập)
        - **Địa điểm:** (Liệt kê các địa danh được đề cập)
        - **Sự kiện & Mốc thời gian:** (Liệt kê các sự kiện hoặc mốc thời gian quan trọng đã được nhắc đến)
        - **Thông tin khác:** (Liệt kê các thuật ngữ, sản phẩm, hoặc thông tin quan trọng khác)
        """
    )

CHOOSE_TOOL_PROMPT = ChatPromptTemplate.from_template(
        """
        You are an expert tool router. The user query has already been approved for access.
        Your job is to decide which tool to use from the following options.
        
        Based on the new user query below, choose the most appropriate tool.
        
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

TECHNICAL_REPORT_SUMMARY_PROMPT = ChatPromptTemplate.from_template(
    """
    Bạn là một nhà phân tích kinh doanh hữu ích. Hãy tóm tắt báo cáo kỹ thuật sau thành một đoạn văn rõ ràng, dễ hiểu cho người dùng doanh nghiệp.
    Tập trung vào những thông tin chi tiết chính, và chỉ cung cấp thông tin theo câu hỏi của người dùng.
    Không sử dụng markdown. Hãy cung cấp một bản tóm tắt đơn giản, bằng ngôn ngữ tự nhiên.

    **Câu hỏi của người dùng:** "{user_query}"

    Technical Report:
    {technical_report}
    """
)


FILTER_GRAPH_TITLE_PROMPT = ChatPromptTemplate.from_template(
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