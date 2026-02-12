"""MCP Server for PDF-based UBO extraction.

This module provides a FastMCP server that exposes the UBO resolution pipeline
as MCP tools for ARK agents. It wraps the existing production-grade functions
from ubo_infra.app.usecases with MCP-friendly interfaces.

Architecture:
    - Uses FastMCP with Streamable HTTP transport for ARK compatibility
    - Wraps usecases.py functions for parsing, indexing, retrieval, extraction
    - Maintains all preprocessing, validation, and error handling from Streamlit app
    - Supports both local file paths and HTTP(S) URLs for PDF sources
    - Configuration loaded from centralized config system

Environment Variables (override config file):
    FASTMCP_HOST: Host to bind to (default: 0.0.0.0)
    FASTMCP_PORT: Port to bind to (default: 8080)
    OPENAI_API_KEY: OpenAI API key for extraction
    OPENAI_BASE_URL: OpenAI/AIGW base URL
    ANTHROPIC_API_KEY: Anthropic API key (if using Claude models)
    ANTHROPIC_BASE_URL: Anthropic base URL
    PERPLEXITY_API_KEY: Perplexity API key
    PERPLEXITY_BASE_URL: Perplexity base URL
    UBO_LLM_DEFAULT_PROVIDER: Default LLM provider (openai/anthropic)
    UBO_LLM_DEFAULT_MODEL: Default model name
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import traceback
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Domain entities for graph rendering
from ubo_domain.entities import Entity, EntityType, Evidence, OwnershipEdge

# Import UBO modules (installed as proper Python packages via pyproject.toml)
from ubo_infra.app.usecases import (
    build_or_load_index,
    compute_ubo_for_target,
    create_case_context,
    extract_edges_from_chunks,
    retrieve_ownership_chunks,
)

# Centralized configuration
from ubo_infra.config import get_config
from ubo_infra.extraction.batch_extract import MultiPassConfig
from ubo_infra.extraction.ownership_extractor import ExtractorConfig
from ubo_infra.extraction.validation import ValidationConfig

# Shared utilities
from ubo_infra.parsing.pdf_renderer import render_pdf_page
from ubo_infra.storage import get_storage

# Visualization service for graph rendering
from ubo_infra.visualization.graph_service import (
    render_ownership_graph as render_graph_impl,
)

# Load .env for local development
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load centralized configuration (from env vars, config file, defaults)
_app_config = get_config()

# Initialize FastMCP server with explicit host and port
mcp = FastMCP(
    "ubo-pdf-tools",
    host=os.getenv("FASTMCP_HOST", "0.0.0.0"),
    port=int(os.getenv("FASTMCP_PORT", "8080")),
)


async def _fetch_pdf(pdf_source: str) -> tuple[str, bytes]:
    """Fetch PDF from file path or URL.

    Args:
        pdf_source: Local file path or HTTP(S) URL to PDF document.

    Returns:
        Tuple of (filename, pdf_bytes).

    Raises:
        FileNotFoundError: If local file doesn't exist.
        httpx.HTTPError: If URL fetch fails.
        ValueError: If pdf_source is empty or invalid.
    """
    if not pdf_source or not pdf_source.strip():
        raise ValueError("pdf_source must be a non-empty string")

    pdf_source = pdf_source.strip()

    # Check if it's a URL
    if pdf_source.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(pdf_source)
            response.raise_for_status()
            
            # Extract filename from URL or use default
            filename = pdf_source.split("/")[-1]
            if not filename.endswith(".pdf"):
                filename = "document.pdf"
            
            return filename, response.content

    # Local file path
    file_path = Path(pdf_source)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_source}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {pdf_source}")
    
    return file_path.name, file_path.read_bytes()


@mcp.tool()
async def analyze_pdf_ownership(
    pdf_path: str,
    target_company: str,
    custom_queries: list[str] | None = None,
    extraction_model: str | None = None,
    extraction_provider: str | None = None,
    num_passes: int | None = None,
    min_votes: int | None = None,
    filter_self_loops: bool | None = None,
    filter_voting_only: bool | None = None,
    filter_subsidiaries: bool | None = None,
    min_confidence: float | None = None,
    ubo_threshold: float | None = None,
) -> dict[str, Any]:
    """Analyzes a PDF document to extract Ultimate Beneficial Owners (UBOs).

    This tool runs the complete UBO resolution pipeline:
    1. PDF Parsing - Extracts text from PDF pages
    2. Chunking & Indexing - Creates vector index for retrieval
    3. RAG Retrieval - Finds ownership-relevant chunks (uses custom_queries if provided)
    4. LLM Extraction - Extracts ownership relations with validation
    5. UBO Computation - Calculates effective ownership and identifies UBOs

    All preprocessing, validation, normalization, and deduplication from the
    production Streamlit app are applied.

    Configuration defaults are loaded from centralized config (env vars or config file).
    
    TIP: Call scout_pdf_for_ownership first to get custom_queries for better retrieval!

    Args:
        pdf_path: Path to PDF file (local path or HTTP(S) URL).
            Examples: "/path/to/annual_report.pdf", "https://example.com/report.pdf"
        target_company: Full legal name of the target company to analyze.
            Example: "Heineken N.V."
        custom_queries: Optional list of custom retrieval queries (from scout agent).
            If provided, these replace the default queries for better targeted retrieval.
            Example: ["Who are the major shareholders of Heineken N.V.?", ...]
        extraction_model: LLM model for extraction. None = use config default.
            Options: "gpt-4o", "gpt-4o-mini", "gpt-4", "claude-3-5-sonnet-20241022".
        extraction_provider: LLM provider. Options: "openai", "anthropic".
            Default: "openai".
        num_passes: Number of extraction passes for voting (improves reproducibility).
            Default: 1 (no voting). Recommended: 3 for production.
        min_votes: Minimum votes required to accept a relation (when num_passes > 1).
            Default: 1. Recommended: 2 when num_passes=3.
        filter_self_loops: Remove relations where owner == owned.
            Default: True (recommended).
        filter_voting_only: Remove relations that only specify voting rights.
            Default: True (focuses on capital ownership).
        filter_subsidiaries: Remove subsidiary table extractions (common false positives).
            Default: True (recommended).
        min_confidence: Minimum confidence threshold (0.0-1.0).
            Default: 0.0 (no filtering).
        ubo_threshold: Effective ownership threshold for UBO identification.
            Default: 0.25 (25%, regulatory standard).

    Returns:
        Dictionary containing:
            - entities: List of entities with {id, name, type, effective_ownership}
            - edges: List of ownership edges with {owner_id, owned_id, pct, voting_pct, 
                     ownership_kind, evidence: {doc_id, page, snippet}}
            - ubos: List of UBO entity IDs (persons with >= ubo_threshold effective ownership)
            - effective_ownership: Dict mapping entity_id -> effective ownership percentage
            - metadata: Pipeline execution metadata
                - case_id: Unique case identifier
                - target_company: Input target company name
                - total_chunks: Number of chunks indexed
                - retrieved_chunks: Number of chunks retrieved for extraction
                - extracted_relations: Number of raw extracted relations
                - validated_relations: Number after validation/filtering
                - duration_seconds: Total pipeline execution time
                - extraction_model: Model used
                - extraction_provider: Provider used

    Raises:
        FileNotFoundError: If local PDF file doesn't exist.
        ValueError: If inputs are invalid (empty strings, negative thresholds, etc.).
        httpx.HTTPError: If fetching PDF from URL fails.
        Exception: For pipeline errors (parsing, extraction, etc.) with detailed messages.

    Example:
        >>> result = await analyze_pdf_ownership(
        ...     pdf_path="https://example.com/heineken_annual_report.pdf",
        ...     target_company="Heineken N.V.",
        ...     extraction_model="gpt-4o",
        ...     num_passes=3,
        ...     min_votes=2
        ... )
        >>> print(f"Found {len(result['ubos'])} UBOs")
        >>> for entity in result['entities']:
        ...     if entity['id'] in result['ubos']:
        ...         print(f"UBO: {entity['name']} ({entity['effective_ownership']:.1%})")
    """
    # Apply config defaults for any None parameters
    cfg = _app_config
    extraction_model = extraction_model or cfg.llm.default_model
    extraction_provider = extraction_provider or cfg.llm.default_provider
    num_passes = num_passes if num_passes is not None else cfg.extraction.num_passes
    min_votes = min_votes if min_votes is not None else cfg.extraction.min_votes
    filter_self_loops = (
        filter_self_loops if filter_self_loops is not None
        else cfg.extraction.filter_self_loops
    )
    filter_voting_only = (
        filter_voting_only if filter_voting_only is not None
        else cfg.extraction.filter_voting_only
    )
    filter_subsidiaries = (
        filter_subsidiaries if filter_subsidiaries is not None
        else cfg.extraction.filter_subsidiaries
    )
    min_confidence = (
        min_confidence if min_confidence is not None
        else cfg.extraction.min_confidence
    )
    ubo_threshold = (
        ubo_threshold if ubo_threshold is not None
        else cfg.extraction.ubo_threshold
    )

    start_time = time.time()

    try:
        logger.info(f"[UBO] Starting analysis for: {pdf_path}")
        logger.info(f"[UBO] Target company: {target_company}")
        logger.info(f"[UBO] Config: model={extraction_model}, provider={extraction_provider}")
        
        # Input validation
        if not pdf_path or not pdf_path.strip():
            raise ValueError("pdf_path must be a non-empty string")
        if not target_company or not target_company.strip():
            raise ValueError("target_company must be a non-empty string")
        if num_passes < 1:
            raise ValueError("num_passes must be >= 1")
        if min_votes < 1 or min_votes > num_passes:
            raise ValueError(f"min_votes must be between 1 and {num_passes}")
        if not (0.0 <= min_confidence <= 1.0):
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        if not (0.0 <= ubo_threshold <= 1.0):
            raise ValueError("ubo_threshold must be between 0.0 and 1.0")
        
        logger.info("[UBO] Input validation passed")

        # Step 1: Fetch PDF
        logger.info(f"[UBO] Step 1: Fetching PDF from {pdf_path}")
        filename, pdf_bytes = await _fetch_pdf(pdf_path)
        logger.info(f"[UBO] Step 1 complete: {filename}, {len(pdf_bytes)} bytes")

        # Step 2: Create case context
        logger.info("[UBO] Step 2: Creating case context")
        ctx = create_case_context([(filename, pdf_bytes)])
        logger.info(f"[UBO] Step 2 complete: case_id={ctx.case.case_id}")

        # Step 3: Parse, chunk, and index
        logger.info("[UBO] Step 3: Building/loading index")
        total_chunks = build_or_load_index(ctx)
        logger.info(f"[UBO] Step 3 complete: {total_chunks} chunks indexed")

        # Step 4: Retrieve ownership chunks (use custom queries if provided)
        if custom_queries:
            logger.info(f"[UBO] Step 4: Retrieving with {len(custom_queries)} CUSTOM queries")
        else:
            logger.info("[UBO] Step 4: Retrieving ownership chunks (default queries)")
        retrieval_result = retrieve_ownership_chunks(
            ctx,
            bundle_name="annual_report",
            per_query_k=20,
            final_k=50,  # Increased for better coverage with custom queries
            filter_ownership=True,
            custom_queries=custom_queries,
        )
        logger.info(f"[UBO] Step 4 complete: {len(retrieval_result.documents)} chunks retrieved")

        # Step 5: Configure extraction
        logger.info(f"[UBO] Step 5: Configuring extraction (model={extraction_model})")
        extractor_cfg = ExtractorConfig(
            provider=extraction_provider,
            model=extraction_model,
        )

        multi_pass_cfg = MultiPassConfig(
            num_passes=num_passes,
            min_votes=min_votes,
        ) if num_passes > 1 else None

        validation_cfg = ValidationConfig(
            remove_self_loops=filter_self_loops,
            remove_voting_only=filter_voting_only,
            min_confidence=min_confidence,
            remove_zero_pct=True,
            dedupe_by_names=True,
        )
        logger.info("[UBO] Step 5 complete: extraction configured")

        # Step 6: Extract ownership edges
        # Returns: tuple[dict[str, Entity], list[OwnershipEdge], list[str], list[OwnershipOut]]
        #
        # IMPORTANT: When custom_queries are provided (from scout agent), we DISABLE
        # section filtering because the scout already found the relevant sections.
        # This ensures we don't miss Note 29, Related Parties, etc.
        should_filter_sections = custom_queries is None  # Only filter if no scout guidance
        logger.info(f"[UBO] Step 6: Extracting ownership edges (filter_sections={should_filter_sections})")
        entities_dict, edges, notes, unverified = await asyncio.to_thread(
            extract_edges_from_chunks,
            retrieval_result.documents,
            extractor_cfg=extractor_cfg,
            target_company=target_company,
            multi_pass_config=multi_pass_cfg,
            validation_config=validation_cfg,
            filter_section_types=should_filter_sections,  # Disabled when scout provided queries
            filter_subsidiaries=filter_subsidiaries,
        )
        logger.info(f"[UBO] Step 6 complete: {len(edges)} edges, {len(entities_dict)} entities")

        raw_edge_count = len(edges)

        # Step 7: Compute UBOs (this internally filters to upstream edges)
        # Returns: tuple[str, UBOResult, list[str]]
        logger.info(f"[UBO] Step 7: Computing UBOs (threshold={ubo_threshold})")
        logger.info(f"[UBO] Input: {len(edges)} edges, {len(entities_dict)} entities")
        logger.info(f"[UBO] Entity IDs: {list(entities_dict.keys())}")
        
        resolved_target_id, ubo_result, ubos = compute_ubo_for_target(
            entities=entities_dict,
            edges=edges,  # Pass ALL edges - function filters internally
            target_company_name=target_company,
            threshold=ubo_threshold,
        )
        logger.info(f"[UBO] Step 7 complete: Found {len(ubos)} UBOs (target_id={resolved_target_id})")
        
        # Get upstream edges for the response (filter after we know the correct target_id)
        from ubo_infra.graph.upstream_filter import filter_edges_upstream_of_target
        upstream_edges = filter_edges_upstream_of_target(edges, resolved_target_id)
        logger.info(f"[UBO] Filtered to {len(upstream_edges)} upstream edges")

        # Step 9: Build response
        entities_list = [
            {
                "id": ent.id,
                "name": ent.name,
                "type": ent.type.value,
                "effective_ownership": ubo_result.effective_ownership.get(ent.id, 0.0),
            }
            for ent in entities_dict.values()
        ]

        edges_list = [
            {
                "owner_id": edge.owner_id,
                "owner_name": entities_dict[edge.owner_id].name if edge.owner_id in entities_dict else edge.owner_id,
                "owned_id": edge.owned_id,
                "owned_name": entities_dict[edge.owned_id].name if edge.owned_id in entities_dict else edge.owned_id,
                "ownership_pct": edge.pct * 100 if edge.pct else None,
                "voting_pct": edge.voting_pct * 100 if edge.voting_pct else None,
                "ownership_kind": edge.ownership_kind.value if edge.ownership_kind else "unknown",
                "share_class": edge.share_class,
                "evidence": {
                    "doc_id": edge.evidence.doc_id if edge.evidence else None,
                    "page": edge.evidence.page if edge.evidence else None,
                    "snippet": edge.evidence.snippet if edge.evidence else None,
                } if edge.evidence else None,
            }
            for edge in upstream_edges
        ]

        duration = time.time() - start_time
        
        logger.info(f"[UBO] Analysis complete in {duration:.1f}s")
        logger.info(f"[UBO] Results: {len(entities_list)} entities, {len(edges_list)} edges, {len(ubos)} UBOs")

        # Build full results for storage
        case_id = ctx.case.case_id
        full_results = {
            "entities": entities_list,
            "edges": edges_list,
            "ubos": ubos,
            "effective_ownership": {
                ent_id: pct
                for ent_id, pct in ubo_result.effective_ownership.items()
            },
            "metadata": {
                "case_id": case_id,
                "target_company": target_company,
                "target_id": resolved_target_id,
                "total_chunks": total_chunks,
                "retrieved_chunks": len(retrieval_result.documents),
                "extracted_relations": raw_edge_count,
                "validated_relations": len(upstream_edges),
                "duration_seconds": round(duration, 2),
                "extraction_model": extraction_model,
                "extraction_provider": extraction_provider,
                "num_passes": num_passes,
                "min_votes": min_votes if num_passes > 1 else None,
                "pdf_path": pdf_path,  # Store for later retrieval
            },
        }

        # Store full results in storage layer
        storage = get_storage()
        storage_path = storage.store_json(case_id, "analysis.json", full_results)
        logger.info(f"[UBO] Stored analysis at: {storage_path}")

        # Collect unique evidence pages for reference
        evidence_pages = sorted(set(
            e["evidence"]["page"]
            for e in edges_list
            if e.get("evidence") and e["evidence"].get("page")
        ))

        # Build ownership table for display (text is fine, not base64 images)
        ownership_table = [
            {
                "owner": e["owner_name"],
                "owned": e["owned_name"],
                "ownership_pct": e.get("ownership_pct"),
                "voting_pct": e.get("voting_pct"),
                "type": e.get("ownership_kind", "unknown"),
                "evidence_page": e["evidence"]["page"] if e.get("evidence") else None,
                "snippet": (
                    e["evidence"]["snippet"][:150] + "..."
                    if e.get("evidence") and e["evidence"].get("snippet")
                    and len(e["evidence"]["snippet"]) > 150
                    else e["evidence"]["snippet"] if e.get("evidence") else None
                ),
            }
            for e in edges_list
        ]

        # Build UBO summary with effective ownership
        ubo_details = [
            {
                "name": e["name"],
                "effective_ownership_pct": round(
                    ubo_result.effective_ownership.get(e["id"], 0) * 100, 2
                ),
            }
            for e in entities_list
            if e["id"] in ubos
        ]

        # Return summary WITH ownership table (text is small, images are big)
        return {
            "case_id": case_id,
            "target_company": target_company,
            "ownership_table": ownership_table,
            "ubos": ubo_details,
            "summary": {
                "total_entities": len(entities_list),
                "total_edges": len(edges_list),
                "ubo_count": len(ubos),
                "evidence_pages": evidence_pages,
            },
            "duration_seconds": round(duration, 2),
            "storage_path": storage_path,
            "message": (
                f"Analysis complete. Found {len(ubos)} UBO(s) for {target_company}. "
                f"Full results stored at case_id={case_id}. "
                f"Use get_pdf_page_image(case_id, page) to store evidence images."
            ),
        }

    except Exception as e:
        # Log the full exception with traceback
        logger.error(f"[UBO] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[UBO] Traceback:\n{traceback.format_exc()}")
        # Re-raise with context
        error_msg = f"UBO analysis failed for '{pdf_path}': {type(e).__name__}: {e}"
        raise Exception(error_msg) from e


@mcp.tool()
async def get_pdf_page_image(
    case_id: str,
    page_number: int,
    dpi: int = 150,
    image_format: str = "png",
) -> dict[str, Any]:
    """Render and store a PDF page image for evidence visualization.

    This tool stores the rendered image in the storage layer and returns
    a reference. This avoids token limit issues from large base64 strings.

    IMPORTANT: Call analyze_pdf_ownership first to get the case_id.

    Args:
        case_id: Case ID from analyze_pdf_ownership result.
        page_number: Page number to render (1-indexed, matching evidence.page).
        dpi: Resolution for rendering (default: 150). Higher = better quality but larger.
        image_format: Image format - "png" (default) or "jpeg".

    Returns:
        Dictionary containing:
            - case_id: The case ID
            - page_number: The requested page number
            - storage_path: Path where image is stored
            - width: Image width in pixels
            - height: Image height in pixels
            - size_bytes: Image size in bytes
            - message: Human-readable status message

    Raises:
        FileNotFoundError: If case_id doesn't exist or PDF not found.
        ValueError: If page_number is out of range.

    Example:
        >>> # After analyze_pdf_ownership returns case_id="abc123":
        >>> result = await get_pdf_page_image(case_id="abc123", page_number=56)
        >>> print(result["message"])
        "Evidence image for page 56 stored at artifacts/abc123/evidence/page_56.png"
    """
    try:
        # Validate inputs
        if not case_id or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")
        if page_number < 1:
            raise ValueError("page_number must be >= 1")
        
        logger.info(f"[PDF_IMAGE] Rendering page {page_number} for case {case_id}")
        
        # Get storage and load analysis to find PDF path
        storage = get_storage()
        
        try:
            analysis = storage.load_json(case_id, "analysis.json")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Case {case_id} not found. Run analyze_pdf_ownership first."
            ) from None
        
        pdf_path = analysis.get("metadata", {}).get("pdf_path")
        if not pdf_path:
            raise ValueError(f"PDF path not found in case {case_id} analysis")
        
        logger.info(f"[PDF_IMAGE] Fetching PDF from {pdf_path}")
        
        # Fetch PDF bytes
        filename, pdf_bytes = await _fetch_pdf(pdf_path)
        
        # Render page
        result = render_pdf_page(
            pdf_bytes=pdf_bytes,
            page_number=page_number,
            dpi=dpi,
            image_format=image_format,
        )
        
        # Store image in storage layer
        image_filename = f"evidence/page_{page_number}.{image_format}"
        storage_path = storage.store_bytes(case_id, image_filename, result.image_bytes)
        
        logger.info(
            f"[PDF_IMAGE] Stored page {page_number}: {result.width}x{result.height}, "
            f"{len(result.image_bytes)} bytes at {storage_path}"
        )
        
        return {
            "case_id": case_id,
            "page_number": page_number,
            "storage_path": storage_path,
            "storage_uri": storage.get_uri(case_id, image_filename),
            "width": result.width,
            "height": result.height,
            "size_bytes": len(result.image_bytes),
            "total_pages": result.total_pages,
            "message": (
                f"Evidence image for page {page_number} stored. "
                f"Another agent can retrieve it from case_id={case_id}, "
                f"file={image_filename}"
            ),
        }
        
    except Exception as e:
        logger.error(f"[PDF_IMAGE] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[PDF_IMAGE] Traceback:\n{traceback.format_exc()}")
        raise


@mcp.tool()
async def get_analysis_results(case_id: str) -> dict[str, Any]:
    """Retrieve full analysis results from storage.

    Use this to get the complete ownership data after analyze_pdf_ownership.
    The viz agent should call this to get entities and edges for graph rendering.

    Args:
        case_id: Case ID from analyze_pdf_ownership result.

    Returns:
        Full analysis results including:
            - entities: List of entities with effective ownership
            - edges: List of ownership edges with evidence
            - ubos: List of UBO entity IDs
            - effective_ownership: Dict of entity_id -> percentage
            - metadata: Pipeline metadata

    Raises:
        FileNotFoundError: If case_id doesn't exist.

    Example:
        >>> results = await get_analysis_results(case_id="abc123")
        >>> print(f"Found {len(results['entities'])} entities")
    """
    try:
        if not case_id or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")
        
        logger.info(f"[GET_RESULTS] Loading analysis for case {case_id}")
        
        storage = get_storage()
        results = storage.load_json(case_id, "analysis.json")
        
        logger.info(
            f"[GET_RESULTS] Loaded: {len(results.get('entities', []))} entities, "
            f"{len(results.get('edges', []))} edges"
        )
        
        return results
        
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Case {case_id} not found. Run analyze_pdf_ownership first."
        ) from None
    except Exception as e:
        logger.error(f"[GET_RESULTS] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[GET_RESULTS] Traceback:\n{traceback.format_exc()}")
        raise


@mcp.tool()
async def list_case_evidence(case_id: str) -> dict[str, Any]:
    """List all stored evidence images for a case.

    Use this to see what evidence images have been rendered and stored.

    Args:
        case_id: Case ID from analyze_pdf_ownership result.

    Returns:
        Dictionary containing:
            - case_id: The case ID
            - evidence_files: List of stored evidence image info
            - analysis_available: Whether analysis.json exists
            - message: Human-readable summary

    Example:
        >>> evidence = await list_case_evidence(case_id="abc123")
        >>> for img in evidence["evidence_files"]:
        ...     print(f"Page {img['page']}: {img['uri']}")
    """
    try:
        if not case_id or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")
        
        logger.info(f"[LIST_EVIDENCE] Listing evidence for case {case_id}")
        
        storage = get_storage()
        
        # Check if analysis exists
        analysis_available = False
        try:
            storage.load_json(case_id, "analysis.json")
            analysis_available = True
        except FileNotFoundError:
            pass
        
        # List evidence files
        evidence_files = []
        evidence_dir = Path(storage.base_path) / case_id / "evidence"
        
        if evidence_dir.exists():
            for img_file in evidence_dir.iterdir():
                if img_file.is_file() and img_file.suffix in [".png", ".jpeg", ".jpg"]:
                    # Extract page number from filename (e.g., page_56.png)
                    match = re.match(r"page_(\d+)\.", img_file.name)
                    page_num = int(match.group(1)) if match else None
                    
                    evidence_files.append({
                        "filename": img_file.name,
                        "page": page_num,
                        "size_bytes": img_file.stat().st_size,
                        "uri": storage.get_uri(case_id, f"evidence/{img_file.name}"),
                    })
        
        evidence_files.sort(key=lambda x: x.get("page") or 0)
        
        logger.info(f"[LIST_EVIDENCE] Found {len(evidence_files)} evidence images")
        
        return {
            "case_id": case_id,
            "evidence_files": evidence_files,
            "evidence_count": len(evidence_files),
            "analysis_available": analysis_available,
            "message": (
                f"Case {case_id}: {len(evidence_files)} evidence image(s) stored. "
                f"Analysis {'available' if analysis_available else 'not found'}."
            ),
        }
        
    except Exception as e:
        logger.error(f"[LIST_EVIDENCE] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[LIST_EVIDENCE] Traceback:\n{traceback.format_exc()}")
        raise


@mcp.tool()
async def render_ownership_graph(
    case_id: str,
    renderer: Literal["plotly", "pyvis"] | None = None,
    theme: Literal["light", "dark"] = "light",
    width: int = 1200,
    height: int = 800,
    export_format: Literal["html", "png", "svg"] = "html",
) -> dict[str, Any]:
    """Render ownership graph from analysis results.

    Creates a visual representation of the ownership structure from a
    previous UBO analysis. The graph shows entities as nodes and ownership
    relationships as edges, with UBOs highlighted.

    IMPORTANT: Requires case_id from a previous analyze_pdf_ownership
    or research_ubo_web call.

    Args:
        case_id: Case ID from previous analysis (required).
        renderer: Graph renderer - "plotly" or "pyvis". If not specified,
            uses the default from app config (visualization.default_renderer).
            Note: PNG/SVG export requires "plotly" renderer.
        theme: Color theme - "light" (default) or "dark".
        width: Image/canvas width in pixels (default: 1200).
        height: Image/canvas height in pixels (default: 800).
        export_format: Output format - "html" (default), "png", or "svg".
            PNG and SVG are static images saved to local filesystem.

    Returns:
        Dictionary containing:
            - case_id: The case ID used
            - renderer: Renderer used (plotly/pyvis)
            - storage_path: Where the render is stored
            - local_path: Local filesystem path (for png/svg exports)
            - width: Rendered width
            - height: Rendered height
            - node_count: Number of entities in graph
            - edge_count: Number of ownership edges
            - message: Status message

    Raises:
        FileNotFoundError: If case_id doesn't exist.
        ValueError: If invalid parameters provided.

    Example:
        >>> result = await render_ownership_graph(
        ...     case_id="abc123",
        ...     renderer="plotly",
        ...     export_format="png"
        ... )
        >>> print(result["local_path"])
        "/path/to/output/abc123/ownership_graph.png"
    """
    try:
        # Validate inputs
        if not case_id or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")

        logger.info(f"[RENDER] Starting graph render for case {case_id}")

        # Load analysis from storage
        storage = get_storage()

        try:
            analysis = storage.load_json(case_id, "analysis.json")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Case {case_id} not found. "
                f"Run analyze_pdf_ownership or research_ubo_web first."
            ) from None

        entity_count = len(analysis.get("entities", []))
        logger.info(f"[RENDER] Loaded analysis with {entity_count} entities")

        # Convert analysis JSON to domain objects
        entities_dict: dict[str, Entity] = {}
        for entity_data in analysis.get("entities", []):
            entity_id = entity_data.get("id", "")
            entity_name = entity_data.get("name", "")

            # Skip invalid entities
            if not entity_id or not entity_name:
                logger.warning(f"[RENDER] Skipping invalid entity: {entity_data}")
                continue

            # Map type string to EntityType enum
            type_str = entity_data.get("type", "other").lower()
            entity_type_map = {
                "person": EntityType.PERSON,
                "company": EntityType.COMPANY,
                "trust": EntityType.TRUST,
            }
            entity_type = entity_type_map.get(type_str, EntityType.OTHER)

            entities_dict[entity_id] = Entity(
                id=entity_id,
                name=entity_name,
                type=entity_type,
            )

        # Convert edges to domain objects
        edges_list: list[OwnershipEdge] = []
        for edge_data in analysis.get("edges", []):
            owner_id = edge_data.get("owner_id", "")
            owned_id = edge_data.get("owned_id", "")

            # Skip invalid edges
            if not owner_id or not owned_id:
                logger.warning(f"[RENDER] Skipping invalid edge: {edge_data}")
                continue

            # Get ownership percentage (convert from % to fraction)
            # OwnershipEdge.pct is required, so default to 0.0 if missing
            ownership_pct = edge_data.get("ownership_pct")
            pct = ownership_pct / 100.0 if ownership_pct is not None else 0.0
            pct = max(0.0, min(1.0, pct))  # Clamp to [0, 1]

            voting_pct = edge_data.get("voting_pct")
            voting_pct_normalized = voting_pct / 100.0 if voting_pct is not None else None
            if voting_pct_normalized is not None:
                voting_pct_normalized = max(0.0, min(1.0, voting_pct_normalized))

            # Build evidence if all required fields are present
            evidence = None
            evidence_data = edge_data.get("evidence")
            if evidence_data:
                doc_id = evidence_data.get("doc_id")
                page = evidence_data.get("page")
                snippet = evidence_data.get("snippet")

                # Evidence requires all fields to be valid
                if doc_id and isinstance(page, int) and page >= 1 and snippet:
                    evidence = Evidence(
                        doc_id=doc_id,
                        page=page,
                        snippet=snippet,
                    )

            edges_list.append(OwnershipEdge(
                owner_id=owner_id,
                owned_id=owned_id,
                pct=pct,
                voting_pct=voting_pct_normalized,
                evidence=evidence,
            ))

        # Get UBO IDs and target ID from metadata
        ubo_ids: list[str] = []
        raw_ubos = analysis.get("ubos", [])
        if isinstance(raw_ubos, list):
            for ubo in raw_ubos:
                if isinstance(ubo, dict):
                    # Handle format: [{"name": "...", "id": "..."}, ...]
                    ubo_id = ubo.get("id") or ubo.get("name")
                    if ubo_id:
                        ubo_ids.append(ubo_id)
                elif isinstance(ubo, str):
                    # Handle format: ["entity_id_1", "entity_id_2"]
                    ubo_ids.append(ubo)

        target_id = analysis.get("metadata", {}).get("target_id", "")
        effective_ownership = analysis.get("effective_ownership", {})

        logger.info(
            f"[RENDER] Rendering graph: {len(entities_dict)} entities, "
            f"{len(edges_list)} edges, {len(ubo_ids)} UBOs"
        )

        # Determine renderer: use parameter if provided, else config default
        config = get_config()
        renderer_type: Literal["plotly", "pyvis"]
        if renderer is not None:
            renderer_type = renderer
        else:
            config_renderer = config.visualization.default_renderer
            renderer_type = (
                config_renderer
                if config_renderer in ("plotly", "pyvis")
                else "pyvis"
            )

        logger.info(f"[RENDER] Using renderer: {renderer_type}")

        # Render the graph
        graph_output = render_graph_impl(
            entities=entities_dict,
            edges=edges_list,
            target_id=target_id,
            ubo_ids=ubo_ids if ubo_ids else None,
            effective_ownership=effective_ownership if effective_ownership else None,
            theme=theme,
            width=width,
            height=height,
            renderer_type=renderer_type,
        )

        # Handle export format
        local_path = None
        
        if export_format in ("png", "svg"):
            # PNG/SVG export requires plotly
            if renderer_type != "plotly":
                logger.warning("[RENDER] PNG/SVG export requires plotly renderer, switching...")
                renderer_type = "plotly"
                graph_output = render_graph_impl(
                    entities=entities_dict,
                    edges=edges_list,
                    target_id=target_id,
                    ubo_ids=ubo_ids if ubo_ids else None,
                    effective_ownership=effective_ownership if effective_ownership else None,
                    theme=theme,
                    width=width,
                    height=height,
                    renderer_type="plotly",
                )
            
            # Export to static image using kaleido
            fig = graph_output.figure
            if fig is not None:
                try:
                    # Determine output path - save to local output directory
                    output_dir = Path.home() / "Desktop" / "alles_code" / "rabo" / "ubo-resolver" / "output" / case_id
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    filename = f"ownership_graph.{export_format}"
                    local_path = str(output_dir / filename)
                    
                    # Export using plotly's write_image (requires kaleido)
                    fig.write_image(local_path, format=export_format, width=width, height=height, scale=2)
                    
                    # Also save to storage
                    with open(local_path, "rb") as f:
                        img_bytes = f.read()
                    storage_path = storage.store_bytes(case_id, filename, img_bytes)
                    
                    logger.info(f"[RENDER] Graph exported to {local_path} ({len(img_bytes)} bytes)")
                except Exception as e:
                    logger.error(f"[RENDER] Failed to export {export_format}: {e}")
                    logger.info("[RENDER] Falling back to HTML export")
                    export_format = "html"
            else:
                logger.warning("[RENDER] No figure available for image export, falling back to HTML")
                export_format = "html"
        
        if export_format == "html":
            # HTML export (default)
            img_bytes = (
                graph_output.html.encode("utf-8")
                if graph_output.html else b""
            )
            filename = "graph.html"
            storage_path = storage.store_bytes(case_id, filename, img_bytes)
            
            # Also save to local output directory
            output_dir = Path.home() / "Desktop" / "alles_code" / "rabo" / "ubo-resolver" / "output" / case_id
            output_dir.mkdir(parents=True, exist_ok=True)
            local_path = str(output_dir / "ownership_graph.html")
            with open(local_path, "wb") as f:
                f.write(img_bytes)

        logger.info(f"[RENDER] Graph saved to {storage_path} ({len(img_bytes)} bytes)")

        return {
            "case_id": case_id,
            "renderer": renderer_type,
            "export_format": export_format,
            "storage_path": storage_path,
            "storage_uri": storage.get_uri(case_id, filename),
            "local_path": local_path,
            "width": width,
            "height": height,
            "node_count": len(entities_dict),
            "edge_count": len(edges_list),
            "ubo_count": len(ubo_ids),
            "size_bytes": len(img_bytes),
            "message": (
                f"Ownership graph rendered successfully as {export_format.upper()} using {renderer_type}. "
                f"{len(entities_dict)} entities, {len(edges_list)} edges, "
                f"{len(ubo_ids)} UBOs highlighted. "
                f"Saved to: {local_path}"
            ),
        }

    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"[RENDER] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[RENDER] Traceback:\n{traceback.format_exc()}")
        raise Exception(
            f"Graph rendering failed for case {case_id}: {type(e).__name__}: {e}"
        ) from e


@mcp.tool()
async def get_current_config() -> dict[str, Any]:
    """Returns the current configuration (non-sensitive values only).

    Useful for debugging and verifying which settings are active.

    Returns:
        Dictionary with current configuration summary.
    """
    cfg = _app_config
    return {
        "llm": {
            "default_provider": cfg.llm.default_provider,
            "default_model": cfg.llm.default_model,
            "openai": {
                "base_url": cfg.llm.openai.base_url or "(default)",
                "timeout_seconds": cfg.llm.openai.timeout_seconds,
            },
            "anthropic": {
                "base_url": cfg.llm.anthropic.base_url or "(default)",
                "timeout_seconds": cfg.llm.anthropic.timeout_seconds,
            },
            "perplexity": {
                "base_url": cfg.llm.perplexity.base_url or "(default)",
                "timeout_seconds": cfg.llm.perplexity.timeout_seconds,
            },
        },
        "storage": {
            "backend": cfg.storage.backend,
            "base_path": cfg.storage.base_path,
        },
        "extraction": {
            "num_passes": cfg.extraction.num_passes,
            "min_votes": cfg.extraction.min_votes,
            "ubo_threshold": cfg.extraction.ubo_threshold,
            "filter_self_loops": cfg.extraction.filter_self_loops,
            "filter_voting_only": cfg.extraction.filter_voting_only,
            "filter_subsidiaries": cfg.extraction.filter_subsidiaries,
        },
        "visualization": {
            "default_renderer": cfg.visualization.default_renderer,
            "default_theme": cfg.visualization.default_theme,
        },
    }


@mcp.tool()
async def scout_pdf_for_ownership(
    pdf_source: str,
    target_company: str,
    full_scan: bool = True,
) -> dict[str, Any]:
    """Comprehensively scout a PDF to find ALL ownership-related content.
    
    Philosophy: Scan EVERYTHING. No sampling, no shortcuts.
    
    This scans the ENTIRE PDF and identifies ALL pages/sections with ownership
    information, extracts ALL entities and percentages, and generates
    comprehensive retrieval queries.
    
    ALWAYS CALL THIS BEFORE analyze_pdf_ownership for best results.
    
    Args:
        pdf_source: URL or local path to PDF document.
        target_company: Name of the company being analyzed.
        full_scan: If True (default), scan ALL pages. Set to False only for testing.
    
    Returns:
        Dictionary containing:
            - total_pages: Total pages in PDF
            - pages_scanned: Number of pages actually scanned
            - relevant_pages: List of ALL page numbers with ownership content
            - sections_found: ALL section headers with ownership info
            - entities_found: ALL entities with their types and pages mentioned
            - percentages_found: ALL percentages with context and page numbers
            - recommended_queries: Comprehensive queries for RAG retrieval (15-30)
            - sample_text: Sample text from relevant pages
            - ownership_keywords_by_page: Keywords found on each page
            - message: Summary of findings
    
    Example:
        >>> scout = await scout_pdf_for_ownership(
        ...     "http://example.com/annual_report.pdf",
        ...     "Company Name",
        ...     full_scan=True
        ... )
        >>> # Use ALL recommended_queries with analyze_pdf_ownership
        >>> print(len(scout["recommended_queries"]))  # 15-30 queries
    """
    try:
        from scout_tools import scan_pdf_for_ownership
        
        logger.info(f"[SCOUT] Starting COMPREHENSIVE PDF scan for: {pdf_source}")
        logger.info(f"[SCOUT] Target company: {target_company}")
        logger.info(f"[SCOUT] Full scan: {full_scan}")
        
        # Fetch PDF if URL
        if pdf_source.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.get(pdf_source)
                resp.raise_for_status()
                pdf_bytes = resp.content
            logger.info(f"[SCOUT] Downloaded PDF: {len(pdf_bytes)} bytes")
        else:
            pdf_path = Path(pdf_source)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_source}")
            pdf_bytes = pdf_path.read_bytes()
        
        # Run the comprehensive scout
        result = scan_pdf_for_ownership(
            pdf_source=pdf_bytes,
            target_company=target_company,
            full_scan=full_scan,
        )
        
        logger.info(f"[SCOUT] Scan complete: {result.pages_scanned}/{result.total_pages} pages scanned")
        logger.info(f"[SCOUT] Relevant pages: {len(result.relevant_pages)}")
        logger.info(f"[SCOUT] Entities found: {len(result.entities_mentioned)}")
        logger.info(f"[SCOUT] Percentages found: {len(result.percentages_found)}")
        logger.info(f"[SCOUT] Queries generated: {len(result.suggested_queries)}")
        
        # Convert entities to serializable format
        entities_json = [
            {
                "name": e.name,
                "type": e.entity_type,
                "pages_mentioned": e.pages_mentioned,
                "ownership_signals": e.ownership_signals,
            }
            for e in result.entities_mentioned
        ]
        
        # Convert percentages to serializable format
        percentages_json = [
            {
                "value": p.value,
                "raw_text": p.raw_text,
                "page": p.page,
                "context": p.context,
            }
            for p in result.percentages_found
        ]
        
        return {
            "total_pages": result.total_pages,
            "pages_scanned": result.pages_scanned,
            "relevant_pages": result.relevant_pages,
            "relevant_page_count": len(result.relevant_pages),
            "sections_found": result.sections_found,
            "entities_found": entities_json,
            "percentages_found": percentages_json,
            "recommended_queries": result.suggested_queries,
            "sample_text": result.sample_text,
            "ownership_keywords_by_page": result.ownership_keywords_by_page,
            "ready_for_extraction": True,
            "message": (
                f"COMPREHENSIVE SCAN COMPLETE. "
                f"Scanned {result.pages_scanned}/{result.total_pages} pages. "
                f"Found {len(result.relevant_pages)} pages with ownership content. "
                f"Identified {len(result.entities_mentioned)} entities and {len(result.percentages_found)} percentages. "
                f"Generated {len(result.suggested_queries)} retrieval queries. "
                f"IMPORTANT: Pass ALL recommended_queries to analyze_pdf_ownership for best results!"
            ),
        }
        
    except Exception as e:
        logger.error(f"[SCOUT] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[SCOUT] Traceback:\n{traceback.format_exc()}")
        raise


@mcp.resource("health://status")
def health_check() -> dict[str, str]:
    """Health check endpoint for Kubernetes probes.

    Returns:
        Dictionary with status="healthy" and service name.
    """
    return {"status": "healthy", "service": "ubo-pdf-tools"}


def main():
    """Run the MCP server over Streamable HTTP.
    
    The server binds to the host and port specified in the constructor
    (from FASTMCP_HOST and FASTMCP_PORT environment variables).
    The MCP endpoint is served at /mcp by default.
    """
    cfg = _app_config
    
    print("=" * 60)
    print("Starting UBO PDF Tools MCP Server")
    print("=" * 60)
    print()
    print("Server:")
    print(f"  Host: {mcp.settings.host}")
    print(f"  Port: {mcp.settings.port}")
    print("  Endpoint: /mcp")
    print()
    print("Configuration:")
    print(f"  Default Provider: {cfg.llm.default_provider}")
    print(f"  Default Model: {cfg.llm.default_model}")
    print(f"  Storage Backend: {cfg.storage.backend}")
    print(f"  UBO Threshold: {cfg.extraction.ubo_threshold * 100:.0f}%")
    print()
    print("API Keys:")
    print(f"  OpenAI: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not Set'}")
    print(f"  Anthropic: {'Set' if os.getenv('ANTHROPIC_API_KEY') else 'Not Set'}")
    print(f"  Perplexity: {'Set' if os.getenv('PERPLEXITY_API_KEY') else 'Not Set'}")
    print()
    print("Base URLs:")
    print(f"  OpenAI: {cfg.llm.openai.base_url or '(default)'}")
    print(f"  Anthropic: {cfg.llm.anthropic.base_url or '(default)'}")
    print(f"  Perplexity: {cfg.llm.perplexity.base_url or '(default)'}")
    print("=" * 60)
    print()
    
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
