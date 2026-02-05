# Sample Data

This directory contains sample COBOL files from the CardDemo application for testing the modernization pipeline.

## COBOL Source Files

| File | Lines | Description |
|------|-------|-------------|
| CBACT01C.cbl | ~500 | Account inquiry and display |
| CBACT02C.cbl | ~450 | Account update processing |
| CBACT03C.cbl | ~450 | Account add processing |
| CBACT04C.cbl | ~1700 | Account statement processing |
| CBCUS01C.cbl | ~230 | Customer data processing |
| CBSTM03A.cbl | ~1200 | Statement generation main |
| CBSTM03B.cbl | ~240 | Statement generation helper |
| CBTRN01C.cbl | ~580 | Transaction list display |
| CBTRN02C.cbl | ~1900 | Transaction add processing |
| CBTRN03C.cbl | ~1700 | Transaction update processing |

## Audio File

| File | Duration | Description |
|------|----------|-------------|
| carddemo-interview.m4a | ~15 min | SME interview about CardDemo modernization |

## Usage

These files are automatically uploaded to the file-gateway when you run:

```bash
make upload-data
```

After upload, they are available at:
- COBOL files: `cobol-source/*.cbl`
- Audio file: `cobol-source/carddemo-interview.m4a`
