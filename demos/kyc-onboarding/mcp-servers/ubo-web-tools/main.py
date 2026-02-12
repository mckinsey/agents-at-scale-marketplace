"""MCP Server for web-based UBO research.

This module provides a FastMCP server that exposes web research capabilities
for Ultimate Beneficial Owner identification using search providers like
Perplexity and Tavily.

Architecture:
    - Uses FastMCP with Streamable HTTP transport for ARK compatibility
    - Wraps UBOWebAgent for web research and LLM extraction
    - Stores results and evidence in pluggable storage layer
    - Returns structured ownership tables compatible with PDF agent output

Environment Variables:
    FASTMCP_HOST: Host to bind to (default: 0.0.0.0)
    FASTMCP_PORT: Port to bind to (default: 8081)
    OPENAI_API_KEY: OpenAI API key for extraction LLM
    OPENAI_BASE_URL: Optional custom OpenAI base URL
    PERPLEXITY_API_KEY: Perplexity API key (for perplexity provider)
    TAVILY_API_KEY: Tavily API key (for tavily provider)
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import time
import traceback
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from ubo_infra.storage import get_storage
from ubo_infra.web_agent.ubo_web_agent import AgentConfig, UBOWebAgent

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fast mode: limit Perplexity responses for faster testing
# Set FAST_MODE=true or MAX_TOKENS_DEFAULT=1500 to enable
FAST_MODE = os.getenv("FAST_MODE", "false").lower() == "true"
MAX_TOKENS_DEFAULT = int(os.getenv("MAX_TOKENS_DEFAULT", "0")) or None
if FAST_MODE and not MAX_TOKENS_DEFAULT:
    MAX_TOKENS_DEFAULT = 1500  # ~1000 words, enough for key info
    logger.info(f"[WEB] FAST_MODE enabled: max_tokens={MAX_TOKENS_DEFAULT}")

# Initialize FastMCP server
mcp = FastMCP(
    "ubo-web-tools",
    host=os.getenv("FASTMCP_HOST", "0.0.0.0"),
    port=int(os.getenv("FASTMCP_PORT", "8081")),
)


def _generate_case_id(target_company: str, provider: str) -> str:
    """Generates a unique case ID for web research.

    Uses hash of target company + provider + timestamp for uniqueness.
    Each research session gets a new case_id (web content changes over time).

    Args:
        target_company: Company being researched.
        provider: Search provider used.

    Returns:
        12-character hex case ID.
    """
    timestamp = datetime.now(UTC).isoformat()
    content = f"{target_company}|{provider}|{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


@mcp.tool()
async def research_ubo_web(
    target_company: str,
    provider: Literal["perplexity", "tavily"] = "perplexity",
    perplexity_model: str = "sonar",
    extraction_model: str = "gpt-4o-mini",
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Research Ultimate Beneficial Owners using web search.

    Searches the web for ownership information about a target company,
    extracts structured ownership relations using LLM, and stores
    results for downstream processing.

    Args:
        target_company: Full legal name of the company to research.
            Example: "Heineken N.V.", "Apple Inc."
        provider: Search provider to use.
            - "perplexity": Uses Perplexity AI (recommended, better synthesis)
            - "tavily": Uses Tavily AI (good for specific domains)
        perplexity_model: Perplexity model variant.
            - "sonar": Fast, good for most queries (default)
            - "sonar-pro": More thorough, better for complex queries
        extraction_model: LLM model for extracting structured data.
            Default: "gpt-4o-mini" (fast and accurate)
        include_domains: Only search these domains (optional).
            Example: ["sec.gov", "bloomberg.com"]
        exclude_domains: Exclude these domains from search (optional).
        max_tokens: Maximum tokens in Perplexity response (optional).
            - None: No limit (default, comprehensive but slower)
            - 1000-2000: Fast mode for testing (less comprehensive)

    Returns:
        Dictionary containing:
            - case_id: Unique identifier for this research session
            - target_company: The company researched
            - ownership_table: List of ownership relations with evidence
            - ubos: List of identified UBO names
            - sources: List of source URLs used
            - summary: Quick stats about findings
            - storage_path: Where full results are stored
            - message: Human-readable summary

    Raises:
        ValueError: If target_company is empty.
        Exception: For research or extraction errors.

    Example:
        >>> result = await research_ubo_web(
        ...     target_company="Heineken N.V.",
        ...     provider="perplexity"
        ... )
        >>> print(f"Found {len(result['ubos'])} UBOs")
    """
    start_time = time.time()
    logger.info(f"[WEB] Starting research for '{target_company}' using {provider}")

    try:
        # Input validation
        if not target_company or not target_company.strip():
            raise ValueError("target_company must be a non-empty string")

        # Generate case ID
        case_id = _generate_case_id(target_company, provider)
        logger.info(f"[WEB] Case ID: {case_id}")

        # Configure and run agent
        # Use provided max_tokens, or fall back to env var default (for fast mode)
        effective_max_tokens = max_tokens if max_tokens is not None else MAX_TOKENS_DEFAULT
        if effective_max_tokens:
            logger.info(f"[WEB] Using max_tokens={effective_max_tokens}")
        
        config = AgentConfig(
            provider=provider,
            perplexity_model=perplexity_model,
            extraction_model=extraction_model,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            max_tokens=effective_max_tokens,
        )

        agent = UBOWebAgent(config)

        try:
            logger.info("[WEB] Running web research...")
            result = await agent.research(target_company)
        finally:
            await agent.close()

        logger.info(
            f"[WEB] Research complete: {len(result.relations)} relations, "
            f"{len(result.identified_ubos)} UBOs"
        )

        # Build ownership table (same structure as PDF agent)
        ownership_table = []
        for rel in result.relations:
            # Collect sources for this relation
            sources_for_rel = [
                {
                    "url": ev.url,
                    "title": ev.title,
                    "source_name": ev.source_name,
                    "accessed_at": ev.accessed_at.isoformat() if ev.accessed_at else None,
                }
                for ev in rel.evidence
            ]

            ownership_table.append({
                "owner": rel.owner_name,
                "owned": rel.owned_name,
                "ownership_pct": rel.ownership_pct,
                "voting_pct": rel.voting_pct,
                "type": rel.ownership_kind.value if rel.ownership_kind else "unknown",
                "share_class": rel.share_class,
                "sources": sources_for_rel,
                "snippet": (
                    rel.evidence[0].snippet[:200] + "..."
                    if rel.evidence and rel.evidence[0].snippet
                    and len(rel.evidence[0].snippet) > 200
                    else rel.evidence[0].snippet if rel.evidence else None
                ),
            })

        # Collect all unique sources
        all_sources = []
        seen_urls = set()
        for rel in result.relations:
            for ev in rel.evidence:
                if ev.url not in seen_urls:
                    seen_urls.add(ev.url)
                    all_sources.append({
                        "url": ev.url,
                        "title": ev.title,
                        "source_name": ev.source_name,
                        "accessed_at": ev.accessed_at.isoformat() if ev.accessed_at else None,
                    })

        # Build UBO details
        ubo_details = [
            {"name": name, "identified_as_ubo": True}
            for name in result.identified_ubos
        ]

        # Full results for storage
        duration = time.time() - start_time
        full_results = {
            "target_company": target_company,
            "ownership_table": ownership_table,
            "ubos": ubo_details,
            "identified_ubo_names": result.identified_ubos,
            "sources": all_sources,
            "raw_response": result.raw_response,
            "search_queries": result.search_queries,
            "notes": result.notes,
            "metadata": {
                "case_id": case_id,
                "provider": provider,
                "perplexity_model": perplexity_model if provider == "perplexity" else None,
                "extraction_model": extraction_model,
                "duration_seconds": round(duration, 2),
                "researched_at": datetime.now(UTC).isoformat(),
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
            },
        }

        # Store to storage layer
        storage = get_storage()
        storage_path = storage.store_json(case_id, "analysis.json", full_results)
        logger.info(f"[WEB] Stored analysis at: {storage_path}")

        # Store evidence separately for easy access
        evidence_data = {
            "case_id": case_id,
            "target_company": target_company,
            "sources": all_sources,
            "raw_response": result.raw_response,
            "researched_at": datetime.now(UTC).isoformat(),
        }
        storage.store_json(case_id, "evidence/sources.json", evidence_data)
        logger.info("[WEB] Stored evidence sources")

        # Return summary (not full raw response to save tokens)
        return {
            "case_id": case_id,
            "target_company": target_company,
            "ownership_table": ownership_table,
            "ubos": ubo_details,
            "sources": all_sources,
            "summary": {
                "total_relations": len(ownership_table),
                "ubo_count": len(result.identified_ubos),
                "source_count": len(all_sources),
            },
            "notes": result.notes,
            "duration_seconds": round(duration, 2),
            "storage_path": storage_path,
            "message": (
                f"Research complete for {target_company}. "
                f"Found {len(result.identified_ubos)} UBO(s), "
                f"{len(ownership_table)} ownership relation(s) "
                f"from {len(all_sources)} source(s). "
                f"Full results stored at case_id={case_id}."
            ),
        }

    except Exception as e:
        logger.error(f"[WEB] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[WEB] Traceback:\n{traceback.format_exc()}")
        raise Exception(
            f"Web research failed for '{target_company}': {type(e).__name__}: {e}"
        ) from e


