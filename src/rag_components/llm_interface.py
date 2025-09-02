from typing import List, Dict

from llm.llm_call import get_structured_llm_output, get_raw_llm_output
from config import settings
from context_engine.rag_prompt import (
    CLASSIFICATION_SELECT_FILE_PROMPT,
    PANDAS_CODE_GENERATION_PROMPT,
    FINAL_ANSWER_PROMPT,
    REFORMULATION_PROMPT
)

def generate_classification_prompt(query: str) -> str:
    return CLASSIFICATION_SELECT_FILE_PROMPT.format(query=query)

async def generate_pandas_code(prompt: str) -> str:
    full_prompt = f"{PANDAS_CODE_GENERATION_PROMPT}\n\nUser query: {prompt}"
    result = await get_raw_llm_output(full_prompt, max_tokens=1024, cloud=not settings.SELF_HOST)
    # Extract the generated text
    content = result["choices"][0]["text"].strip()

    # Optionally extract code block if wrapped in triple backticks
    if "```" in content:
        return content.split("```")[1].strip().replace("python", "").strip()

    print("=>>>>>>>>>>>>>>>content", content.strip())
    return content.strip()



async def generate_final_answer(user_query: str, result_chunk: str, cloud=False) -> str:
    full_prompt = f"""Knowledge base: <<{result_chunk}>>
                      Your task: <<{FINAL_ANSWER_PROMPT}
                      User query: <<{user_query}>>
                      Your answer:
                      """
    print("*" * 100)
    print("==> full_prompt: ", full_prompt)
    result = await get_raw_llm_output(prompt=full_prompt, max_tokens=1024, cloud=cloud)

    # Extract the generated text
    content = result.strip()

    # Nếu kết quả trả về có bao code block thì tách phần code ra
    if "```" in content:
        return content.split("```")[1].strip().replace("python", "").strip()
    print("*" * 100)
    return content.strip()



async def reformulate_query(query: str, chat_history: List[Dict]) -> str:
    """Reformulates a query to be standalone if chat history exists."""
    if not chat_history:
        return query

    recent_history = chat_history[-2:]
    context_str = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in recent_history])
    prompt = REFORMULATION_PROMPT.format(chat_history=context_str, query=query)

    result = await get_raw_llm_output(prompt, max_tokens=256, cloud=not settings.SELF_HOST)
    return result.strip()