import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class InvalidAPIKeyError(Exception):
    pass

def list_all_chatbots(typesense_client: Any) -> List[Dict[str, Any]]:
    """Retrieves a list of all chatbots from Typesense."""
    try:
        result = typesense_client.client.collections["chatbot_info"].documents.search({
            "q": "*",
            "query_by": "name",
            "per_page": 250  # Use per_page for clarity
        })
        # Correctly map documents, retrieving stored timestamps
        return [
            {
                "chatbot_id": doc.get("id"),
                "name": doc.get("name"),
                "description": doc.get("description", ""),
                "chatbot_api_key": doc.get("api_key"),
                "created_at": doc.get("created_at"),  # FIX: Use stored value
                "updated_at": doc.get("updated_at")  # FIX: Use stored value
            }
            for hit in result.get("hits", [])
            if (doc := hit.get("document"))
        ]
    except Exception as e:
        logger.error(f"Error retrieving chatbots: {e}", exc_info=True)
        raise



def get_chatbot_name_by_api_key(typesense_client: Any, api_key: str) -> str:
    """Validates an API key and returns the associated chatbot name."""
    try:
        result = typesense_client.client.collections["chatbot_info"].documents.search({
            "q": "*",
            "query_by": "api_key",
            "filter_by": f"api_key:={api_key}",
            "limit": 1
        })
        print(result)
        if hits := result.get("hits"):
            return hits[0]["document"]["name"]
        raise InvalidAPIKeyError("Invalid API Key provided.")
    except Exception as e:
        logger.error(f"Error validating API key: {e}", exc_info=True)
        if not isinstance(e, InvalidAPIKeyError):
            raise Exception("Could not validate API key.") from e
        raise