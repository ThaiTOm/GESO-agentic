import logging
from typing import List, Dict, Any
from .typesense_declare import TypesenseClient

logger = logging.getLogger(__name__)

def get_document_safe(doc_id: str, typesense_client: TypesenseClient, collection_name: str) -> Dict:
    try:
        doc = typesense_client.client.collections[collection_name].documents[doc_id].retrieve()
        return doc
    except Exception as e:
        logger.warning(f"Error retrieving document {doc_id}: {e}")
        return None

def get_all_chunks_of_page(uuid, page, typesense_client=None, found_collection=None):
    chunk_index = 0
    chunks = []
    while True:
        chunk_id = f"{uuid}_{page}_{chunk_index}"
        chunk_doc = get_document_safe(chunk_id, typesense_client, found_collection)
        if not chunk_doc:
            break
        chunks.append(chunk_doc.get("text", ""))
        chunk_index += 1
    return chunks

def perform_vector_search(collection_name: str, query_embedding: List[float], top_k: int, typesense_client: TypesenseClient) -> List[Dict]:
    """Performs a vector search using the Typesense client."""
    search_requests = {
        "searches": [
            {
                "collection": collection_name,
                "q": "*",
                "vector_query": f"embedding:([{','.join(map(str, query_embedding))}], k:{top_k * 5})",
                "include_fields": "id,text,title,page_num,chunk_num"
            }
        ]
    }
    multi_search_result = typesense_client.multi_search(search_requests)
    print(multi_search_result)
    return multi_search_result.get("results", [{}])[0].get("hits", [])