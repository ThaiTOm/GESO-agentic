import hashlib
import pandas as pd
from pydantic_ai import Agent

from llm.provider import LLMModels
from context_engine.rag_prompt import DATA_ANALYST_PANDAS_PROMPT
from utils.helper_rag import format_numbers_in_string
import numpy as np

class DataAnalystAgent:
    _transform_cache = {}

    default_instruction = (
        "Hôm nay là ngày {time.strftime('%d/%m/%Y')}.\n\n"
        "Data đã được load vào variable `df`. "
        "Dưới đây là các thông tin mô tả DataFrame: \n"
        "####"

        "- Kiểu dữ liệu các cột (df.dtypes): \n"
        "{df.dtypes} \n\n"

        "- Thống kê mô tả (df.describe(include='all')): \n"
        "{df.describe(include='all').to_markdown()}\n\n"

        "- Số lượng giá trị null (df.isnull().sum()): \n"
        "{df.isnull().sum()}\n\n"

        "- ví dụ các giá trị của cột: \n"
        "{column_examples}\n\n"

        "- 10 dòng đầu tiên (df.head()): \n"
        "{df.head(10).to_csv()}\n\n"

        "Câu hỏi của bạn là: {query}"
    )

    def __init__(self, model=LLMModels.or_gemini_2_5_pro):
        self.model = model
        self._agent = None
        self._setup_agent()

    def _setup_agent(self):
        self._agent = Agent(
            system_prompt=DATA_ANALYST_PANDAS_PROMPT,
            model=self.model,
            retries=3
        )

    def get_agent(self):
        return self._agent

    def build_prompt(self, query: str, df: pd.DataFrame):
        # Generate the column examples dictionary as a string
        column_examples = {}
        for col in df.columns:
            column_examples[col] = df[col].dropna().unique()[:30].tolist()

        # Format the prompt with all the necessary replacements
        prompt = self.default_instruction.replace(
            "{df.dtypes}", df.dtypes.to_markdown()
        ).replace(
            "{df.describe(include='all').to_markdown()}", str(df.describe(include='all').to_markdown())
        ).replace(
            "{df.isnull().sum()}", str(df.isnull().sum())
        ).replace(
            "{df.head(10).to_csv()}", str(df.head(10).to_csv())
        ).replace(
            "{query}", query
        ).replace(
            "{column_examples}", str(column_examples)
        )
        return prompt

    @staticmethod
    def _hash_df(df: pd.DataFrame) -> str:
        """Generate a hash for the DataFrame content."""
        # Consider sorting columns to make it order-independent
        df_bytes = pd.util.hash_pandas_object(df, index=True).values.tobytes()
        return hashlib.md5(df_bytes).hexdigest()

    @classmethod
    def transform_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Cached transformation using hash of DataFrame content."""
        df_hash = cls._hash_df(df)

        if df_hash in cls._transform_cache:
            return cls._transform_cache[df_hash]

        transformed = df.copy()
        transformed.columns = transformed.columns.str.lower().str.strip()

        for col in transformed.columns:
            if transformed[col].dtype == 'object':
                transformed[col] = transformed[col].str.lower()

        cls._transform_cache[df_hash] = transformed
        return transformed


def analyze_dataframe(query: str, df: pd.DataFrame, master_data: str, row_rules:dict, user_id:str, user_role:str) -> dict:
    """
    Phân tích dữ liệu dạng bảng (CSV/Excel).
    Chỉ sử dụng tool này nếu người dùng hỏi về bảng, con số, dữ liệu dạng bảng.
    Tool sẽ tự lấy file pickle mới nhất trong working_data/.
    """
    # ===== Data Preprocessing =====
    try:
        print("The user role is ", user_role )
        print("The user id is ", user_id )
        row_rules = row_rules['rowRules']
        roles = row_rules.keys()
        if user_id != 'duythai':
            for role in roles:
                print("The role of current is ", role)
                if role == user_role:
                    print('This go inside ')
                    print("we have ", row_rules[role])
                    for permission in row_rules[role]:
                        print(permission, permission["column"])
                        df = df[df[permission["column"]] == int(user_id)]
                        print("we run into this read along column")

        # init class DataAnalystAgent
        # Chèn Master Data vào vị trí '####'
        modified_instruction = DataAnalystAgent.default_instruction.replace(
            "####",
            f"\n\n--- MASTER DATA --- \n**Master Data:** {master_data} \n\n"
        )

        # Sau đó gán lại cho class
        DataAnalystAgent.default_instruction = modified_instruction

        # Sau đó mới tiến hành transform DataFrame
        df = DataAnalystAgent.transform_df(df)  # Use cached transformation
    except Exception as e:
        return {"result": None, "code": "", "error": f"❌ Tiền xử lý DataFrame thất bại: {e}"}

    # ===== Environment Setup =====
    execution_env = {
        "df": df.copy(),  # Prevent mutation of original DataFrame
        "pd": pd,  # Provide pandas as global variable
        "np": np  # Provide numpy as global variable
    }

    # ===== Code Generation =====
    analyst = DataAnalystAgent(model=LLMModels.or_gemini_flash)
    try:
        prompt = analyst.build_prompt(query=query, df=df)
        print(prompt)
        raw_code = analyst.get_agent().run_sync(prompt).output
        print(raw_code)
        code = raw_code.replace('```python', '').replace('```', '').strip()

    except Exception as e:
        print(e)
        return {"result": None, "code": "", "error": f"❌ Lỗi sinh mã: {e}"}

    # ===== Code Execution =====
    try:
        exec(code, execution_env, execution_env)
    except KeyError as e:
        missing_col = str(e).split("'")[1]
        return {"result": None, "code": code,
                "error": f"❌ Thiếu cột '{missing_col}'. Các cột có sẵn: {list(df.columns)}"}
    except Exception as e:
        return {"result": None, "code": code,
                "error": f"❌ Lỗi thực thi: {e}\nChi tiết DataFrame:\n- Kiểu dữ liệu: {df.dtypes.to_dict()}"}

    # ===== Result Handling =====
    result = execution_env.get("result")
    result = format_numbers_in_string(str(result))
    if not result:
        return {"result": None, "code": code,
                "error": "⚠️ Không tìm thấy biến 'result'. Kiểm tra logic mã sinh."}

    return {
        "result": result,
        "code": code,
        "error": None
    }