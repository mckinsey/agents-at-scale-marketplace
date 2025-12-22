# File Browser

Simple React-based file browser for the File API.  It may not work all the time...

## Quickstart

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Configuration

Set the API base URL via environment variable:

```bash
VITE_API_BASE_URL=http://localhost:8080 npm run dev
```

Default: `http://localhost:8080`

## Features

- List files with prefix filtering
- Pagination support (load more)
- File size and last modified display
- Clean, simple UI

## Build

```bash
npm run build
```

Output in `dist/`
