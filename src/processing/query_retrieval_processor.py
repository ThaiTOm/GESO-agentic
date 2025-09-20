#
# File: query_pipeline.py
#
from typing import Dict, Optional, Literal

# Assuming these are in your project structure
from llm.ModelEmbedding import EmbeddingModel, get_embedding_model_service
from chonkie import ChromaHandshake


class QueryClassifierPipeline:
    """
    A pipeline for classifying incoming queries against a predefined set of categories
    using semantic similarity in a vector database.
    """

    def __init__(
            self,
            embedding_model: EmbeddingModel,
            db_handshake: ChromaHandshake,
            categories: Optional[Dict[str, str]] = None,
            threshold: float = 1.0
    ):
        """
        Initializes the classification pipeline.

        Args:
            embedding_model (EmbeddingModel): The sentence-transformer model service.
            db_handshake (ChromaHandshake): The ChromaDB connection manager.
            categories (Dict[str, str]): A dictionary where keys are category names (e.g., "Billing")
                                          and values are descriptive paragraphs for that category.
            threshold (float): The maximum distance for a query to be considered a match.
                               For ChromaDB's default L2 (Euclidean) distance, a lower value is stricter.
                               A good starting point might be 1.0.
        """

        self.embedding_model = embedding_model
        self.db_handshake = db_handshake
        self.collection = db_handshake.collection  # Get a direct reference to the collection
        self.categories = categories or {}
        self.threshold = threshold
        print("✅ QueryClassifierPipeline initialized.")
        print(f"   - Collection: '{self.collection.name}'")
        print(f"   - Categories to manage: {list(self.categories.keys())}")
        print(f"   - Similarity Threshold (L2 Distance): {self.threshold}")

    def index_categories(self) -> None:
        """
        Embeds and stores the category descriptions currently held by the pipeline.
        If no categories are loaded, this method does nothing.
        """
        # --- CHANGE 3: Gracefully handle having no categories to index ---
        if not self.categories:
            print("ℹ️ No categories to index. Use `add_or_update_category` to add data.")
            return

        print(f"\n🔄 Indexing {len(self.categories)} categories...")
        category_names = list(self.categories.keys())
        category_descriptions = list(self.categories.values())

        embeddings = self.embedding_model.embed_batch(category_descriptions)

        self.collection.upsert(
            ids=category_names,
            embeddings=[e.tolist() for e in embeddings],
            documents=category_descriptions
        )
        print(f"✅ Successfully indexed {len(category_names)} categories.")

    def add_or_update_category(self, category_name: str, category_description: str):
        """
        Embeds and upserts a single category into the vector database.
        """
        print(f"\n🔄 Upserting single category: '{category_name}'")
        embedding = self.embedding_model.embed(category_description)
        self.collection.upsert(
            ids=[category_name],
            embeddings=[embedding.tolist()],
            documents=[category_description]
        )
        self.categories[category_name] = category_description
        print(f"✅ Successfully upserted '{category_name}'.")

    def classify(self, query_text: str) -> Optional[Literal["FOUND", "NOT_FOUND"]]:
        # This method requires no changes. It's already robust.
        query_embedding = self.embedding_model.embed(query_text)
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=1
        )

        if not results or not results.get('ids') or not results['ids'][0]:
            print(f"\n🔎 Query: '{query_text}'")
            print("   -> Classification: 'Unknown' (no categories in the database to compare against).")
            return "NOT_FOUND"

        closest_category = results['ids'][0][0]
        distance = results['distances'][0][0]

        print(f"\n🔎 Query: '{query_text}'")
        print(f"   -> Closest Match: '{closest_category}' (Distance: {distance:.4f})")

        if distance <= self.threshold:
            print(f"   -> Classification: '{closest_category}' (within threshold of {self.threshold})")
            return "FOUND"
        else:
            print(f"   -> Classification: 'Unknown' (distance exceeds threshold of {self.threshold})")
            return "NOT_FOUND"

    def __call__(self, query_text: str) -> Optional[Literal["FOUND", "NOT_FOUND"]]:
        return self.classify(query_text)

    def sync_from_db(self):
        """
        Loads all existing data from the ChromaDB collection into the pipeline's
        in-memory 'self.categories' dictionary. This is crucial for synchronizing
        state when the application restarts.
        """
        print("🔄 Syncing pipeline state from database...")

        # The .get() method in ChromaDB retrieves records.
        # By not providing IDs, we get all of them.
        all_items = self.collection.get()

        if not all_items or not all_items['ids']:
            print("ℹ️ Database collection is empty. No categories to sync.")
            return

        # Reconstruct the categories dictionary from the database records
        synced_categories = {
            doc_id: doc
            for doc_id, doc in zip(all_items['ids'], all_items['documents'])
        }

        self.categories = synced_categories
        print(f"✅ Sync complete. Loaded {len(self.categories)} categories from the database.")


# This global variable will hold our single instance
_pipeline_instance: Optional[QueryClassifierPipeline] = None


def get_classifier_pipeline() -> QueryClassifierPipeline:
    """
    Returns the singleton instance of the QueryClassifierPipeline.
    Initializes it on the first call.
    """
    global _pipeline_instance

    # This is the core logic: only create the instance if it doesn't exist yet
    if _pipeline_instance is None:
        print("🚀 Initializing QueryClassifierPipeline for the first time...")

        # 1. Get the shared dependencies (which are also singletons)
        model_embedding_service = get_embedding_model_service()
        handshake = ChromaHandshake(
            path="./classification_db",
            collection_name="global_classifier"
        )

        # 2. Create the pipeline instance
        # We start it empty, as it will sync with the database.
        _pipeline_instance = QueryClassifierPipeline(
            embedding_model=model_embedding_service,
            db_handshake=handshake,
            threshold=55
        )

        # 3. (IMPORTANT) Sync the pipeline's memory with the database on startup
        _pipeline_instance.sync_from_db()  # We need to add this method! See Step 2.

    return _pipeline_instance