@mcp.tool()
async def web_search(
    query: str,
    provider: Literal["perplexity", "tavily"] = "perplexity",
    max_results: int = 5,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> dict[str, Any]:
    """General web search for any query. Returns search results with URLs.

    Use this for general company research, news, industry information, etc.
    Each result includes a URL that can be cited as source_reference.

    Args:
        query: Search query (e.g., "Heineken employees headquarters industry").
        provider: Search provider - "perplexity" (recommended) or "tavily".
        max_results: Maximum number of results to return (default: 5).
        include_domains: Only search these domains (optional).
        exclude_domains: Exclude these domains (optional).

    Returns:
        Dictionary containing:
            - query: The search query
            - results: List of {url, title, snippet, source}
            - sources: List of URLs (for easy source_reference)
            - message: Human-readable summary

    Example:
        >>> result = await web_search(query="Heineken company employees industry")
        >>> for r in result["results"]:
        ...     print(f"Source: {r['url']}")
        ...     print(f"Content: {r['snippet']}")
    """
    start_time = time.time()
    logger.info(f"[WEB] web_search: query='{query}', provider={provider}")

    try:
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")

        # Initialize provider
        if provider == "perplexity":
            from ubo_infra.web_agent.providers.perplexity_provider import PerplexityProvider
            search_provider = PerplexityProvider(max_tokens=MAX_TOKENS_DEFAULT)
        else:
            from ubo_infra.web_agent.providers.tavily_provider import TavilyProvider
            search_provider = TavilyProvider()

        try:
            # For Perplexity, use research() to get synthesized answer
            if provider == "perplexity":
                research_result = await search_provider.research(
                    query,
                    include_domains=include_domains,
                )
                search_results = research_result.search_results[:max_results]
                synthesized_answer = research_result.answer
            else:
                # Tavily returns proper snippets via search()
                search_results = await search_provider.search(
                    query,
                    max_results=max_results,
                    include_domains=include_domains,
                    exclude_domains=exclude_domains,
                )
                synthesized_answer = None
        finally:
            await search_provider.close()

        duration = time.time() - start_time
        logger.info(f"[WEB] web_search complete: {len(search_results)} results in {duration:.2f}s")

        # Format results
        results = []
        sources = []
        for sr in search_results:
            results.append({
                "url": sr.url,
                "title": sr.title,
                "snippet": sr.snippet[:500] if sr.snippet else "",
                "source": sr.source,
                "score": sr.score if hasattr(sr, 'score') else None,
            })
            if sr.url:
                sources.append(sr.url)

        response = {
            "query": query,
            "provider": provider,
            "results": results,
            "sources": sources,
            "result_count": len(results),
            "duration_seconds": round(duration, 2),
            "message": f"Found {len(results)} result(s) for '{query}'. Use 'sources' list for source_reference.",
        }
        
        # Include synthesized answer from Perplexity (this contains the actual content!)
        if synthesized_answer:
            response["answer"] = synthesized_answer
            response["message"] = f"Found answer with {len(results)} source(s). Use 'answer' for content and 'sources' for source_reference."
        
        return response

    except Exception as e:
        logger.error(f"[WEB] web_search FAILED: {type(e).__name__}: {e}")
        logger.error(f"[WEB] Traceback:\n{traceback.format_exc()}")
        raise Exception(f"Web search failed for '{query}': {type(e).__name__}: {e}") from e


@mcp.tool()
async def get_web_research_results(case_id: str) -> dict[str, Any]:
    """Retrieve full web research results from storage.

    Use this to get complete research data including raw response
    and all evidence sources.

    Args:
        case_id: Case ID from research_ubo_web result.

    Returns:
        Full research results including:
            - ownership_table: List of ownership relations
            - ubos: List of identified UBOs
            - sources: All source URLs with metadata
            - raw_response: Original research response
            - metadata: Research configuration and timing

    Raises:
        FileNotFoundError: If case_id doesn't exist.

    Example:
        >>> results = await get_web_research_results(case_id="abc123def456")
        >>> print(f"Found {len(results['sources'])} sources")
    """
    try:
        if not case_id or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")

        logger.info(f"[WEB] Loading research results for case {case_id}")

        storage = get_storage()
        results = storage.load_json(case_id, "analysis.json")

        logger.info(
            f"[WEB] Loaded: {len(results.get('ownership_table', []))} relations, "
            f"{len(results.get('sources', []))} sources"
        )

        return results

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Case {case_id} not found. Run research_ubo_web first."
        ) from None
    except Exception as e:
        logger.error(f"[WEB] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[WEB] Traceback:\n{traceback.format_exc()}")
        raise


