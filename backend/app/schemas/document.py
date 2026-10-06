import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    filename: str
    total_pages: int
    total_chunks: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total_count: int


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    page_number: int
    section_title: Optional[str]
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
