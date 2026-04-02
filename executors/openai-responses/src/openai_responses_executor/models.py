"""Pydantic models for OpenAI Responses API tool declarations."""

from typing import List, Literal, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Web search
# ---------------------------------------------------------------------------


class WebSearchUserLocation(BaseModel):
    """Approximate location hint passed to the web_search_preview tool."""

    type: Literal["approximate"] = "approximate"
    country: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None


class WebSearchTool(BaseModel):
    """OpenAI built-in web search tool."""

    type: Literal["web_search_preview"] = "web_search_preview"
    user_location: Optional[WebSearchUserLocation] = None
    # "low", "medium", "high" — controls how much context is retrieved
    search_context_size: Optional[Literal["low", "medium", "high"]] = None


# ---------------------------------------------------------------------------
# File search
# ---------------------------------------------------------------------------


class FileSearchRankingOptions(BaseModel):
    """Ranking options for file search results."""

    ranker: Optional[Literal["auto", "default_2024_08_21"]] = None
    # Only return results above this score threshold (0.0 - 1.0)
    score_threshold: Optional[float] = None


class FileSearchTool(BaseModel):
    """OpenAI built-in file search tool.

    ``vector_store_ids`` are runtime parameters — they should come from the
    Query CR (e.g. ``spec.tools.file_search.vector_store_ids``) rather than
    being hardcoded on the Agent CR.
    """

    type: Literal["file_search"] = "file_search"
    vector_store_ids: Optional[List[str]] = None
    max_num_results: Optional[int] = None
    ranking_options: Optional[FileSearchRankingOptions] = None


# ---------------------------------------------------------------------------
# Code interpreter
# ---------------------------------------------------------------------------


class CodeInterpreterContainer(BaseModel):
    """Container configuration for the code interpreter tool."""

    # "auto" lets OpenAI manage the container lifecycle;
    # a specific container ID reuses an existing container across turns.
    type: Literal["auto"] = "auto"


class CodeInterpreterTool(BaseModel):
    """OpenAI built-in code interpreter tool."""

    type: Literal["code_interpreter"] = "code_interpreter"
    container: Optional[CodeInterpreterContainer] = None


# ---------------------------------------------------------------------------
# Computer use
# ---------------------------------------------------------------------------


class ComputerUseTool(BaseModel):
    """OpenAI built-in computer use tool."""

    type: Literal["computer_use_preview"] = "computer_use_preview"
    display_width: Optional[int] = None
    display_height: Optional[int] = None
