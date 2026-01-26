# KYC Demo Data Files

This directory contains sample customer data files used by the KYC demo bundle.

## Structure

```
data/
├── customers/          Customer information files
│   ├── john-doe.txt    Sample customer data for John Michael Smith (plain text)
│   └── john-doe.json   Alternative JSON format (advanced users)
└── reports/            Generated compliance reports (created by agents)
```

## Customer Data Format

### Recommended: Plain Text (.txt)

Customer files use simple, human-readable text format. Anyone can create or edit these files in Notepad, TextEdit, or any text editor.

**Example (`john-doe.txt`):**

```
KYC CUSTOMER INFORMATION REQUEST

================================================================================
PERSONAL INFORMATION
================================================================================

Full Name: John Michael Smith
Date of Birth: March 15, 1985
Nationality: United States
Residential Address: 123 Main Street, New York, NY 10001, USA

Contact Information:
- Phone: +1-555-0123
- Email: john.smith@email.com

================================================================================
IDENTIFICATION DOCUMENTS
================================================================================

Primary Document:
- Type: US Passport
- Number: P123456789
- Issue Date: January 15, 2020
- Expiry Date: January 15, 2030

Secondary Document:
- Type: NY Driver's License
- Number: 123456789
- Issue Date: May 10, 2019

================================================================================
BUSINESS PROFILE
================================================================================

Account Purpose: Opening personal investment account

Expected Transaction Activity:
- Monthly deposits: $5,000 - $10,000

Source of Funds: Employment income (software engineer)

Employment Details:
- Occupation: Software Engineer
- Employer: Tech Solutions Inc.
- Annual Income: $120,000
```

### Alternative: JSON Format (.json)

For technical users who prefer structured data, JSON format is also supported. See `john-doe.json` for an example.

## Usage

Agents use filesystem MCP tools to:
- **Read** customer data from `customers/` directory
- **Write** compliance reports to `reports/` directory

The workflow instructs agents to read customer files and generate reports based on the data.

## Adding New Customers

### For Non-Technical Users

1. Copy `john-doe.txt` to a new file (e.g., `jane-smith.txt`)
2. Edit the file in any text editor
3. Update the customer information (name, documents, etc.)
4. Upload via Ark Dashboard Files section or `make upload-data`

### For Technical Users

Create new files in `customers/` directory in either .txt or .json format. Reference them in your Argo Workflow by updating the customer file path parameter.
