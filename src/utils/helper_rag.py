import requests

from rag_components.chatbot_manager import get_chatbot_name_by_api_key
from rag_components.llm_interface import reformulate_query_with_chain, get_final_answer_chain
from database.typesense_search import get_all_chunks_of_page, perform_vector_search
from typing_class.rag_type import *
from processing.document_processor import *
from llm.ModelEmbedding import get_embedding_model_service
embeddings_service = get_embedding_model_service()

from config import settings
import math
import sys, os
from pathlib import Path

sys.path.append(Path(os.getcwd(), "backend").as_posix())

from pydantic import BaseModel, Field
from loguru import logger
import logging
import os
import re
import uuid
import time
from typing import List, Dict, Any
from fastapi import UploadFile, HTTPException

from context_engine.rag_prompt import *

# --- Constants ---
DEFAULT_SEARCH_LIMIT = 100
MIN_QUESTION_LENGTH = 15
MAX_CONTEXT_LENGTH_CHARS = 8000 * 4  # ~8k tokens


import nest_asyncio

nest_asyncio.apply()
logger = logging.getLogger(__name__)
embedding_service = get_embedding_model_service()


# Function để tính độ tương đồng giữa chunk và query embedding
def compute_similarity(chunk_text, query_emb):
    try:
        chunk_emb = embedding_service.encode(chunk_text).tolist()
        # Tính cosine similarity
        dot_product = sum(a * b for a, b in zip(chunk_emb, query_emb))
        magnitude_a = math.sqrt(sum(a * a for a in chunk_emb))
        magnitude_b = math.sqrt(sum(b * b for b in query_emb))
        if magnitude_a * magnitude_b == 0:
            return 0
        return dot_product / (magnitude_a * magnitude_b)
    except Exception as e:
        print(f"Lỗi khi tính similarity: {str(e)}")
        return 0


