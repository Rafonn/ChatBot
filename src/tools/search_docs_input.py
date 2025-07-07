from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Optional

"""
This module defines the input schema for searching documents.
"""


class SearchDocsInput(BaseModel):
    query: str = Field(
        description="A pergunta detalhada do usuário para buscar em documentos e na web."
    )
    source_filter: Optional[dict] = Field(
        default=None,
        description="Filtro opcional para a busca interna. Ex: {'file_name': 'manual.pdf'}",
    )
