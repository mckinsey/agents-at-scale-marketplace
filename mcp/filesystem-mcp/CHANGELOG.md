# Changelog

## [0.1.0] - 2025-12-02

### Features

* Initial release of MCP Filesystem Server
* MCP Protocol compliant with full session lifecycle management
* Persistent session tracking via file-based storage
* LRU eviction for automatic session cleanup when limit reached
* Annotation-driven workspace configuration via ARK Query annotations
* Shared base directory with user-specified workspaces under `/data/`
* Filesystem tools:
  - `read_file` / `read_text_file` - read text files with optional head/tail
  - `read_media_file` - read images and audio files as base64
  - `read_multiple_files` - batch read multiple files
  - `write_file` - create or overwrite files
  - `edit_file` - line-based text edits with diff preview
  - `create_directory` - create directories recursively
  - `list_directory` - list directory contents
  - `list_directory_with_sizes` - list with file sizes and sorting
  - `directory_tree` - recursive JSON tree view
  - `move_file` - move or rename files
  - `search_files` - glob pattern search
  - `get_file_info` - file metadata
  - `list_allowed_directories` - show accessible paths
* Session management via `set_base_directory` tool
* Helm chart with persistent volume support
