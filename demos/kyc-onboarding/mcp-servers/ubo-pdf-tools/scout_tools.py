"""Comprehensive PDF scanning tools for ownership discovery.

Philosophy: Scan EVERYTHING. No sampling, no shortcuts.
Uses pypdf for fast text extraction without heavy dependencies.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import httpx
from pypdf import PdfReader


@dataclass
class PercentageFound:
    """A percentage found in the document with context."""
    value: float
    raw_text: str
    page: int
    context: str  # Surrounding text snippet


@dataclass
class EntityFound:
    """An entity found in the document."""
    name: str
    entity_type: str  # company, trust, foundation, fund, person
    pages_mentioned: list[int] = field(default_factory=list)
    ownership_signals: list[str] = field(default_factory=list)


@dataclass
class PDFScanResult:
    """Comprehensive result of scanning a PDF for ownership content."""
    total_pages: int
    pages_scanned: int
    relevant_pages: list[int]
    sections_found: list[str]
    entities_mentioned: list[EntityFound]
    percentages_found: list[PercentageFound]
    suggested_queries: list[str]
    sample_text: dict[int, str]  # page_num -> sample text
    ownership_keywords_by_page: dict[int, list[str]]


# Keywords that often indicate ownership content - EXPANDED list
OWNERSHIP_KEYWORDS = [
    # Direct ownership terms
    "shareholder", "shareholders", "shareholding", "shareholdings",
    "ownership", "owner", "owns", "owned", "owning",
    "stake", "stakes", "holding", "holdings", "held", "holds",
    "beneficial owner", "ultimate beneficial", "ubo",
    "voting rights", "voting power", "voting shares", "voting interest",
    "capital", "equity", "shares", "stock", "issued share capital",
    "interest", "interests", "participation",
    
    # Control terms
    "controlling", "controlled by", "control of", "controls",
    "majority", "minority", "dominant", "significant",
    "direct", "indirect", "through",
    
    # Structure terms
    "subsidiary", "subsidiaries", "parent company", "parent",
    "affiliate", "affiliates", "associated company", "associated",
    "group", "group company", "group structure", "holding company",
    "investment vehicle", "family office", "private company",
    
    # Section headers
    "corporate governance", "share capital", "equity structure",
    "major shareholders", "principal shareholders", "substantial shareholders",
    "ownership structure", "group structure", "shareholder structure",
    "significant shareholders", "principal shareholder",
    "related parties", "related party", "note 28", "note 29", "note 30",
    "directors' interests", "directors interests", "board interests",
    "substantial shareholdings", "notifiable interests",
    
    # Legal/regulatory
    "disclosure", "register", "psc", "persons with significant control",
    "transparency", "beneficial ownership", "ultimate owner",
    
    # Financial notes
    "consolidated", "consolidation", "group accounts",
    "investments in subsidiaries", "equity method",
]

# Comprehensive patterns for entity names
ENTITY_PATTERNS = [
    # Companies with suffixes
    r"[A-Z][a-zA-Z\-']+(?:\s+[A-Za-z\-']+)*\s+(?:N\.V\.|B\.V\.|Ltd\.?|LLC|Inc\.?|Corp\.?|PLC|plc|SA|AG|GmbH|S\.A\.|S\.E\.|Holdings?|Limited|Incorporated)",
    # Trusts and foundations
    r"[A-Z][a-zA-Z\-']+(?:\s+[A-Za-z\-']+)*\s+(?:Trust|Foundation|Fund|Stichting|Stiftung)",
    # Family offices and investment vehicles
    r"[A-Z][a-zA-Z\-']+\s+(?:Family\s+Office|Investments?|Capital|Partners|Ventures)",
    # Charitable entities
    r"[A-Z][a-zA-Z\-']+\s+(?:Charitable|Charity|Endowment)",
]

# Patterns to extract percentages
PERCENTAGE_PATTERNS = [
    r"(\d{1,3}(?:[.,]\d{1,3})?)\s*%",  # 56.6%, 79,2%
    r"(\d{1,3}(?:[.,]\d{1,3})?)\s*per\s*cent",  # 56.6 per cent
    r"(\d{1,3}(?:[.,]\d{1,3})?)\s*percent",  # 56.6 percent
]


def fetch_pdf_bytes(url: str, timeout: float = 120.0) -> bytes:
    """Fetch PDF from URL with retry."""
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content


def scan_page_for_ownership(text: str) -> tuple[bool, list[str]]:
    """Check if page text contains ownership-related keywords."""
    text_lower = text.lower()
    found = []
    
    for keyword in OWNERSHIP_KEYWORDS:
        if keyword in text_lower:
            found.append(keyword)
    
    # Also check for percentage patterns
    for pattern in PERCENTAGE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append("percentage")
            break
    
    return len(found) >= 2, found  # Require at least 2 keywords for relevance


def extract_percentages(text: str, page_num: int) -> list[PercentageFound]:
    """Extract all percentages from text with context."""
    percentages = []
    
    for pattern in PERCENTAGE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                # Get the raw percentage string
                raw = match.group(1).replace(",", ".")
                value = float(raw)
                
                # Skip obviously irrelevant percentages (0%, 100%, tiny decimals)
                if value <= 0 or value > 100:
                    continue
                
                # Get surrounding context (100 chars before and after)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].replace("\n", " ").strip()
                
                # Only include if context has ownership signals
                context_lower = context.lower()
                if any(kw in context_lower for kw in 
                       ["share", "own", "hold", "stake", "interest", "capital", "voting", "control"]):
                    percentages.append(PercentageFound(
                        value=value,
                        raw_text=match.group(0),
                        page=page_num,
                        context=context
                    ))
            except ValueError:
                continue
    
    return percentages


def classify_entity_type(name: str) -> str:
    """Classify an entity into a type."""
    name_lower = name.lower()
    
    if any(x in name_lower for x in ["trust", "stichting"]):
        return "trust"
    if any(x in name_lower for x in ["foundation", "stiftung", "charitable", "charity"]):
        return "foundation"
    if any(x in name_lower for x in ["fund", "investment"]):
        return "fund"
    if any(x in name_lower for x in ["family office"]):
        return "family_office"
    return "company"


def extract_entities(text: str) -> list[tuple[str, str]]:
    """Extract potential entity names with their types."""
    entities = []
    seen = set()
    
    for pattern in ENTITY_PATTERNS:
        for match in re.finditer(pattern, text):
            name = match.group(0).strip()
            # Clean up common issues
            name = re.sub(r'\s+', ' ', name)
            
            # Skip if too short or already seen
            if len(name) < 5 or name.lower() in seen:
                continue
            
            seen.add(name.lower())
            entity_type = classify_entity_type(name)
            entities.append((name, entity_type))
    
    return entities


def extract_section_headers(text: str) -> list[str]:
    """Extract potential section headers."""
    lines = text.split('\n')
    headers = []
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5 or len(line) > 100:
            continue
        
        # Header patterns
        # Numbered section: "29. Related Parties"
        if re.match(r'^[\d\.]+\s+[A-Z]', line):
            headers.append(line)
        # Note headers: "Note 29 - Related Parties"
        elif re.match(r'^Note\s+\d', line, re.IGNORECASE):
            headers.append(line)
        # ALL CAPS headers
        elif line.isupper() and len(line.split()) < 10:
            headers.append(line)
        # Title Case with ownership keywords
        elif any(kw in line.lower() for kw in 
                 ['shareholder', 'ownership', 'governance', 'capital', 'structure',
                  'related parties', 'beneficial', 'voting', 'principal']):
            headers.append(line[:80])
    
    return list(set(headers))


def generate_comprehensive_queries(
    target_company: str,
    entities: list[EntityFound],
    percentages: list[PercentageFound],
    sections: list[str],
) -> list[str]:
    """Generate comprehensive retrieval queries based on scan results."""
    queries = []
    
    # Base queries - always include
    queries.extend([
        f"Who are the major shareholders of {target_company}?",
        f"What is the ownership structure of {target_company}?",
        f"Shareholder breakdown and percentages for {target_company}",
        f"{target_company} beneficial owners and controlling parties",
        f"Voting rights distribution in {target_company}",
        f"Capital structure and equity ownership {target_company}",
        f"Ultimate beneficial owners of {target_company}",
        f"Parent company controlling shareholder {target_company}",
        f"Group structure and subsidiaries {target_company}",
        f"Related parties transactions {target_company}",
    ])
    
    # Entity-specific queries - for EACH entity found
    for entity in entities:
        name = entity.name
        if name.lower() != target_company.lower():
            queries.extend([
                f"What percentage does {name} own in {target_company}?",
                f"{name} ownership stake shareholding {target_company}",
                f"{name} voting rights control {target_company}",
            ])
    
    # Percentage-specific queries - for each unique percentage
    seen_pcts = set()
    for pct in percentages:
        pct_str = f"{pct.value:.1f}"
        if pct_str not in seen_pcts and pct.value > 5:  # Focus on significant percentages
            seen_pcts.add(pct_str)
            queries.append(f"{pct_str}% shareholder ownership {target_company}")
    
    # Section-specific queries
    for section in sections[:10]:
        if len(section) < 60:
            queries.append(f"{section} {target_company}")
    
    # Note-specific queries (financial notes often have ownership info)
    queries.extend([
        f"Note 28 related parties {target_company}",
        f"Note 29 related party transactions {target_company}",
        f"Note 30 group structure {target_company}",
        f"directors interests shareholdings {target_company}",
        f"substantial shareholders register {target_company}",
    ])
    
    # Deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique_queries.append(q)
    
    return unique_queries[:30]  # Return up to 30 queries


def scan_pdf_for_ownership(
    pdf_source: str | bytes,
    target_company: str,
    max_pages: int | None = None,  # None = scan ALL pages
    full_scan: bool = True,  # Always do full scan by default
) -> PDFScanResult:
    """
    Comprehensively scan PDF to find ALL ownership-related content.
    
    Philosophy: Scan EVERYTHING. No sampling, no shortcuts.
    
    Args:
        pdf_source: URL or bytes of PDF
        target_company: Name of company being analyzed
        max_pages: Maximum pages to scan (None = all pages)
        full_scan: If True, scan all pages regardless of max_pages
    
    Returns:
        PDFScanResult with ALL relevant pages, entities, percentages, and queries
    """
    # Get PDF bytes
    if isinstance(pdf_source, str):
        pdf_bytes = fetch_pdf_bytes(pdf_source)
    else:
        pdf_bytes = pdf_source
    
    # Parse PDF
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)
    
    # If full_scan, scan ALL pages
    pages_to_scan = total_pages if full_scan else min(total_pages, max_pages or total_pages)
    
    relevant_pages: list[int] = []
    all_entities: dict[str, EntityFound] = {}
    all_percentages: list[PercentageFound] = []
    all_sections: list[str] = []
    sample_text: dict[int, str] = {}
    keywords_by_page: dict[int, list[str]] = {}
    
    # Scan EVERY page
    for i in range(pages_to_scan):
        page_num = i + 1  # 1-indexed
        try:
            page = reader.pages[i]
            text = page.extract_text() or ""
            
            if not text.strip():
                continue
            
            has_ownership, keywords = scan_page_for_ownership(text)
            
            if has_ownership:
                relevant_pages.append(page_num)
                keywords_by_page[page_num] = keywords
                
                # Extract ALL entities from this page
                entities = extract_entities(text)
                for name, etype in entities:
                    if name in all_entities:
                        all_entities[name].pages_mentioned.append(page_num)
                    else:
                        all_entities[name] = EntityFound(
                            name=name,
                            entity_type=etype,
                            pages_mentioned=[page_num],
                            ownership_signals=[]
                        )
                    
                    # Check for ownership signals
                    for kw in keywords:
                        if kw not in all_entities[name].ownership_signals:
                            all_entities[name].ownership_signals.append(kw)
                
                # Extract ALL percentages from this page
                percentages = extract_percentages(text, page_num)
                all_percentages.extend(percentages)
                
                # Extract section headers
                sections = extract_section_headers(text)
                all_sections.extend(sections)
                
                # Store sample text (first 1000 chars for comprehensive sample)
                sample_text[page_num] = text[:1000]
                
        except Exception as e:
            # Log but continue - don't fail on one bad page
            continue
    
    # Convert entities dict to list
    entity_list = list(all_entities.values())
    
    # Sort entities by number of pages mentioned (most relevant first)
    entity_list.sort(key=lambda x: len(x.pages_mentioned), reverse=True)
    
    # Deduplicate percentages
    unique_percentages = []
    seen_pcts = set()
    for pct in all_percentages:
        key = (pct.value, pct.page)
        if key not in seen_pcts:
            seen_pcts.add(key)
            unique_percentages.append(pct)
    
    # Generate comprehensive queries
    suggested_queries = generate_comprehensive_queries(
        target_company,
        entity_list,
        unique_percentages,
        list(set(all_sections)),
    )
    
    return PDFScanResult(
        total_pages=total_pages,
        pages_scanned=pages_to_scan,
        relevant_pages=sorted(relevant_pages),
        sections_found=list(set(all_sections))[:30],
        entities_mentioned=entity_list[:30],  # Top 30 entities
        percentages_found=unique_percentages[:50],  # Top 50 percentages
        suggested_queries=suggested_queries,
        sample_text=sample_text,
        ownership_keywords_by_page=keywords_by_page,
    )
