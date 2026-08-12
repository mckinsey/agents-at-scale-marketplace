// Shared tool argument schemas and MCP tool descriptors.
//
// Both the filesystem and s3 adapters import from here so that the tool NAMES and
// inputSchemas they expose are guaranteed identical. Ark derives Tool CRD names from
// the MCP tool names, so any drift between adapters would silently break agents that
// reference the existing `*-write-file`, `*-read-file`, etc. tools. Keeping one source
// of truth prevents that.

import { z } from "zod";

// Schema definitions
export const SetBaseDirectoryArgsSchema = z.object({
  path: z.string().describe("The new root directory for file operations."),
});

export const ReadTextFileArgsSchema = z.object({
  path: z.string(),
  tail: z
    .number()
    .optional()
    .describe("If provided, returns only the last N lines of the file"),
  head: z
    .number()
    .optional()
    .describe("If provided, returns only the first N lines of the file"),
});

export const ReadMediaFileArgsSchema = z.object({
  path: z.string(),
});

export const ReadMultipleFilesArgsSchema = z.object({
  paths: z
    .array(z.string())
    .min(1, "At least one file path must be provided")
    .describe(
      "Array of file paths to read. Each path must be a string pointing to a valid file within allowed directories."
    ),
});

export const WriteFileArgsSchema = z.object({
  path: z.string(),
  content: z.string(),
});

export const EditOperation = z.object({
  oldText: z.string().describe("Text to search for - must match exactly"),
  newText: z.string().describe("Text to replace with"),
});

export const EditFileArgsSchema = z.object({
  path: z.string(),
  edits: z.array(EditOperation),
  dryRun: z
    .boolean()
    .default(false)
    .describe("Preview changes using git-style diff format"),
});

export const CreateDirectoryArgsSchema = z.object({
  path: z.string(),
});

export const ListDirectoryArgsSchema = z.object({
  path: z.string(),
});

export const ListDirectoryWithSizesArgsSchema = z.object({
  path: z.string(),
  sortBy: z
    .enum(["name", "size"])
    .optional()
    .default("name")
    .describe("Sort entries by name or size"),
});

export const DirectoryTreeArgsSchema = z.object({
  path: z.string(),
  excludePatterns: z.array(z.string()).optional().default([]),
});

export const MoveFileArgsSchema = z.object({
  source: z.string(),
  destination: z.string(),
});

export const SearchFilesArgsSchema = z.object({
  path: z.string(),
  pattern: z.string(),
  excludePatterns: z.array(z.string()).optional().default([]),
});

export const GetFileInfoArgsSchema = z.object({
  path: z.string().nonempty(),
});

type ToolInput = any;

