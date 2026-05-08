"""Provider-agnostic Files API.

Exposes /v1/files endpoints that delegate to the configured file provider
(OpenAI, Anthropic, etc.). The provider is selected via FILE_PROVIDER env var.
"""

import logging
import os

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from .config import config
from .providers import FileProvider, create_provider

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt", ".md", ".json", ".html", ".xml", ".css", ".js", ".ts", ".tsx", ".jsx",
    ".py", ".rb", ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".zsh", ".ps1", ".bat", ".r", ".m", ".sql",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".log", ".csv",
    ".doc", ".docx", ".rtf", ".odt",
    ".ppt", ".pptx",
    ".xls", ".xlsx", ".tsv",
}

_provider: FileProvider | None = None


def _get_provider() -> FileProvider:
    global _provider
    if _provider is None:
        if not config.openai_api_key:
            raise ValueError("No API key configured. Set OPENAI_API_KEY env var.")
        _provider = create_provider(
            provider=config.file_provider,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url or None,
        )
    return _provider


async def upload_file(request: Request) -> JSONResponse:
    form = await request.form()
    upload = form.get("file")
    purpose = form.get("purpose", "user_data")

    if not upload:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    filename = getattr(upload, "filename", "upload")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            {"error": f"File type '{ext}' is not supported. Accepted: PDF, text/code, documents, presentations, spreadsheets."},
            status_code=400,
        )

    content = await upload.read()
    provider = _get_provider()
    result = await provider.upload(filename, content, purpose)
    return JSONResponse(result.to_dict(), status_code=201)


async def list_files(request: Request) -> JSONResponse:
    purpose = request.query_params.get("purpose")
    provider = _get_provider()
    files = await provider.list_files(purpose=purpose)
    return JSONResponse({"data": [f.to_dict() for f in files], "object": "list"})


async def get_file(request: Request) -> JSONResponse:
    file_id = request.path_params["file_id"]
    provider = _get_provider()
    result = await provider.get(file_id)
    return JSONResponse(result.to_dict())


async def delete_file(request: Request) -> JSONResponse:
    file_id = request.path_params["file_id"]
    provider = _get_provider()
    result = await provider.delete(file_id)
    return JSONResponse(result.to_dict())


async def file_ui(request: Request) -> HTMLResponse:
    return HTMLResponse(UI_HTML)


UI_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ark File Manager</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f1117; color: #e0e0e0; padding: 2rem; }
  h1 { font-size: 1.4rem; margin-bottom: 1.5rem; color: #fff; }
  .card { background: #1a1d27; border: 1px solid #2a2d37; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }
  .card h2 { font-size: 1rem; margin-bottom: 1rem; color: #aaa; text-transform: uppercase; letter-spacing: 0.05em; }
  .drop-zone { border: 2px dashed #3a3d47; border-radius: 8px; padding: 2rem; text-align: center; cursor: pointer; transition: border-color 0.2s; }
  .drop-zone:hover, .drop-zone.dragover { border-color: #6366f1; }
  .drop-zone input { display: none; }
  button { background: #6366f1; color: #fff; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
  button:hover { background: #5558e6; }
  button.danger { background: #dc2626; }
  button.danger:hover { background: #b91c1c; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { text-align: left; padding: 0.5rem; border-bottom: 1px solid #2a2d37; color: #888; font-weight: 500; }
  td { padding: 0.5rem; border-bottom: 1px solid #1f2230; }
  .id { font-family: monospace; font-size: 0.8rem; color: #6366f1; }
  .status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
  .status.processed { background: #064e3b; color: #6ee7b7; }
  .status.pending { background: #78350f; color: #fbbf24; }
  .empty { text-align: center; padding: 2rem; color: #555; }
  .toast { position: fixed; bottom: 1rem; right: 1rem; background: #1e40af; color: #fff; padding: 0.75rem 1.25rem; border-radius: 6px; font-size: 0.85rem; display: none; z-index: 100; }
  .toast.error { background: #991b1b; }
  .provider-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; background: #1e293b; color: #94a3b8; margin-left: 0.5rem; }
</style>
</head>
<body>
<h1>Ark File Manager <span class="provider-badge" id="providerBadge"></span></h1>

<div class="card">
  <h2>Upload</h2>
  <div class="drop-zone" id="dropZone">
    <p>Drop files here or click to browse</p>
    <input type="file" id="fileInput" multiple>
  </div>
</div>

<div class="card">
  <h2>Files</h2>
  <div id="fileList"><div class="empty">Loading...</div></div>
</div>

<div class="toast" id="toast"></div>

<script>
const API = '/v1/files';
const drop = document.getElementById('dropZone');
const input = document.getElementById('fileInput');
const toast = document.getElementById('toast');

function showToast(msg, isError) {
  toast.textContent = msg;
  toast.className = 'toast' + (isError ? ' error' : '');
  toast.style.display = 'block';
  setTimeout(() => toast.style.display = 'none', 3000);
}

drop.addEventListener('click', () => input.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
drop.addEventListener('drop', e => {
  e.preventDefault();
  drop.classList.remove('dragover');
  uploadFiles(e.dataTransfer.files);
});
input.addEventListener('change', () => { uploadFiles(input.files); input.value = ''; });

async function uploadFiles(files) {
  for (const file of files) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('purpose', 'user_data');
    try {
      const res = await fetch(API, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) { showToast(data.error || 'Upload failed', true); continue; }
      showToast(`Uploaded: ${data.filename} → ${data.id}`, false);
    } catch (e) { showToast('Upload error: ' + e.message, true); }
  }
  loadFiles();
}

async function deleteFile(id) {
  if (!confirm('Delete ' + id + '?')) return;
  try {
    await fetch(API + '/' + id, { method: 'DELETE' });
    showToast('Deleted ' + id, false);
    loadFiles();
  } catch (e) { showToast('Delete error: ' + e.message, true); }
}

function formatBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB';
  return (b / 1048576).toFixed(1) + ' MB';
}

function formatDate(ts) {
  return new Date(ts * 1000).toLocaleString();
}

async function loadFiles() {
  const el = document.getElementById('fileList');
  try {
    const res = await fetch(API);
    const data = await res.json();
    if (!data.data || data.data.length === 0) {
      el.innerHTML = '<div class="empty">No files uploaded</div>';
      if (data.data && data.data.length === 0) {
        document.getElementById('providerBadge').textContent = '';
      }
      return;
    }
    const provider = data.data[0].provider || 'unknown';
    document.getElementById('providerBadge').textContent = provider;
    el.innerHTML = '<table><thead><tr><th>ID</th><th>Filename</th><th>Size</th><th>Created</th><th>Status</th><th></th></tr></thead><tbody>' +
      data.data.map(f => `<tr>
        <td class="id">${f.id}</td>
        <td>${f.filename}</td>
        <td>${formatBytes(f.bytes)}</td>
        <td>${formatDate(f.created_at)}</td>
        <td><span class="status ${f.status}">${f.status}</span></td>
        <td><button class="danger" onclick="deleteFile('${f.id}')">Delete</button></td>
      </tr>`).join('') + '</tbody></table>';
  } catch (e) {
    el.innerHTML = '<div class="empty">Error loading files</div>';
  }
}

loadFiles();
</script>
</body>
</html>
"""


file_api_routes = [
    Route("/files", file_ui, methods=["GET"]),
    Route("/v1/files", upload_file, methods=["POST"]),
    Route("/v1/files", list_files, methods=["GET"]),
    Route("/v1/files/{file_id}", get_file, methods=["GET"]),
    Route("/v1/files/{file_id}", delete_file, methods=["DELETE"]),
]
