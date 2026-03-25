# Companies House MCP Server

UK Companies House API integration for company search and beneficial ownership (PSC) data.

## Features

- **get_uk_company_number**: Search for a UK company by name, returns matching company numbers, status, and addresses
- **get_uk_person_in_control**: Get persons with significant control (PSC / beneficial owners) for a company

## Quick Start

```bash
# Build Docker image
docker build -t companies-house-mcp:latest .

# Deploy to Kubernetes
kubectl apply -f k8s-deployment.yaml

# Verify
kubectl get mcpserver companies-house
kubectl get pods -l app=companies-house-mcp
```

## Configuration

Set via Kubernetes Secret `companies-house-api-key`:
- `COMPANIES_HOUSE_API_KEY`: API key from [Companies House Developer Hub](https://developer.company-information.service.gov.uk/) (required)

Authentication uses HTTP Basic Auth with the API key as username (no password).

## Dependencies

- mcp[cli]>=1.1.0
- httpx>=0.27.0 (HTTP client)

Total: 2 dependencies, ~160 lines of code

## Tool Usage

```yaml
# In agent YAML
tools:
  - type: mcp
    name: companies-house-get-uk-company-number
  - type: mcp
    name: companies-house-get-uk-person-in-control
```

## Limitations

- Requires a valid Companies House API key (free registration)
- Rate limited by Companies House API (600 requests per 5 minutes)
- UK companies only
