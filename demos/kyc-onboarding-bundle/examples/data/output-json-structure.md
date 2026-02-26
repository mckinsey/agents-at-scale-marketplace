# Output JSON Structure

Also output structured data for the UBO Designer:

```json
{
  "case_id": "<from analysis>",
  "target_company": "<name>",
  "ownership_table": [
    {
      "owner_name": "...",
      "owned_name": "...",
      "capital_pct": 56.6,
      "voting_pct": null,
      "relationship_type": "direct",
      "evidence": {
        "page": 99,
        "snippet": "..."
      }
    }
  ],
  "entities": [
    {"name": "...", "type": "company|person|trust|foundation"}
  ],
  "notes": ["Any uncertainties or observations"]
}
```
