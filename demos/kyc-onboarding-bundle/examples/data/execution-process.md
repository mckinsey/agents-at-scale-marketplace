# EXECUTION PROCESS

## Phase 1: Input Processing

You will receive from the Scout Agent:
- `recommended_queries`: Apply all provided search queries
- `entities_found`: Candidate entities for investigation
- `percentages_found`: Numerical ownership indicators to validate
- `ownership_pages`: Document sections containing ownership data

## Phase 2: Document Query

Execute document analysis with provided parameters:
```
analyze_pdf_ownership(
  pdf_path="<url>",
  target_company="<company name>",
  custom_queries=<scout's recommended_queries>,
  extraction_model="gpt-4o"
)
```

## Phase 3: Results Compilation

Present ALL extracted relationships in a structured table:

| Owner | Owned | Capital % | Voting % | Type | Page | Evidence |
|-------|-------|-----------|----------|------|------|----------|
| ... | ... | ... | ... | ... | ... | ... |

Include:
- **Complete relationship catalog** regardless of ownership percentage
- **Source page references** for each data point
- **Supporting documentation quotes** from original text
- **Classification**: direct stake, indirect stake, aggregated
