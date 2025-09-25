from .base_prompt import BasePrompt

class ReformulationPrompt(BasePrompt):
    """
    Prompt for reformulating user queries to include more context.

    This prompt analyzes the conversation context and rewrites short or ambiguous
    user queries to be more complete and specific.
    """

    def __init__(self):
        template = """
            Dưới đây là cuộc hội thoại gần nhất:
            {context_str}
            Câu hỏi mới của người dùng: "{query}"
            Câu hỏi này có vẻ ngắn gọn và thiếu ngữ cảnh.
            Hãy phân tích ngữ cảnh từ cuộc hội thoại trước và viết lại câu hỏi mới một cách đầy đủ.
            Bạn phải:
            1\. Bổ sung chủ đề/chủ thể chính đang được thảo luận.
            2\. Làm rõ ý nghĩa ngầm ẩn trong các câu hỏi ngắn như "Tính như thế nào?", "Có những khu vực nào?", "Có tỉnh nào khác không?".
            3\. Thay thế đại từ và từ chỉ định (như "đó", "này", "nó") bằng các thực thể cụ thể.
            4\. Kết hợp thông tin từ các câu hỏi và câu trả lời trước để tạo ngữ cảnh đầy đủ.
            5\. Giữ nguyên phần "Tôi là..." trong câu hỏi mới của người dùng.
            Bạn là một chuyên gia chăm sóc khách hàng, nắm rõ các nghiệm vụ về thị trường chứng khoán
            Trả về câu hỏi đã được viết lại một cách đầy đủ, không thêm bất kỳ lời giải thích nào.

        """
        super().__init__(template, name="ReformulationPrompt")

    def format_prompt(self, context_str, query):
        """
        Format the reformulation prompt with the given context and query.

        Args:
            context_str (str): The conversation context.
            query (str): The user's query.

        Returns:
            str: The formatted prompt ready to be sent to the LLM.
        """
        return self.format(context_str=context_str, query=query)

reformulation_query_prompt = """
    Bạn là một trợ lý chuyên về định dạng văn bản. Nhiệm vụ của bạn là trình bày lại câu trả lời dưới đây một cách chuyên nghiệp và dễ đọc, lịch sự, và hãy nói sơ qua về lý do bạn làm như vậy (nói đơn giản dễ hiểu, không đề cập đến kỹ thuật như dataframe, cột, dòng, etc).

    **Yêu cầu định dạng:**
    - **In đậm:** Sử dụng in đậm cho các tiêu đề chính hoặc các thuật ngữ quan trọng.
    - **Danh sách:** Sử dụng gạch đầu dòng (-) hoặc danh sách có thứ tự (1., 2.) để liệt kê các ý.
    - **Viết hoa:** Luôn viết hoa tên riêng, tên người, tên sản phẩm, và các danh từ riêng quan trọng.
    - **Cấu trúc:** Phân chia nội dung thành các đoạn văn ngắn, có tiêu đề rõ ràng nếu cần.
    - **Lưu ý:** Tuyệt đối không sử dụng định dạng bảng, chỉ trả lời dựa trên câu trả lời từ người dùng, không được thêm kiến thức khác.

    **Đây là câu trả lời hãy chỉ cho ra kết quả cuối cùng, không kèm thêm gì**
     - **Câu trả lời:** "{answer}"
     - **Câu hỏi của người dùng:** "{query}"
     - **Lý do phân tích:** "{reason}"
     - **Tổng quan dữ liệu và các cột có trong dữ liệu:** "{db_description}"
"""

not_known_prompt = "Rất tiếc, tôi chưa có thông tin về vấn đề này. Vui lòng liên hệ bộ phận hỗ trợ phù hợp để được giải đáp."

# Create an instance for easy import
reformulation_prompt_ins = ReformulationPrompt()
