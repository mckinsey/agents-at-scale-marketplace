# Sample data for KYC Onboarding Bundle

## What to keep (input only)

Only **input** (and **rag**) data should be stored in the repo. These are read by the workflows:

| Path | Purpose |
|------|---------|
| `*/input/` | Prompts (`.yml`), customer/profile data (`.json`), mock-ups (`.txt`, `.json`), PDFs, etc. |
| `2-customer-due-diligence/rag/` | Reference data (e.g. `uk_sanctions_list.txt`) |

## What is created at runtime (do not commit)

The following folders are **written by the workflows** when they run. Do not copy them from another environment or commit them:

- **`*/output/`** — Reports, summaries, generated markdown/SVG
- **`*/intermediate/`** — Intermediate JSON and step outputs (except see below)
- **`*/profile_sections/`** — Consolidated profile sections (e.g. `key_controllers.json`, `adverse_media_screening.json`)
- **`*/tmp/`** — Temporary files (e.g. `screening_list.yaml`)
- **`2-customer-due-diligence/screening/`** — Screening results (blacklist/sanction JSON)

**Pre-created folders (like COBOL demo output):**
- `1-customer-profile-initialization/intermediate/` contains a `.keep` placeholder so the folder exists in the file gateway after `make upload-data`. The profile-initialization workflow then writes `inquiry_information.json` there.
- `1-customer-profile-initialization/output/` contains a `.keep` placeholder so the folder exists before **lx-initial-risk-assessment** runs. That workflow writes `kyc_profile.json`, `kyc_profile.md`, and `summary_risk_report.md` there. Only `.keep` is committed; other files under `intermediate/` and `output/` are generated at runtime.

If you copied a full tree from LegacyX or another run, delete those folders and keep only the **input** (and **rag**) contents.
