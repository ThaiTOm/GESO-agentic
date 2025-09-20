from abc import ABC
from typing import Callable, List

from chonkie import BaseEmbeddings

from config import settings
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

# Base model Embedding
class EmbeddingModel(BaseEmbeddings):
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        # The BaseEmbeddings __init__ can be called if needed, but it's empty in the example
        # super().__init__()
        super().__init__()
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        self.model = SentenceTransformer(
            model_name,
            cache_folder=settings.MODEL_CACHE_DIR,
            device=device
        )
        self.batch_size = settings.EMBEDDING_BATCH_SIZE

        # This property is not used by SentenceTransformer's encode method
        # self.max_seq_length = settings.EMBEDDING_MAX_SEQ_LENGTH

    # 1. IMPLEMENTED `embed` (Required by the abstract class)
    def embed(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        # We can call the more efficient batch method for a single item
        embedding = self.model.encode(
            text,
            batch_size=1  # Batch size of 1 for a single text
        )
        return np.array(embedding)

    # 2. OVERRIDE `embed_batch` for better performance (Optional but highly recommended)
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Embed a list of text strings into vector representations."""
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
        )
        # The output of model.encode is already a list of arrays
        return [np.array(e) for e in embeddings]

    # 3. IMPLEMENTED `dimension` (Required by the abstract class)
    @property
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        return self.model.get_sentence_embedding_dimension()

    # 4. IMPLEMENTED `get_tokenizer_or_token_counter` (Required by the abstract class)
    def get_tokenizer_or_token_counter(self) -> Callable[[str], int]:
        """Return a function that counts tokens for a given text."""
        # We return a lambda function that uses the model's tokenizer
        return lambda text: len(self.model.tokenizer.encode(text))

_embedding_model_instance = None

def get_embedding_model_service() -> EmbeddingModel:
    """
    Returns the singleton instance of the EmbeddingModel.
    Initializes it if it hasn't been initialized yet.
    """
    global _embedding_model_instance
    if _embedding_model_instance is None:
        _embedding_model_instance = EmbeddingModel() # Instantiate your wrapper class
    return _embedding_model_instance
