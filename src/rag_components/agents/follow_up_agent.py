import hashlib
import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from typing import List

from src.llm.provider import LLMModels
from src.context_engine.rag_prompt import FOLLOW_UP_QUESTION_PROMPT

class FollowUpRequestsResult(BaseModel):
    """Pydantic model representing the agent's output."""
    thoughts: str
    inferred_user_intent: str
    dataset_limitation: str
    questions: List[str]



class FollowUpQuestionAgent:
    _prompt_cache = {}
    default_instruction = (
        "--- CONTEXT --- \n"
        "**Original Query:** {query} \n"
        "**Analysis Result:** {analysis_result} \n"
        "**DataFrame Summary:** \n"
        "- Columns explain: Thang, Nam, Ma_khach_hang, Ma_he_thong, Don_vi, Dia_chi, Ma_SP, Ten_SP, So_luong, Doanh_so (see DataAnalystAgent for details) \n"
        "- Column Types (df.dtypes): \n"
        "{df_dtypes} \n"
        "- Descriptive Stats (df.describe()): \n"
        "{df.describe(include='all').to_markdown()} \n"
        "- Null Counts (df.isnull().sum()): \n"
        "{df.isnull().sum()} \n"
        "- Head (df.head()): \n"
        "{df.head(10).to_csv()} \n"
        "--- END CONTEXT --- \n"
        " \n"
        "Suggest 3-5 follow-up requests. Return requests only. \n"
    )

    def __init__(self, model=LLMModels.gemini_2_flash):
        self.model = model
        self._agent = None
        self._setup_agent()

    def _setup_agent(self):
        self._agent = Agent(
            system_prompt=FOLLOW_UP_QUESTION_PROMPT,
            model=self.model,
            retries=3,
            result_type=FollowUpRequestsResult
        )

    def get_agent(self):
        return self._agent

    @staticmethod
    def _hash_input(query: str, previous_response: str) -> str:
        """
        Generate a hash for caching based on the user input and previous response.
        """
        combined = (query + previous_response).encode('utf-8')
        return hashlib.md5(combined).hexdigest()

    def build_prompt(self, query: str, df: pd.DataFrame, analysis_result: str):
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
            "{analysis_result}", analysis_result
        )
        return prompt
