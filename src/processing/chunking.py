from chonkie import SemanticChunker
from llm.ModelEmbedding import get_embedding_model_service

model_embedding_service = get_embedding_model_service()
# Basic initialization with default parameters
chunker = SemanticChunker(
    embedding_model=model_embedding_service,
    threshold=0.8,
    chunk_size=2048,
    similarity_window=3,
    skip_window=0
)

from chonkie import ChromaHandshake, SemanticChunker

print("Setting up ChromaDB handshake...")
handshake = ChromaHandshake(path="./query_retrieval_db")


# 5. SEARCH FUNCTION: This is the function you wanted to write
def search(query_text, n_results=2):
    """
    Searches the ChromaDB for the most relevant chunks based on a query.

    Args:
        query_text (str): The question or text to search for.
        n_results (int): The number of top results to return.

    Returns:
        list: A list of search result objects.
    """
    print(f"\n🔎 Searching for: '{query_text}'")
    search_results = handshake.search(query=query_text, n_results=n_results)
    return search_results

