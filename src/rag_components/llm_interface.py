from typing import List, Dict

from config import settings
from context_engine.rag_prompt import (
    CLASSIFICATION_SELECT_FILE_PROMPT,
    PANDAS_CODE_GENERATION_PROMPT,
    FINAL_ANSWER_PROMPT,
    REFORMULATION_PROMPT
)

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from llm.llm_langchain import gemini_llm_service, local_llm_service

def generate_classification_prompt(query: str) -> str:
    return CLASSIFICATION_SELECT_FILE_PROMPT.format(query=query)

pandas_code_prompt = ChatPromptTemplate.from_template(
    f"{PANDAS_CODE_GENERATION_PROMPT}\n\nUser query: {{user_query}}"
)

def _extract_code_from_markdown(text: str) -> str:
    """Extracts code from a markdown code block."""
    text = text.strip()
    if "```" in text:
        return text.split("```")[1].strip().replace("python", "").strip()
    return text

pandas_chain_cloud = (
    pandas_code_prompt
    | local_llm_service.bind(max_output_tokens=1024)
    | StrOutputParser()
    | _extract_code_from_markdown # Pipe the output into our helper!
)

# 1. Define the prompt template with multiple input variables
final_answer_prompt = ChatPromptTemplate.from_template(
    """Knowledge base: <<{knowledge_chunk}>>
    Your task: <<{task_prompt}>>
    User query: <<{user_query}>>
    Your answer:
    """
)

# 2. Create the chain (we'll make one and select the LLM during use)
def get_final_answer_chain(use_cloud: bool) -> Runnable:
    return (
        final_answer_prompt
        | local_llm_service.bind(max_output_tokens=1024) # Use max_output_tokens for Gemini
        | StrOutputParser()
    )


reformulation_prompt = ChatPromptTemplate.from_template(REFORMULATION_PROMPT) # Assuming the prompt has {chat_history} and {query}

# 2. Create the chain
reformulation_chain = (
    reformulation_prompt
    | gemini_llm_service.bind()
    | StrOutputParser()
)

# 3. Create the new async function that wraps the logic
async def reformulate_query_with_chain(query: str, chat_history: List[Dict], user_id="str") -> str:
    """Reformulates a query to be standalone if chat history exists."""

    if not chat_history:
        return query

    # Prepare inputs for the chain
    recent_history = chat_history[-5:]

    context_str = "\n".join(f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_history)

    print(context_str)

    # Invoke the chain
    reformulated = await reformulation_chain.ainvoke({
        "chat_history": context_str,
        "query": f"Tôi là user: {user_id}. {query}." ,
    })
    return reformulated.strip()