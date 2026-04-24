#!/usr/bin/env python3
"""
Lightweight Web Research MCP Server
Replacement for ubo-web-tools with minimal dependencies
"""
import os
import json
from typing import Dict, List, Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP(
    "WebResearchServer",
    stateless_http=True,
    host="0.0.0.0"
)

# Configuration from environment
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "tavily")  # tavily or perplexity
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")


def search_tavily(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search using Tavily API"""
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced"
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def search_perplexity(query: str, max_results: int = 5) -> str:
    """Search using Perplexity API"""
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar",
        "messages": [
            {"role": "user", "content": query}
        ],
        "top_k": max_results
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


def extract_ownership_from_search_results(results: List[Dict], target_company: str) -> Dict[str, Any]:
    """Extract ownership information from search results"""
    # Simple extraction - combine all result snippets
    combined_text = "\n\n".join([
        f"Source: {r.get('title', 'Unknown')}\n{r.get('content', r.get('snippet', ''))}"
        for r in results
    ])
    
    # For now, return structured format with sources
    # In a real implementation, you'd parse with LLM
    return {
        "ownership_table": [],  # Would extract from results
        "sources": [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": r.get("content", r.get("snippet", ""))[:200]
            }
            for r in results
        ],
        "summary": f"Found {len(results)} sources for {target_company}. Review sources for ownership details.",
        "raw_results": combined_text[:2000]  # First 2000 chars
    }


@mcp.tool()
def research_ubo_web(
    target_company: str,
    search_provider: Optional[str] = None,
    max_results: int = 5
) -> Dict[str, Any]:
    """
    Research Ultimate Beneficial Owners via web search.
    
    Args:
        target_company: Name of the company to research
        search_provider: Search provider (tavily/perplexity, default: from env)
        max_results: Maximum number of results to return
    
    Returns:
        Dictionary with ownership_table, sources, and summary
    """
    provider = search_provider or SEARCH_PROVIDER
    
    try:
        # Build search query
        query = f"{target_company} beneficial owners ownership structure shareholders"
        
        # Execute search
        if provider == "perplexity":
            if not PERPLEXITY_API_KEY:
                raise ValueError("PERPLEXITY_API_KEY not configured")
            
            response_text = search_perplexity(query, max_results)
            
            # Return formatted result
            return {
                "ownership_table": [],
                "sources": [],
                "summary": response_text,
                "search_provider": "perplexity"
            }
        
        else:  # tavily (default)
            if not TAVILY_API_KEY:
                raise ValueError("TAVILY_API_KEY not configured")
            
            results = search_tavily(query, max_results)
            
            # Extract results
            search_results = results.get("results", [])
            extracted = extract_ownership_from_search_results(search_results, target_company)
            extracted["search_provider"] = "tavily"
            
            return extracted
    
    except Exception as e:
        return {
            "ownership_table": [],
            "sources": [],
            "summary": f"Error during web research: {str(e)}",
            "error": str(e)
        }


@mcp.tool()
def get_web_research_results(case_id: str) -> Dict[str, Any]:
    """
    Get previous web research results (stateless - always returns empty).
    This is a compatibility stub for workflows expecting this tool.
    """
    return {
        "case_id": case_id,
        "status": "not_found",
        "message": "This server is stateless. Use research_ubo_web directly.",
        "ownership_table": []
    }


@mcp.tool()
def list_web_evidence(case_id: str) -> Dict[str, Any]:
    """
    List web evidence sources (stateless - always returns empty).
    This is a compatibility stub for workflows expecting this tool.
    """
    return {
        "case_id": case_id,
        "sources": [],
        "message": "This server is stateless. Use research_ubo_web directly."
    }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="streamable-http")
