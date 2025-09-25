import json
import textwrap
import time

from langchain_core.messages import HumanMessage
import hashlib
import pandas as pd
from langchain_core.output_parsers import PydanticOutputParser
from pydantic_ai import Agent
from llm.llm_langchain import local_llm_service, gemini_llm_service

from llm.provider import LLMModels
from utils.helper_rag import format_numbers_in_string
import numpy as np
import re
from utils.helper import standardize_text

from pydantic import BaseModel, Field
from utils.helper_authorization import authorize


class CodeOutput(BaseModel):
    """A Pydantic model to structure the output for the data analyst agent."""
    reasoning: str = Field(description="A brief, one-sentence explanation of the plan in Vietnamese.")
    code: str = Field(description="The Python code to execute to answer the user's query.")


class DataAnalystAgent:
    _transform_cache = {}

    # --- 1. Define our high-quality examples ---
    _examples = [
        {
            "query": "tổng doanh thu là bao nhiêu?",
            "output": CodeOutput(
                reasoning="Để tính tổng doanh thu, tôi sẽ tính tổng của cột 'DoanhThu'.",
                code="result = df['DoanhThu'].sum()"
            )
        },
        {
            "query": "có bao nhiêu đơn hàng cho mỗi thành phố?",
            "output": CodeOutput(
                reasoning="Để đếm đơn hàng cho mỗi thành phố, tôi sẽ nhóm theo cột 'ThanhPho' và đếm số lượng.",
                code="result = df.groupby('ThanhPho').size()"
            )
        },
        {
            "query": "cho biết số cửa hiệu mà Đặng Thị Hồng đang quản lý?",
            "output": CodeOutput(
                reasoning="""Áp dụng Nguyên tắc #1 (Chuẩn hóa) và #2.A (So sánh Chính xác), tôi sẽ chuẩn hóa cột 'DaiDienKinhDoanh' và chuỗi tìm kiếm đầy đủ để so sánh bằng (==).""",
                code=textwrap.dedent("""
                        search_value = standardize_text('Đặng Thị Hồng')
                        mask = df['DaiDienKinhDoanh'].astype(str).apply(standardize_text) == search_value
                        result = df.loc[mask, 'CuaHieuQuanLy'].sum()
                        """)
            )
        },
        {
            "query": "tìm các sản phẩm có chữ 'baby gold'",
            "output": CodeOutput(
                reasoning="""Áp dụng Nguyên tắc #1 (Chuẩn hóa) và #2.B (So sánh Tương đối), tôi sẽ chuẩn hóa cột 'TenSanPham' và dùng .str.contains() để tìm kiếm một phần chuỗi.""",
                code=textwrap.dedent("""
                        search_term = standardize_text('baby gold')
                        mask = df['TenSanPham'].astype(str).apply(standardize_text).str.contains(search_term, na=False)
                        result = df[mask]
                        """
                ))
        },
        {
            "query": "Liệt kê các đơn hàng của kho 'hcm_bd'",
            "output": CodeOutput(
                reasoning="""Để liệt kê đơn hàng của kho 'hcm_bd', tôi cần chuẩn hóa cả hai vế để so sánh chính xác, loại bỏ ảnh hưởng của chữ hoa/thường và khoảng trắng.""",
                code=textwrap.dedent("""
                # Trong trường hợp này, mã kho không có dấu, chỉ cần lower() và strip() là đủ
                search_value = standardize_text('hcm_bd')
                mask = df['MaKho'].astype(str).apply(standardize_text) == search_value
                result = df[mask]
                """
            ))
        },
        {
            "query": "doanh thu của khách hàng tên 'thuoc quynh anh'",
            "output": CodeOutput(
                reasoning="""Vì người dùng cung cấp một phần tên ('thuoc quynh anh') chứ không phải tên đầy đủ, tôi sẽ áp dụng Nguyên tắc #2.B (So sánh Tương đối) và dùng .str.contains() để tìm tất cả khách hàng có tên chứa chuỗi này.""",
                code=textwrap.dedent("""
                        # Chuẩn hóa cụm từ tìm kiếm
                        search_term = standardize_text('thuoc quynh anh')

                        # Chuẩn hóa cột TENKH và dùng .str.contains() để tìm kiếm tương đối
                        mask = df['TENKH'].astype(str).apply(standardize_text).str.contains(search_term, na=False)

                        # Lọc DataFrame và tính tổng doanh thu
                        filtered_df = df[mask]
                        result = filtered_df['DoanhThu'].sum()
                """)
            )
        },
        {
            "query": "Tổng doanh thu của khách hàng HỘ KINH DOANH NHÀ THUỐC QUỲNH ANH",
            "output": CodeOutput(
                reasoning="""Vì người dùng cung cấp tên khách hàng đầy đủ và cụ thể, tôi sẽ áp dụng Nguyên tắc #2.A (So sánh Chính xác) và dùng toán tử '==' để có kết quả chính xác nhất.""",
                code=textwrap.dedent("""
                        search_customer = standardize_text('HỘ KINH DOANH NHÀ THUỐC QUỲNH ANH')
                        mask_customer = df['TENKH'].astype(str).apply(standardize_text) == search_customer
                        filtered_df = df[mask_customer]
                        result = filtered_df['DoanhThu'].sum()
                """)
            )
        }
    ]

    # --- 2. Update the prompt template to include a placeholder for examples ---
    default_instruction = (
        "You are a top-tier Python data analyst AI. Your primary goal is to write robust Python code to answer a user's question about a pandas DataFrame (`df`).\n"
        "You must follow these guiding principles at all times.\n\n"

        "--- GUIDING PRINCIPLES ---\n"
        "1.  **Standardize Text Before Comparison (Mandatory):** User text is inconsistent ('Hà Nội' vs 'ha noi'). To handle this, YOU MUST ALWAYS use the `standardize_text()` helper function on BOTH the user's search term AND the relevant DataFrame column before any comparison. This applies to all text filtering.\n\n"

        "2.  **Select the Appropriate Comparison Method:** After standardizing, choose the correct comparison method based on the user's query.\n"
        "    - **A. Use Exact Match (`==`):** Use this when the user provides a complete, specific identifier. This is best for codes (`MaKho`), categories, statuses, or when a full, precise name is given (e.g., 'HỘ KINH DOANH NHÀ THUỐC QUỲNH ANH').\n"
        "    - **B. Use Partial Match (`.str.contains()`):** Use this when the user's query implies a search for a fragment or keyword. Look for phrases like 'có chứa', 'liên quan đến', or when the user provides an incomplete name (e.g., searching for 'thuoc quynh anh' inside a full name).\n\n"

        "3.  **Use Provided Helper Functions:** The function `standardize_text(text)` is available. Use it for Principle #1. Do not redefine it.\n\n"

        "4.  **Strict JSON Output:** Your final response MUST BE a single, valid JSON object with `reasoning` and `code` keys.\n\n"

        "--- EXAMPLES OF APPLYING THE PRINCIPLES ---\n"
        "{examples}\n\n"

        "--- CURRENT TASK ---\n"
        f"Today's date is {time.strftime('%d/%m/%Y')}.\n"
        "Here is the context for the current DataFrame:\n"
        "{master_data_context}"
        "- Column Data Types (df.dtypes):\n"
        "{df_dtypes}\n\n"
        "User's question: {query}"
    )

    def __init__(self, model):
        self.model = model

    # --- 3. Add a helper method to format the examples into a string ---
    def _format_examples(self) -> str:
        formatted_list = []
        for example in self._examples:
            query = example["query"]
            # Cập nhật reasoning trong ví dụ để nó tham chiếu đến NGUYÊN TẮC
            reasoning = example["output"].reasoning.replace(
                "Để tìm", "Áp dụng Nguyên tắc #1 (Robust Text Comparison), để tìm"
            )
            code = example["output"].code.replace(
                "# Định nghĩa hàm chuẩn hóa để sử dụng",
                "# Using the pre-defined standardize_text() helper function."
            )

            output_dict = {"reasoning": reasoning, "code": code}
            # json_output = json.dumps(output_dict, ensure_ascii=False, indent=2)

            formatted_list.append(
                f"Question: {query}\n"
                f"Answer:\n{output_dict}"
            )
        return "\n\n".join(formatted_list)

    def build_prompt(self, query: str, df: pd.DataFrame, master_data: str):
        column_examples = {}
        for col in df.columns:
            column_examples[col] = df[col].dropna().unique()[:10].tolist()

        # --- 4. Format the examples and insert them into the prompt ---
        formatted_examples = self._format_examples()
        master_data_context = f"\n\n--- MASTER DATA --- \n**Master Data:** {master_data} \n\n"

        prompt_template = self.default_instruction

        prompt = prompt_template.replace(
            "{examples}", formatted_examples
        ).replace(
            "{master_data_context}", master_data_context
        ).replace(
            "####", ""  # Let's remove the old placeholder now that we have a better one
        ).replace(
            "{df_dtypes}", df.dtypes.to_markdown()
        ).replace(
            "{query}", query
        )

        print("=============== The prompt after build ")
        print(prompt)
        return prompt

    @staticmethod
    def _hash_df(df: pd.DataFrame) -> str:
        """Generate a hash for the DataFrame content."""
        # Consider sorting columns to make it order-independent
        df_bytes = pd.util.hash_pandas_object(df, index=True).values.tobytes()
        return hashlib.md5(df_bytes).hexdigest()

    @classmethod
    def transform_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cached transformation. Automatically cleans column names and converts
        date-like columns to datetime objects.
        """
        df_hash = cls._hash_df(df)

        if df_hash in cls._transform_cache:
            print("INFO: Returning cached and transformed DataFrame.")
            return cls._transform_cache[df_hash]

        print("INFO: Performing new transformation on DataFrame...")
        transformed = df.copy()

        # 1. Clean column names by stripping whitespace
        transformed.columns = transformed.columns.str.strip()

        # 2. Automatically detect and convert date-like columns
        for col in transformed.select_dtypes(include=['object']).columns:
            # Don't check every value for performance. Take a sample of the first 100 non-null values.
            sample = transformed[col].dropna().head(100)

            if sample.empty:
                continue

            try:
                # Attempt to convert the sample to datetime.
                # 'dayfirst=True' is crucial for DD/MM/YYYY formats.
                # 'errors='coerce'' will turn unparseable strings into NaT (Not a Time).
                converted_sample = pd.to_datetime(sample, dayfirst=True, errors='coerce')

                # Heuristic: If over 90% of the non-null sample values are valid dates,
                # we assume the entire column is a date column.
                successful_conversions = converted_sample.notna().sum()
                total_sample_size = len(sample)

                success_ratio = successful_conversions / total_sample_size

                if success_ratio > 0.90:
                    print(f"INFO: Auto-detected date column '{col}'. Converting to datetime.")
                    # If the sample looks like a date, convert the entire column.
                    transformed[col] = pd.to_datetime(transformed[col], dayfirst=True, errors='coerce')

            except (ValueError, TypeError):
                # This column is not a date format, continue to the next one.
                continue

        # Cache the transformed DataFrame
        cls._transform_cache[df_hash] = transformed
        print("INFO: Transformation complete and cached.")
        return transformed

def analyze_dataframe(query: str, df: pd.DataFrame, master_data: str, row_rules:dict, user_id:str, user_role:str, selected_db:str) -> dict:
    try:
        df = authorize(row_rules, user_id, user_role, df, selected_db)

        # init class DataAnalystAgent
        # Chèn Master Data vào vị trí '####'
        # print("The master data is ", master_data)
        # Sau đó mới tiến hành transform DataFrame
        df = DataAnalystAgent.transform_df(df)  # Use cached transformation
        print("DataFrame after transformation:\n", df.head())
    except Exception as e:
        print(e)
        return {"result": None, "code": "", "error": f"❌ Tiền xử lý DataFrame thất bại: {e}"}

    # ===== Environment Setup =====
    execution_env = {
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "standardize_text": standardize_text
    }

    # ===== Code Generation =====
    analyst = DataAnalystAgent(model=gemini_llm_service)
    try:
        # 1. Set up the parser using your Pydantic class
        parser = PydanticOutputParser(pydantic_object=CodeOutput)

        # 2. Build the initial prompt
        base_prompt = analyst.build_prompt(query=query, df=df, master_data=master_data)

        # 3. Get the formatting instructions from the parser and add them to the prompt
        #    This is how we tell the model to generate JSON.
        format_instructions = parser.get_format_instructions()
        prompt_with_instructions = f"{base_prompt}\n\n{format_instructions}"

        # 4. Invoke the model with the combined prompt
        messages = [HumanMessage(content=prompt_with_instructions)]
        response_object = analyst.model.invoke(messages, max_tokens=258, temperature=0.0)

        print("Raw response from model:\n", response_object.content)

        # 5. Use the parser to convert the model's string response into a Pydantic object
        #    This step handles JSON validation and parsing automatically.
        parsed_output = parser.parse(response_object.content)

        # 6. Access the attributes directly from the parsed object
        code = parsed_output.code
        reasoning = parsed_output.reasoning


        code = textwrap.dedent(code).strip()

        # Your original search terms
        # search_customer = standardize_text('HỘ KINH DOANH NHÀ THUỐC QUỲNH ANH')
        # search_scheme = standardize_text('9.CT Cam Ranh')

        # --- DEBUGGING ---

        # 1. Create a mask ONLY for the customer
        # mask_customer = df['TENKH'].astype(str).apply(standardize_text) == search_customer
        # print(f"Matches for customer '{search_customer}': {mask_customer.sum()}")
        #
        # # 2. Create a mask ONLY for the scheme
        # mask_scheme = df['SCHEME'].astype(str).apply(standardize_text) == search_scheme
        # print(f"Matches for scheme '{search_scheme}': {mask_scheme.sum()}")

        print(f"AI Reasoning: {reasoning}")
        print("Extracted code:\n", code)

    except Exception as e:
        print(e)
        return {"result": None, "code": "", "error": f"❌ Lỗi sinh mã: {e}"}

    # ===== Code Execution =====
    try:
        exec(code, execution_env, execution_env)
    except KeyError as e:
        print(e)
        missing_col = str(e)
        return {"result": None, "code": code,
                "error": f"❌ Thiếu cột '{missing_col}'. Các cột có sẵn: {list(df.columns)}"}
    except Exception as e:
        print(e)
        return {"result": None, "code": code,
                "error": f"❌ Lỗi thực thi: {e}\nChi tiết DataFrame:\n- Kiểu dữ liệu: {df.dtypes.to_dict()}"}

    # ===== Result Handling =====
    result = execution_env.get("result")
    print("=============== The result code run by AI ")
    result = format_numbers_in_string(str(result))
    print(result[:100])


    if not result or len(result) > 3000:
        return {"result": None, "reason": None,
                "error": "⚠️ Không tìm thấy biến 'result'. Kiểm tra logic mã sinh."}

    return {
        "result": result,
        "reason": reasoning,
        "error": None
    }