// The canonical list of tools exposed over MCP. Order and names must stay stable.
export const TOOL_DEFINITIONS: Array<{
  name: string;
  description: string;
  inputSchema: ToolInput;
}> = [
  {
    name: "set_base_directory",
    description:
      "Add a directory to the allowed directories list. This allows file operations " +
      "to access files within this directory in addition to the session directory.",
    inputSchema: z.toJSONSchema(SetBaseDirectoryArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "read_file",
    description:
      "Read the complete contents of a file as text. DEPRECATED: Use read_text_file instead.",
    inputSchema: z.toJSONSchema(ReadTextFileArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "read_text_file",
    description:
      "Read the complete contents of a file from the file system as text. " +
      "Handles various text encodings and provides detailed error messages " +
      "if the file cannot be read. Use this tool when you need to examine " +
      "the contents of a single file. Use the 'head' parameter to read only " +
      "the first N lines of a file, or the 'tail' parameter to read only " +
      "the last N lines of a file. Operates on the file as text regardless of extension. " +
      "Only works within allowed directories.",
    inputSchema: z.toJSONSchema(ReadTextFileArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "read_media_file",
    description:
      "Read an image or audio file. Returns the base64 encoded data and MIME type. " +
      "Only works within allowed directories.",
    inputSchema: z.toJSONSchema(ReadMediaFileArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "read_multiple_files",
    description:
      "Read the contents of multiple files simultaneously. This is more " +
      "efficient than reading files one by one when you need to analyze " +
      "or compare multiple files. Each file's content is returned with its " +
      "path as a reference. Failed reads for individual files won't stop " +
      "the entire operation. Only works within allowed directories.",
    inputSchema: z.toJSONSchema(ReadMultipleFilesArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "write_file",
    description:
      "Create a new file or completely overwrite an existing file with new content. " +
      "Use with caution as it will overwrite existing files without warning. " +
      "Handles text content with proper encoding. Only works within allowed directories.",
    inputSchema: z.toJSONSchema(WriteFileArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "edit_file",
    description:
      "Make line-based edits to a text file. Each edit replaces exact line sequences " +
      "with new content. Returns a git-style diff showing the changes made. " +
      "Only works within allowed directories.",
    inputSchema: z.toJSONSchema(EditFileArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "create_directory",
    description:
      "Create a new directory or ensure a directory exists. Can create multiple " +
      "nested directories in one operation. If the directory already exists, " +
      "this operation will succeed silently. Perfect for setting up directory " +
      "structures for projects or ensuring required paths exist. Only works within allowed directories.",
    inputSchema: z.toJSONSchema(CreateDirectoryArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "list_directory",
    description:
      "Get a detailed listing of all files and directories in a specified path. " +
      "Results clearly distinguish between files and directories with [FILE] and [DIR] " +
      "prefixes. This tool is essential for understanding directory structure and " +
      "finding specific files within a directory. Only works within allowed directories.",
    inputSchema: z.toJSONSchema(ListDirectoryArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "list_directory_with_sizes",
    description:
      "Get a detailed listing of all files and directories in a specified path, including sizes. " +
      "Results clearly distinguish between files and directories with [FILE] and [DIR] " +
      "prefixes. This tool is useful for understanding directory structure and " +
      "finding specific files within a directory. Only works within allowed directories.",
    inputSchema: z.toJSONSchema(ListDirectoryWithSizesArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "directory_tree",
    description:
      "Get a recursive tree view of files and directories as a JSON structure. " +
      "Each entry includes 'name', 'type' (file/directory), and 'children' for directories. " +
      "Files have no children array, while directories always have a children array (which may be empty). " +
      "The output is formatted with 2-space indentation for readability. Only works within allowed directories.",
    inputSchema: z.toJSONSchema(DirectoryTreeArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "move_file",
    description:
      "Move or rename files and directories. Can move files between directories " +
      "and rename them in a single operation. If the destination exists, the " +
      "operation will fail. Works across different directories and can be used " +
      "for simple renaming within the same directory. Both source and destination must be within allowed directories.",
    inputSchema: z.toJSONSchema(MoveFileArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "search_files",
    description:
      "Recursively search for files and directories matching a pattern. " +
      "The patterns should be glob-style patterns that match paths relative to the working directory. " +
      "Use pattern like '*.ext' to match files in current directory, and '**/*.ext' to match files in all subdirectories. " +
      "Returns full paths to all matching items. Great for finding files when you don't know their exact location. " +
      "Only searches within allowed directories.",
    inputSchema: z.toJSONSchema(SearchFilesArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "get_file_info",
    description:
      "Retrieve detailed metadata about a file or directory. Returns comprehensive " +
      "information including size, creation time, last modified time, permissions, " +
      "and type. This tool is perfect for understanding file characteristics " +
      "without reading the actual content. Only works within allowed directories.",
    inputSchema: z.toJSONSchema(GetFileInfoArgsSchema, { io: "input" }) as ToolInput,
  },
  {
    name: "list_allowed_directories",
    description:
      "Returns the list of directories that this server is allowed to access. " +
      "Subdirectories within these allowed directories are also accessible. " +
      "Use this to understand which directories and their nested paths are available " +
      "before trying to access files.",
    inputSchema: {
      type: "object",
      properties: {},
      required: [],
    },
  },
];
