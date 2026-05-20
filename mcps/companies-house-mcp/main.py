#!/usr/bin/env python3
"""
Companies House MCP Server
Provides UK Companies House API tools for KYC workflows.
"""
import os
import json
import base64
from typing import Dict, List, Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "CompaniesHouseServer",
    stateless_http=True,
    host="0.0.0.0"
)

API_BASE_URL = "https://api.company-information.service.gov.uk"
API_KEY = os.getenv("COMPANIES_HOUSE_API_KEY", "")


def _make_request(endpoint: str) -> Dict[str, Any]:
    """Make authenticated request to Companies House API."""
    # Companies House uses HTTP Basic Auth with API key as username, no password
    credentials = base64.b64encode(f"{API_KEY}:".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json"
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{API_BASE_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()


@mcp.tool()
def get_uk_company_number(
    company_name: str,
    items_per_page: Optional[int] = 5
) -> Dict[str, Any]:
    """
    Search for a UK company by name and return matching company numbers.

    Args:
        company_name: Name of the company to search for
        items_per_page: Number of results to return (default: 5)

    Returns:
        Dictionary with matching companies including company numbers
    """
    try:
        result = _make_request(
            f"/search/companies?q={company_name}&items_per_page={items_per_page}"
        )

        companies = []
        for item in result.get("items", []):
            companies.append({
                "company_name": item.get("title", ""),
                "company_number": item.get("company_number", ""),
                "company_status": item.get("company_status", ""),
                "company_type": item.get("company_type", ""),
                "date_of_creation": item.get("date_of_creation", ""),
                "registered_office_address": item.get("registered_office_address", {})
            })

        return {
            "query": company_name,
            "total_results": result.get("total_results", 0),
            "companies": companies
        }

    except httpx.HTTPStatusError as e:
        return {
            "query": company_name,
            "total_results": 0,
            "companies": [],
            "error": f"API error: {e.response.status_code} - {e.response.text[:200]}"
        }
    except Exception as e:
        return {
            "query": company_name,
            "total_results": 0,
            "companies": [],
            "error": str(e)
        }


@mcp.tool()
def get_uk_person_in_control(
    company_number: str
) -> Dict[str, Any]:
    """
    Get persons with significant control (PSC / beneficial owners) for a UK company.

    Args:
        company_number: The Companies House company number (e.g., "00293262")

    Returns:
        Dictionary with PSC data including names, nationalities, and natures of control
    """
    try:
        result = _make_request(
            f"/company/{company_number}/persons-with-significant-control"
        )

        persons = []
        for item in result.get("items", []):
            person = {
                "name": item.get("name", item.get("name_elements", {}).get("surname", "Unknown")),
                "kind": item.get("kind", ""),
                "natures_of_control": item.get("natures_of_control", []),
                "nationality": item.get("nationality", ""),
                "country_of_residence": item.get("country_of_residence", ""),
                "notified_on": item.get("notified_on", ""),
            }

            # Include name elements if available
            name_elements = item.get("name_elements", {})
            if name_elements:
                person["name_elements"] = {
                    "title": name_elements.get("title", ""),
                    "forename": name_elements.get("forename", ""),
                    "surname": name_elements.get("surname", ""),
                }

            # Include address if available
            address = item.get("address", {})
            if address:
                person["address"] = {
                    "locality": address.get("locality", ""),
                    "region": address.get("region", ""),
                    "country": address.get("country", ""),
                    "postal_code": address.get("postal_code", ""),
                }

            persons.append(person)

        return {
            "company_number": company_number,
            "total_results": result.get("total_results", len(persons)),
            "persons_with_significant_control": persons
        }

    except httpx.HTTPStatusError as e:
        return {
            "company_number": company_number,
            "total_results": 0,
            "persons_with_significant_control": [],
            "error": f"API error: {e.response.status_code} - {e.response.text[:200]}"
        }
    except Exception as e:
        return {
            "company_number": company_number,
            "total_results": 0,
            "persons_with_significant_control": [],
            "error": str(e)
        }


@mcp.tool()
def get_uk_company_info(
    company_number: str,
    subpage: Optional[str] = ""
) -> Dict[str, Any]:
    """
    Get UK company information from Companies House.

    Args:
        company_number: The Companies House company number (e.g., "00293262")
        subpage: Optional subpage for specific data. Common values:
            "" (empty) — general company profile
            "officers" — directors and secretaries
            "filing-history" — recent filings
            "registers" — statutory registers
            "charges" — secured debts

    Returns:
        Dictionary with company data for the requested subpage
    """
    if not company_number:
        return {"error": "company_number is required"}

    endpoint = f"/company/{company_number}"
    if subpage:
        endpoint = f"{endpoint}/{subpage.strip('/')}"

    try:
        result = _make_request(endpoint)
        return {
            "company_number": company_number,
            "subpage": subpage or "profile",
            "data": result,
        }
    except httpx.HTTPStatusError as e:
        return {
            "company_number": company_number,
            "subpage": subpage or "profile",
            "data": {},
            "error": f"API error: {e.response.status_code} - {e.response.text[:200]}",
        }
    except Exception as e:
        return {
            "company_number": company_number,
            "subpage": subpage or "profile",
            "data": {},
            "error": str(e),
        }


@mcp.tool()
def get_uk_financial_data(
    company_number: str,
    financial_year: Optional[str] = None,
    items_per_page: Optional[int] = 10
) -> Dict[str, Any]:
    """
    Get UK company financial filings metadata from Companies House.

    Returns the filing-history accounts entries. Optionally filters by
    financial year. Does NOT download PDFs — returns metadata with
    document_metadata links the caller can fetch separately.

    Args:
        company_number: The Companies House company number (e.g., "00293262")
        financial_year: Optional year filter (e.g., "2024"). When set, only
            filings whose date contains this year are returned.
        items_per_page: Max filings to return (default: 10)

    Returns:
        Dictionary with filings list (date, description, type, links)
    """
    if not company_number:
        return {"error": "company_number is required"}

    endpoint = (
        f"/company/{company_number}/filing-history"
        f"?category=accounts&items_per_page={items_per_page}"
    )

    try:
        result = _make_request(endpoint)
        items = result.get("items", [])

        if financial_year:
            items = [i for i in items if financial_year in str(i.get("date", ""))]

        filings = [
            {
                "date": item.get("date", ""),
                "description": item.get("description", ""),
                "type": item.get("type", ""),
                "action_date": item.get("action_date", ""),
                "document_metadata": item.get("links", {}).get("document_metadata", ""),
            }
            for item in items
        ]

        return {
            "company_number": company_number,
            "financial_year": financial_year,
            "total_results": len(filings),
            "filings": filings,
        }
    except httpx.HTTPStatusError as e:
        return {
            "company_number": company_number,
            "financial_year": financial_year,
            "total_results": 0,
            "filings": [],
            "error": f"API error: {e.response.status_code} - {e.response.text[:200]}",
        }
    except Exception as e:
        return {
            "company_number": company_number,
            "financial_year": financial_year,
            "total_results": 0,
            "filings": [],
            "error": str(e),
        }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
