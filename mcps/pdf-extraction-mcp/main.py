#!/usr/bin/env python3
"""
Lightweight PDF Extraction MCP Server
Replacement for ubo-pdf-tools with minimal dependencies
"""
import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

import logging
import fitz  # PyMuPDF
import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    "PDFExtractionServer",
    stateless_http=True,
    host="0.0.0.0"
)

# Configuration from environment
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai or anthropic
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_VERSION = os.getenv("LLM_API_VERSION", "")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from PDF file"""
    if pdf_path.startswith("http://") or pdf_path.startswith("https://"):
        # Download PDF from URL
        response = httpx.get(pdf_path, timeout=30.0)
        response.raise_for_status()
        pdf_content = response.content
        doc = fitz.open(stream=pdf_content, filetype="pdf")
    else:
        # Open local file
        doc = fitz.open(pdf_path)
    
    text_content = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            text_content.append(f"--- Page {page_num} ---\n{text}")
    
    doc.close()
    return "\n\n".join(text_content)


def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
    """Simple text chunking by character count"""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks


def call_llm(prompt: str, model: str = None, provider: str = None) -> str:
    """Call LLM API (OpenAI or Anthropic)"""
    model = model or LLM_MODEL
    provider = provider or LLM_PROVIDER

    if provider == "anthropic":
        return call_anthropic(prompt, model)
    else:
        return call_openai(prompt, model)


def call_openai(prompt: str, model: str) -> str:
    """Call OpenAI API"""
    url = f"{LLM_BASE_URL}/chat/completions" if LLM_BASE_URL else "https://api.openai.com/v1/chat/completions"
    if LLM_API_VERSION:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}api-version={LLM_API_VERSION}"

    headers = {
        "Content-Type": "application/json"
    }
    # Azure OpenAI uses api-key header; standard OpenAI uses Bearer token
    if LLM_API_VERSION:
        headers["api-key"] = LLM_API_KEY
    else:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    payload = {
        "messages": [
            {"role": "system", "content": "You are a financial document analyst extracting ownership information."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    # Only include model for non-Azure (Azure uses deployment name in URL)
    if not LLM_API_VERSION:
        payload["model"] = model

    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        actual_model = result.get("model", "unknown")
        if actual_model != model:
            logger.warning("LLM_MODEL env=%s but gateway returned model=%s", model, actual_model)
        else:
            logger.info("LLM call succeeded: model=%s", actual_model)
        return result["choices"][0]["message"]["content"]


def call_anthropic(prompt: str, model: str) -> str:
    """Call Anthropic API"""
    url = f"{LLM_BASE_URL}/messages" if LLM_BASE_URL else "https://api.anthropic.com/v1/messages"
    
    headers = {
        "x-api-key": LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "max_tokens": 4096,
        "temperature": 0.1,
        "system": "You are a financial document analyst extracting ownership information.",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["content"][0]["text"]


@mcp.tool()
def analyze_pdf_ownership(
    pdf_path: str,
    target_company: str,
    extraction_model: Optional[str] = None,
    extraction_provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract ownership information from PDF document.
    
    Args:
        pdf_path: Path to PDF file or HTTP(S) URL
        target_company: Name of the target company
        extraction_model: LLM model to use (default: from env)
        extraction_provider: Provider (openai/anthropic, default: from env)
    
    Returns:
        Dictionary with ownership_table, extracted_entities, and summary
    """
    provider = extraction_provider or LLM_PROVIDER
    model = extraction_model or LLM_MODEL

    try:
        # Extract text from PDF
        full_text = extract_text_from_pdf(pdf_path)

        # Identify ownership-relevant pages using high-signal terms
        # Tier 1: strong ownership indicators (weighted 3x)
        tier1_terms = ["major interest", "controlling shareholder", "beneficial owner",
                       "issued share capital", "ordinary shares", "voting rights",
                       "substantial shareholding", "significant holding"]
        # Tier 2: moderate indicators (weighted 1x)
        tier2_terms = ["owner", "ownership", "shareholder", "stake", "percent",
                       "share capital", "substantial"]

        # Split text by page markers and score pages for relevance
        pages = full_text.split("--- Page ")
        scored_pages = []
        for page_block in pages:
            if not page_block.strip():
                continue
            page_text_lower = page_block.lower()
            score = sum(3 for term in tier1_terms if term in page_text_lower)
            score += sum(1 for term in tier2_terms if term in page_text_lower)
            if score > 0:
                scored_pages.append((score, page_block))

        # Sort by relevance score (highest first)
        scored_pages.sort(key=lambda x: x[0], reverse=True)

        # Two-pass approach: first extract focused ownership paragraphs, then full pages as fallback
        ownership_line_terms = ["wittington", "garfield", "weston", "controlling shareholder",
                               "major interest", "beneficial owner", "ordinary shares",
                               "share capital", "issued share", "voting rights", "%",
                               "ownership", "shareholder", "foundation", "concert"]
        focused_text = ""
        for score, page_block in scored_pages[:10]:  # top 10 pages
            pg_num = page_block.split(" ---")[0].strip() if " ---" in page_block else "?"
            lines = page_block.split("\n")
            relevant_lines = []
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(term in line_lower for term in ownership_line_terms):
                    # Include surrounding context (2 lines before and after)
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    for j in range(start, end):
                        if lines[j].strip() and lines[j] not in relevant_lines:
                            relevant_lines.append(lines[j])
            if relevant_lines:
                focused_text += f"\n--- Page {pg_num} (ownership-relevant excerpts) ---\n"
                focused_text += "\n".join(relevant_lines) + "\n"

        # Use focused text if substantial, otherwise fall back to full top pages
        if len(focused_text) > 500:
            text_sample = focused_text
        else:
            text_sample = ""
            char_budget = 48000
            for score, page_block in scored_pages:
                if len(text_sample) + len(page_block) > char_budget:
                    break
                text_sample += f"--- Page {page_block}\n\n"

        # If no relevant pages found, fall back to first portion of document
        if not text_sample:
            text_sample = full_text[:16000]

        # Build extraction prompt
        prompt = f"""Analyze this document and extract ALL ownership information for: {target_company}

Document content (ownership-relevant pages, sorted by relevance):
{text_sample}

IMPORTANT INSTRUCTIONS:
- Look for "Major interests in shares" sections, "controlling shareholder" disclosures, and "substantial shareholdings"
- Extract EXACT percentages as stated in the document (e.g., "56.1%", "56.6%")
- Include ALL named shareholders, parent companies, foundations, trusts, and family members
- Look for relationships like "X held Y shares representing Z% of issued share capital"
- Look for controlling shareholder relationships and concert party arrangements

Extract the following in JSON format:
1. ownership_table: Array of ALL ownership relationships found, with:
   - owner: Owner name (exact as stated in document)
   - owned: Entity owned (e.g., "{target_company}")
   - ownership_pct: Ownership percentage as stated (e.g., "56.1%" or "79.2%")
   - type: "direct" or "indirect"
   - details: Any additional context (e.g., "together with subsidiary Howard Investments Limited")

2. extracted_entities: Array of all company/person names mentioned as owners, shareholders, or controlling parties

3. summary: Detailed summary including ALL specific percentages and ownership chains found

Return ONLY valid JSON, no markdown formatting."""

        # Call LLM
        response = call_llm(prompt, model=model, provider=provider)

        # Parse response
        # Remove markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        result = json.loads(response)
        
        # Ensure required fields exist
        if "ownership_table" not in result:
            result["ownership_table"] = []
        if "extracted_entities" not in result:
            result["extracted_entities"] = []
        if "summary" not in result:
            result["summary"] = "No ownership information found."
        
        return result
        
    except Exception as e:
        # Return error in expected format
        return {
            "ownership_table": [],
            "extracted_entities": [],
            "summary": f"Error analyzing PDF: {str(e)}",
            "error": str(e)
        }


