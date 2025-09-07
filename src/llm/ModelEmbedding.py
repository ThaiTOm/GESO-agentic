from config import settings
from sentence_transformers import SentenceTransformer
import torch
import numpy as np

# Base model Embedding
class EmbeddingModel:
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        print(device)
        self.model = SentenceTransformer(
            model_name,
            cache_folder=settings.MODEL_CACHE_DIR,
            device=device
        )
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self.max_seq_length = settings.EMBEDDING_MAX_SEQ_LENGTH

    def encode(self, texts, **kwargs) -> np.ndarray:
        """
        Encode a list of texts into embeddings.
        """
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            max_length=self.max_seq_length,
        )
        return embeddings

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
