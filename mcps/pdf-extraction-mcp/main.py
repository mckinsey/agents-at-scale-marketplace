#!/usr/bin/env python3
"""
Lightweight PDF Extraction MCP Server
Replacement for ubo-pdf-tools with minimal dependencies
"""
import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

import fitz  # PyMuPDF
import httpx
from mcp.server.fastmcp import FastMCP

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


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from PDF file"""
    if pdf_path.startswith("http://") or pdf_path.startswith("https://"):
        # Download PDF from URL
        response = httpx.get(pdf_path, timeout=30.0)
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


def call_llm(prompt: str, model: str = None) -> str:
    """Call LLM API (OpenAI or Anthropic)"""
    model = model or LLM_MODEL
    
    if LLM_PROVIDER == "anthropic":
        return call_anthropic(prompt, model)
    else:
        return call_openai(prompt, model)


def call_openai(prompt: str, model: str) -> str:
    """Call OpenAI API"""
    url = f"{LLM_BASE_URL}/chat/completions" if LLM_BASE_URL else "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a financial document analyst extracting ownership information."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
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
    # Override provider if specified
    global LLM_PROVIDER, LLM_MODEL
    original_provider = LLM_PROVIDER
    original_model = LLM_MODEL
    
    if extraction_provider:
        LLM_PROVIDER = extraction_provider
    if extraction_model:
        LLM_MODEL = extraction_model
    
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_path)
        
        # Chunk text (simple approach - just take first 16k chars for now)
        text_sample = text[:16000]
        
        # Build extraction prompt
        prompt = f"""Analyze this document excerpt and extract ownership information for: {target_company}

Document content:
{text_sample}

Extract the following in JSON format:
1. ownership_table: Array of ownership relationships with:
   - owner: Owner name
   - owned: Entity owned
   - ownership_pct: Ownership percentage (number)
   - type: "direct" or "indirect"
   
2. extracted_entities: Array of all company/person names mentioned

3. summary: Brief summary of findings

Return ONLY valid JSON, no markdown formatting."""

        # Call LLM
        response = call_llm(prompt, extraction_model or LLM_MODEL)
        
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
    finally:
        # Restore original settings
        LLM_PROVIDER = original_provider
        LLM_MODEL = original_model


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