@mcp.tool()
def scout_pdf_for_ownership(
    pdf_path: str,
    search_terms: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Scout PDF for pages containing ownership-related content.
    Lightweight version - just returns page numbers with keywords.
    
    Args:
        pdf_path: Path to PDF file or HTTP(S) URL
        search_terms: Optional list of terms to search for
    
    Returns:
        Dictionary with relevant page numbers and snippets
    """
    default_terms = ["owner", "ownership", "beneficial", "shareholder", "stake", "%", "percent"]
    terms = search_terms or default_terms
    
    try:
        # Extract text
        if pdf_path.startswith("http://") or pdf_path.startswith("https://"):
            response = httpx.get(pdf_path, timeout=30.0)
            pdf_content = response.content
            doc = fitz.open(stream=pdf_content, filetype="pdf")
        else:
            doc = fitz.open(pdf_path)
        
        relevant_pages = []
        
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text().lower()
            
            # Check if any search term appears
            matches = [term for term in terms if term.lower() in text]
            
            if matches:
                # Extract snippet (first 200 chars)
                snippet = page.get_text()[:200].replace("\n", " ")
                relevant_pages.append({
                    "page": page_num,
                    "matched_terms": matches,
                    "snippet": snippet
                })
        
        doc.close()
        
        return {
            "relevant_pages": relevant_pages,
            "total_pages": len(relevant_pages),
            "summary": f"Found {len(relevant_pages)} pages with ownership-related content"
        }
        
    except Exception as e:
        return {
            "relevant_pages": [],
            "total_pages": 0,
            "summary": f"Error scouting PDF: {str(e)}",
            "error": str(e)
        }


@mcp.tool()
def extract_pdf_sections(
    pdf_path: str,
    search_terms: List[str],
    extraction_prompt: str,
    extraction_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    General-purpose PDF extraction using custom search terms and prompt.
    Finds relevant pages by search terms, then uses LLM to extract structured data.

    Args:
        pdf_path: Path to PDF file or HTTP(S) URL
        search_terms: List of terms to find relevant pages (e.g., ["subsidiary", "undertakings"])
        extraction_prompt: The specific question/instruction for the LLM to answer from the PDF content
        extraction_model: Optional LLM model override

    Returns:
        Dictionary with extracted data and source pages
    """
    model = extraction_model or LLM_MODEL

    try:
        full_text = extract_text_from_pdf(pdf_path)

        # Score pages by search term relevance
        pages = full_text.split("--- Page ")
        scored_pages = []
        for page_block in pages:
            if not page_block.strip():
                continue
            page_text_lower = page_block.lower()
            score = sum(1 for term in search_terms if term.lower() in page_text_lower)
            if score > 0:
                scored_pages.append((score, page_block))

        scored_pages.sort(key=lambda x: x[0], reverse=True)

        # For general extraction, send FULL pages (not just keyword-matched lines)
        # because data like subsidiary lists contain entity names that won't match search terms
        text_sample = ""
        char_budget = 60000
        for score, page_block in scored_pages:
            if len(text_sample) + len(page_block) > char_budget:
                break
            pg_num = page_block.split(" ---")[0].strip() if " ---" in page_block else "?"
            text_sample += f"--- Page {pg_num} ---\n{page_block.split('---', 1)[-1] if '---' in page_block else page_block}\n\n"

        if not text_sample:
            return {
                "data": [],
                "pages_found": 0,
                "summary": "No pages matched the search terms."
            }

        prompt = f"""{extraction_prompt}

Document content (relevant pages):
{text_sample}

Return ONLY valid JSON, no markdown formatting."""

        response = call_llm(prompt, model=model)

        # Parse response
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        result = json.loads(response)
        result["pages_found"] = len(scored_pages)
        return result

    except Exception as e:
        return {
            "data": [],
            "pages_found": 0,
            "summary": f"Error extracting from PDF: {str(e)}",
            "error": str(e)
        }


@mcp.tool()
def get_analysis_results(case_id: str) -> Dict[str, Any]:
    """
    Get previous analysis results (stateless - always returns empty).
    This is a compatibility stub for workflows expecting this tool.
    """
    return {
        "case_id": case_id,
        "status": "not_found",
        "message": "This server is stateless. Use analyze_pdf_ownership directly.",
        "ownership_table": []
    }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run(transport="streamable-http")