@mcp.tool()
async def list_web_evidence(case_id: str) -> dict[str, Any]:
    """List all evidence sources for a web research case.

    Args:
        case_id: Case ID from research_ubo_web result.

    Returns:
        Dictionary containing:
            - case_id: The case ID
            - sources: List of source URLs with metadata
            - raw_response_available: Whether raw response is stored
            - message: Human-readable summary

    Raises:
        FileNotFoundError: If case_id doesn't exist.

    Example:
        >>> evidence = await list_web_evidence(case_id="abc123def456")
        >>> for src in evidence["sources"]:
        ...     print(f"Source: {src['url']}")
    """
    try:
        if not case_id or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")

        logger.info(f"[WEB] Listing evidence for case {case_id}")

        storage = get_storage()

        try:
            evidence = storage.load_json(case_id, "evidence/sources.json")
        except FileNotFoundError:
            # Try loading from main analysis file
            analysis = storage.load_json(case_id, "analysis.json")
            evidence = {
                "sources": analysis.get("sources", []),
                "raw_response": analysis.get("raw_response"),
            }

        sources = evidence.get("sources", [])
        has_raw = bool(evidence.get("raw_response"))

        logger.info(f"[WEB] Found {len(sources)} sources")

        return {
            "case_id": case_id,
            "sources": sources,
            "source_count": len(sources),
            "raw_response_available": has_raw,
            "message": (
                f"Case {case_id}: {len(sources)} evidence source(s) available. "
                f"Raw response {'available' if has_raw else 'not available'}."
            ),
        }

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Case {case_id} not found. Run research_ubo_web first."
        ) from None
    except Exception as e:
        logger.error(f"[WEB] FAILED: {type(e).__name__}: {e}")
        logger.error(f"[WEB] Traceback:\n{traceback.format_exc()}")
        raise


