import hashlib
import pandas as pd
import time
from pydantic_ai import Agent

from src.llm.provider import LLMModels
from src.context_engine.rag_prompt import DATA_ANALYST_PANDAS_PROMPT

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