# Function to chunk text into manageable pieces
def chunk_text(text, max_chars=1000, overlap=200):
    """
    Chia văn bản thành các đoạn nhỏ với kích thước phù hợp và có phần chồng lấp.

    Args:
        text (str): Văn bản cần chia
        max_chars (int): Số ký tự tối đa cho mỗi chunk
        overlap (int): Số ký tự chồng lấp giữa các chunk

    Returns:
        tuple: (chunks, chunk_indices) - danh sách chunks và vị trí của chúng
    """
    chunks = []
    chunk_indices = []

    # Nếu text rỗng, trả về list rỗng
    if not text:
        return [], []

    # Nếu text ngắn hơn max_chars, trả về trực tiếp
    if len(text) <= max_chars:
        return [text], [(0, len(text))]

    start = 0
    previous_end = 0  # Lưu vị trí kết thúc trước đó để kiểm tra tiến triển
    previous_chunks = set()  # Lưu các chunk đã xử lý để tránh lặp

    max_iterations = min(1000, len(text) // max(1, (max_chars - overlap)) + 10)
    iteration = 0

    while start < len(text) and iteration < max_iterations:
        iteration += 1
        end = min(start + max_chars, len(text))

        # Tìm điểm ngắt phù hợp nếu chưa đến cuối văn bản
        if end < len(text):
            # Ưu tiên ngắt tại đoạn văn
            para_break = text.rfind('\n\n', start, end)
            if para_break != -1 and para_break > start + (max_chars // 3):
                end = para_break + 2
            else:
                # Ngắt tại dấu chấm kết thúc câu
                sent_break = text.rfind('. ', start, end)
                if sent_break != -1 and sent_break > start + (max_chars // 3):
                    end = sent_break + 2
                else:
                    # Ngắt tại khoảng trắng
                    space = text.rfind(' ', start, end)
                    if space != -1 and space > start + (max_chars // 3):
                        end = space + 1

        # Kiểm tra xem có tiến triển không
        if end <= start:
            # Nếu không tìm được điểm ngắt phù hợp, cắt cứng tại max_chars
            end = min(start + max_chars, len(text))
            if end <= start:  # Vẫn không có tiến triển, thoát vòng lặp
                break

        # Đảm bảo có tiến triển so với vòng lặp trước
        if end <= previous_end:
            # Force tiến ít nhất 1 ký tự
            start = previous_end + 1
            if start >= len(text):
                break
            continue

        chunk = text[start:end]

        # Kiểm tra chunk trùng lặp
        if chunk in previous_chunks:
            # Vòng lặp đang lặp lại, hãy thoát
            break

        previous_chunks.add(chunk)
        chunks.append(chunk)
        chunk_indices.append((start, end))

        previous_end = end

        # Cập nhật vị trí bắt đầu mới, đảm bảo có tiến triển
        if len(text) - end < overlap:  # Gần cuối văn bản
            start = end  # Không chồng lấp nữa, lấy nốt đoạn cuối
        else:
            start = end - overlap

        # Đảm bảo start tiến ít nhất 1 ký tự để tránh lặp vô hạn
        start = max(start, previous_end - overlap, previous_end - max_chars // 2)

        # Kiểm tra thêm: Nếu phần còn lại quá nhỏ, gộp vào chunk cuối
        if len(text) - start < max_chars // 3:
            last_chunk = text[start:]
            if last_chunk.strip():  # Chỉ thêm nếu có nội dung có ý nghĩa
                chunks[-1] = chunks[-1] + last_chunk
                chunk_indices[-1] = (chunk_indices[-1][0], len(text))
            break

    # Xử lý trường hợp vẫn còn nội dung chưa xử lý sau khi đã đạt số vòng lặp tối đa
    if start < len(text) and iteration >= max_iterations:
        last_part = text[start:]
        # Chỉ thêm nếu có nội dung có ý nghĩa và khác với chunk cuối cùng
        if last_part.strip() and (not chunks or last_part != chunks[-1]):
            chunks.append(last_part)
            chunk_indices.append((start, len(text)))

    return chunks, chunk_indices


# Get context for a chunk
def get_context_for_chunk(hit, pdf_pages):
    page_num = hit['document']['page_num']
    chunk_num = hit['document']['chunk_num']

    # Get the full page text
    page_text = pdf_pages[page_num]

    # If it's the first chunk of a page and not the first page, add previous page
    if chunk_num == 0 and page_num > 0:
        context = pdf_pages[page_num - 1] + "\n\n" + page_text
    # If it's the last chunk of a page and not the last page, add next page
    elif chunk_num == len(chunk_text(page_text)[0]) - 1 and page_num < len(pdf_pages) - 1:
        context = page_text + "\n\n" + pdf_pages[page_num + 1]
    else:
        context = page_text

    return context


def search_documents(query_text, top_k=10):
    # Generate embedding for query
    query_embedding = embedding_service.encode(query_text).tolist()

    # Perform vector search using multi_search
    try:
        # Search by vector embedding similarity using multi_search
        vector_multi_search_params = {
            'searches': [
                {
                    'collection': 'pdf_documents',
                    'q': '*',  # Match all documents
                    'vector_query': f'embedding:({str(query_embedding)}, k:{top_k * 3})',
                    'limit': top_k * 2
                }
            ]
        }

        # Make the multi_search request for vector search
        multi_search_url = 'http://localhost:6211/multi_search'
        headers = {'X-TYPESENSE-API-KEY': settings.TYPESENSE_API_KEY}

        vector_response = requests.post(multi_search_url, headers=headers, json=vector_multi_search_params)

        # Check if the request was successful
        if vector_response.status_code == 200:
            vector_results = vector_response.json()['results'][0]
            vector_hits = vector_results.get('hits', [])
            # print(f"==> Vector search found: {len(vector_hits)} embedding vectors")
            # print("==> vector_results: ", vector_results)

            return vector_results
        else:
            print(f"Error with vector multi_search: {vector_response.text}")
            return {'hits': []}  # Return empty results if search fails
    except Exception as e:
        print(f"Error during vector search: {str(e)}")
        return {'hits': []}  # Return empty results if search fails



def format_numbers_in_string(text):
    """
    Finds sequences of digits in a string and formats those with 4 or more
    digits with comma thousand separators, *unless* they immediately follow
    a decimal point.

    Args:
      text: The input string.

    Returns:
      The string with relevant numbers formatted.
    """
    if not text:  # Handle empty string case
        return ""

    # Regular expression to find ANY sequence of one or more digits.
    # We'll check length and context in the replacement function.
    pattern = r'\d+'

    # Define a function to be used as the replacement in re.sub
    def replace_logic(match):
        # Get the matched number string
        number_str = match.group(0)
        # Get the start position of the match in the original string
        start_index = match.start()

        # Condition 1: Check length - don't format if less than 4 digits
        if len(number_str) < 4:
            return number_str  # Return original number string

        # Condition 2: Check context - don't format if immediately preceded by '.'
        # Make sure we don't check index -1 if the match is at the beginning
        if start_index > 0 and text[start_index - 1] == '.':
            return number_str  # Return original number string (it's after a decimal)

        # If conditions pass, format the number
        try:
            # Convert to integer
            number_int = int(number_str)
            # Format with commas
            return f"{number_int:,}"
        except ValueError:
            # Should not happen with \d+ but good practice
            return number_str  # Return original if conversion fails

    # Use re.sub to find all digit sequences and apply the replacement logic
    formatted_text = re.sub(pattern, replace_logic, text)
    return formatted_text

class FollowUpRequestsResult(BaseModel):
    """
    Pydantic model representing the agent's output.
    """
    thoughts: str
    inferred_user_intent: str
    dataset_limitation: str
    questions: List[str]

# --- Custom Exceptions for clear error handling ---
class InvalidAPIKeyError(Exception):
    pass


class DocumentProcessingError(Exception):
    pass



async def process_and_index_pdf(chatbot_name: str, file: UploadFile, typesense_client: Any) -> Dict[str, Any]:
    """Saves, processes, chunks, and indexes a PDF file into Typesense."""
    temp_dir = "./temp"
    os.makedirs(temp_dir, exist_ok=True)
    document_id = str(uuid.uuid4())
    temp_path = os.path.join(temp_dir, f"{document_id}.pdf")

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        pages = extract_text_from_pdf(temp_path)
        if not pages:
            raise DocumentProcessingError("Cannot extract text from PDF")

        documents = []
        for page_index, page_text in enumerate(pages):
            chunks, chunk_indices = chunk_text(page_text)
            for chunk_index, (chunk, indices) in enumerate(zip(chunks, chunk_indices)):
                doc = {
                    "id": f"{document_id}_{page_index}_{chunk_index}",
                    "title": file.filename,
                    "text": chunk,
                    "page_num": page_index + 1,
                    "chunk_num": chunk_index,
                    "start_index": indices[0] if indices else 0,
                    "end_index": indices[1] if indices else 0,
                    "embedding": embeddings_service.encode(chunk).tolist()
                }
                documents.append(doc)

        # Bulk import in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            try:
                typesense_client.client.collections[chatbot_name].documents.import_(batch)
            except Exception as e:
                logger.error(f"Error importing batch starting at index {i}: {e}")

        return {
            "document_id": document_id,
            "file_name": file.filename,
            "num_chunks": len(documents)
        }
    except Exception as e:
        logger.error(f"Error processing PDF '{file.filename}': {e}", exc_info=True)
        raise DocumentProcessingError(f"Failed to process and index PDF: {e}") from e
    finally:
        # FIX: Use a finally block to ensure cleanup
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as e:
                logger.warning(f"Could not remove temp file {temp_path}: {e}")

def _build_rag_context(hits: List[Dict], query_embedding: List[float], typesense_client: Any, collection_name: str) -> \
tuple[str, List[Dict]]:
    """Builds a comprehensive context from search results for the LLM."""
    if not hits:
        return "", []

    top_hit_doc = hits[0].get("document", {})
    top_document_id = top_hit_doc.get("id", "")

    sources = [{
        "document_id": top_document_id,
        "score": hits[0].get("vector_distance"),
        "file_name": top_hit_doc.get("title")
    }]

    context_chunks = []

    # Attempt to expand context around the best hit
    try:
        parts = top_document_id.rsplit("_", 2)
        if len(parts) == 3:
            doc_uuid, page_num_str, _ = parts
            page_num = int(page_num_str)

            # 1. Get all chunks from the hit's page
            context_chunks.extend(get_all_chunks_of_page(doc_uuid, page_num, typesense_client, collection_name))

            # 2. Get chunks from surrounding pages
            for offset in [-2, -1, 1, 2]:
                neighbor_page_num = page_num + offset
                if neighbor_page_num >= 0:
                    context_chunks.extend(
                        get_all_chunks_of_page(doc_uuid, neighbor_page_num, typesense_client, collection_name))
    except (ValueError, IndexError) as e:
        logger.warning(f"Could not parse doc ID '{top_document_id}' for context expansion: {e}")
        context_chunks.append(top_hit_doc.get("text", ""))

    # Add text from other top hits to the context pool
    for hit in hits[1:5]:
        doc = hit.get("document", {})
        context_chunks.append(doc.get("text", ""))
        sources.append({
            "document_id": doc.get("id"),
            "score": hit.get("vector_distance"),
            "file_name": doc.get("title")
        })

    # De-duplicate, score, and rank chunks to build final context
    unique_chunks = list(dict.fromkeys(context_chunks))
    scored_chunks = [(chunk, compute_similarity(chunk, query_embedding)) for chunk in unique_chunks]
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    # Build final context string, respecting token limits
    final_context_parts = []
    current_length = 0
    for chunk, _ in scored_chunks:
        if current_length + len(chunk) <= MAX_CONTEXT_LENGTH_CHARS:
            final_context_parts.append(chunk)
            current_length += len(chunk)
        else:
            break

    combined_context = "\n\n---\n\n".join(final_context_parts)
    return combined_context, sources


async def process_rag_query(request, api_key, typesense_client) -> Dict[str, Any]:
    """Orchestrates the entire RAG query process."""
    try:
        collection_name = get_chatbot_name_by_api_key(typesense_client, api_key)
        reformulated_query = await reformulate_query_with_chain(
            query=request.query,
            chat_history=request.chat_history
        )
        query_embedding = embeddings_service.encode(reformulated_query).tolist()

        hits = perform_vector_search(collection_name, query_embedding, request.top_k, typesense_client)
        if not hits:
            return {"answer": "I could not find an answer in the provided documents. Please try a different question.",
                    "sources": []}

        combined_context, sources = _build_rag_context(hits, query_embedding, typesense_client, collection_name)

        final_answer_chain = get_final_answer_chain(use_cloud=request.cloud_call)

        final_answer = await final_answer_chain.ainvoke({
            "knowledge_chunk": combined_context,
            "task_prompt": FINAL_ANSWER_PROMPT,
            "user_query": reformulated_query
        })

        return {
            "query": request.query,
            "answer": final_answer,
            "sources": sources,
            "context": combined_context,
            "metadata": {
                "collection": collection_name,
                "file_name": sources[0].get("file_name") if sources else "none",
                "original_query": request.query,
                "reformulated_query": reformulated_query
            }
        }
    except InvalidAPIKeyError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing RAG query: {e}", exc_info=True)
        # FIX: Log full error, return generic message
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing your query.")