# Fetch URL: used by source-verifier and any agent that needs to verify cited URLs
FETCH_URL_TIMEOUT = int(os.getenv("FETCH_URL_TIMEOUT_SECONDS", "15"))
FETCH_URL_MAX_CHARS = int(os.getenv("FETCH_URL_MAX_CHARS", "15000"))


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace for snippet."""
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@mcp.tool(name="fetch-url")
async def fetch_url(url: str, max_chars: int | None = None) -> str:
    """Fetch a URL and return a plain-text snippet of the response body.

    Use this to verify that a cited source exists and to extract content
    for attribution checks (e.g. does the source support the claim?).

    Args:
        url: Full URL (must be http or https).
        max_chars: Maximum characters to return (default from env, typically 15000).

    Returns:
        Plain-text snippet of the page body, or an error message if fetch failed.
    """
    if not url or not url.strip():
        return "Error: URL is empty."
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Error: URL scheme must be http or https, got: {parsed.scheme}"
    limit = max_chars if max_chars is not None else FETCH_URL_MAX_CHARS
    try:
        async with httpx.AsyncClient(
            timeout=FETCH_URL_TIMEOUT, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            body = response.text
            if not body:
                return f"OK (empty body). Status: {response.status_code}"
            text = _strip_html(body)
            if len(text) > limit:
                text = text[:limit] + "\n[... truncated ...]"
            return f"Status: {response.status_code}\n\nSnippet:\n{text}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} for {url}"
    except httpx.TimeoutException:
        return f"Error: Timeout after {FETCH_URL_TIMEOUT}s for {url}"
    except Exception as e:
        logger.exception("fetch_url failed for %s", url)
        return f"Error: {type(e).__name__} - {e}"


@mcp.resource("health://status")
def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Dictionary with status and service name.
    """
    return {"status": "healthy", "service": "ubo-web-tools"}


def main():
    """Run the MCP server over Streamable HTTP."""
    print("=" * 60)
    print("Starting UBO Web Tools MCP Server")
    print("=" * 60)

    # Check API keys
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    print(f"PERPLEXITY_API_KEY: {'Set' if perplexity_key else 'Not Set'}")
    print(f"TAVILY_API_KEY: {'Set' if tavily_key else 'Not Set'}")
    print(f"OPENAI_API_KEY: {'Set' if openai_key else 'Not Set'}")
    print(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', 'Not Set')}")
    print("=" * 60)

    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
