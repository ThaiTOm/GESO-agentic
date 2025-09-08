from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Union
from fastapi import UploadFile

class SpeakingRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, Any]]] = None
    voice: Optional[bool] = False
    voice_data: UploadFile = None