import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import path from "path";
import { minimatch } from "minimatch";
import {
  ListObjectsV2Command,
  ListObjectsV2CommandOutput,
} from "@aws-sdk/client-s3";
import {
  TOOL_DEFINITIONS,
  SetBaseDirectoryArgsSchema,
  ReadTextFileArgsSchema,
  ReadMediaFileArgsSchema,
  ReadMultipleFilesArgsSchema,
  WriteFileArgsSchema,
  EditFileArgsSchema,
  CreateDirectoryArgsSchema,
  ListDirectoryArgsSchema,
  ListDirectoryWithSizesArgsSchema,
  DirectoryTreeArgsSchema,
  MoveFileArgsSchema,
  SearchFilesArgsSchema,
  GetFileInfoArgsSchema,
} from "../shared/tool-schemas.js";
import { formatSize } from "../filesystem/lib.js";
import { S3Context } from "./s3-context.js";
import { createS3Client, BUCKET_NAME, KEY_PREFIX } from "./s3-client.js";
import {
  getObjectText,
  getObjectBase64,
  putObjectText,
  putEmptyObject,
  deleteObject,
  copyObject,
  headObjectInfo,
  objectExists,
  headLines,
  tailLines,
  applyEditsToString,
  NotFoundError,
} from "./lib.js";

// S3-backed implementation of the same MCP tool surface as the filesystem adapter.
// Objects are addressed by key; "directories" are key prefixes. Tool names/schemas
// come from the shared module so they stay identical to the filesystem adapter.
export const createServer = async () => {
  if (!BUCKET_NAME) {
    throw new Error(
      "S3 backend selected (STORAGE_BACKEND=s3) but BUCKET_NAME is not set"
    );
  }

  const client = createS3Client();
  const bucket = BUCKET_NAME;
  const ctx = new S3Context(client, bucket, KEY_PREFIX);
  await ctx.initialize();

  const server = new Server(
    {
      name: "secure-filesystem-server",
      version: "0.2.0",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // List one "directory" level using a delimited listing.
  async function listLevel(
    prefix: string
  ): Promise<{ dirs: string[]; files: { name: string; size: number }[] }> {
    const dirs = new Set<string>();
    const files: { name: string; size: number }[] = [];
    let token: string | undefined = undefined;
    do {
      const resp: ListObjectsV2CommandOutput = await client.send(
        new ListObjectsV2Command({
          Bucket: bucket,
          Prefix: prefix,
          Delimiter: "/",
          ContinuationToken: token,
        })
      );
      for (const cp of resp.CommonPrefixes || []) {
        if (cp.Prefix) dirs.add(cp.Prefix.slice(prefix.length).replace(/\/$/, ""));
      }
      for (const obj of resp.Contents || []) {
        if (obj.Key === undefined) continue;
        const name = obj.Key.slice(prefix.length);
        if (name === "" || name.endsWith("/")) continue; // self / directory marker
        files.push({ name, size: obj.Size || 0 });
      }
      token = resp.IsTruncated ? resp.NextContinuationToken : undefined;
    } while (token);
    return { dirs: [...dirs], files };
  }

  const mimeTypes: Record<string, string> = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
  };

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools: TOOL_DEFINITIONS };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "set_base_directory": {
          const parsed = SetBaseDirectoryArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for set_base_directory: ${parsed.error}`);
          }
          const newBase = ctx.setBaseDirectory(parsed.data.path);
          return {
            content: [
              {
                type: "text",
                text: `Successfully set base directory: ${bucket}/${newBase}`.replace(/\/$/, ""),
              },
            ],
          };
        }

        case "read_file":
        case "read_text_file": {
          const parsed = ReadTextFileArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for read_text_file: ${parsed.error}`);
          }
          if (parsed.data.head && parsed.data.tail) {
            throw new Error("Cannot specify both head and tail parameters simultaneously");
          }
          const key = ctx.validateKey(parsed.data.path);
          const text = await getObjectText(client, bucket, key);
          if (parsed.data.tail) {
            return { content: [{ type: "text", text: tailLines(text, parsed.data.tail) }] };
          }
          if (parsed.data.head) {
            return { content: [{ type: "text", text: headLines(text, parsed.data.head) }] };
          }
          return { content: [{ type: "text", text }] };
        }

        case "read_media_file": {
          const parsed = ReadMediaFileArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for read_media_file: ${parsed.error}`);
          }
          const key = ctx.validateKey(parsed.data.path);
          const extension = path.extname(key).toLowerCase();
          const mimeType = mimeTypes[extension] || "application/octet-stream";
          const data = await getObjectBase64(client, bucket, key);
          const type = mimeType.startsWith("image/")
            ? "image"
            : mimeType.startsWith("audio/")
              ? "audio"
              : "blob";
          return { content: [{ type, data, mimeType }] };
        }

        case "read_multiple_files": {
          const parsed = ReadMultipleFilesArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for read_multiple_files: ${parsed.error}`);
          }
          const results = await Promise.all(
            parsed.data.paths.map(async (filePath: string) => {
              try {
                const key = ctx.validateKey(filePath);
                const content = await getObjectText(client, bucket, key);
                return `${filePath}:\n${content}\n`;
              } catch (error) {
                const msg = error instanceof Error ? error.message : String(error);
                return `${filePath}: Error - ${msg}`;
              }
            })
          );
          return { content: [{ type: "text", text: results.join("\n---\n") }] };
        }

        case "write_file": {
          const parsed = WriteFileArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for write_file: ${parsed.error}`);
          }
          const key = ctx.validateKey(parsed.data.path);
          if (key === "") throw new Error("Cannot write to the bucket root");
          await putObjectText(client, bucket, key, parsed.data.content);
          return {
            content: [{ type: "text", text: `Successfully wrote to ${parsed.data.path}` }],
          };
        }

        case "edit_file": {
          const parsed = EditFileArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for edit_file: ${parsed.error}`);
          }
          const key = ctx.validateKey(parsed.data.path);
          const content = await getObjectText(client, bucket, key);
          const { modifiedContent, formattedDiff } = applyEditsToString(
            content,
            parsed.data.edits,
            parsed.data.path
          );
          if (!parsed.data.dryRun) {
            await putObjectText(client, bucket, key, modifiedContent);
          }
          return { content: [{ type: "text", text: formattedDiff }] };
        }

        case "create_directory": {
          const parsed = CreateDirectoryArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for create_directory: ${parsed.error}`);
          }
          const key = ctx.validateKey(parsed.data.path);
          if (key !== "") {
            // Zero-byte marker so the "directory" is visible in listings. Idempotent.
            await putEmptyObject(client, bucket, `${key}/`);
          }
          return {
            content: [{ type: "text", text: `Successfully created directory ${parsed.data.path}` }],
          };
        }

        case "list_directory": {
          const parsed = ListDirectoryArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for list_directory: ${parsed.error}`);
          }
          const prefix = ctx.listingPrefix(parsed.data.path);
          const { dirs, files } = await listLevel(prefix);
          const formatted = [
            ...dirs.map((d) => `[DIR] ${d}`),
            ...files.map((f) => `[FILE] ${f.name}`),
          ].join("\n");
          return { content: [{ type: "text", text: formatted }] };
        }

        case "list_directory_with_sizes": {
          const parsed = ListDirectoryWithSizesArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for list_directory_with_sizes: ${parsed.error}`);
          }
          const prefix = ctx.listingPrefix(parsed.data.path);
          const { dirs, files } = await listLevel(prefix);

          const entries = [
            ...dirs.map((d) => ({ name: d, isDirectory: true, size: 0 })),
            ...files.map((f) => ({ name: f.name, isDirectory: false, size: f.size })),
          ];
          const sorted = [...entries].sort((a, b) => {
            if (parsed.data.sortBy === "size") return b.size - a.size;
            return a.name.localeCompare(b.name);
          });
          const formattedEntries = sorted.map(
            (e) =>
              `${e.isDirectory ? "[DIR]" : "[FILE]"} ${e.name.padEnd(30)} ${
                e.isDirectory ? "" : formatSize(e.size).padStart(10)
              }`
          );
          const totalFiles = files.length;
          const totalDirs = dirs.length;
          const totalSize = files.reduce((sum, f) => sum + f.size, 0);
          const summary = [
            "",
            `Total: ${totalFiles} files, ${totalDirs} directories`,
            `Combined size: ${formatSize(totalSize)}`,
          ];
          return {
            content: [{ type: "text", text: [...formattedEntries, ...summary].join("\n") }],
          };
        }

        case "directory_tree": {
          const parsed = DirectoryTreeArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for directory_tree: ${parsed.error}`);
          }
          interface TreeEntry {
            name: string;
            type: "file" | "directory";
            children?: TreeEntry[];
          }
          const prefix = ctx.listingPrefix(parsed.data.path);
          const all = await ctx.listAllKeys(prefix);
          const excludePatterns = parsed.data.excludePatterns;
          const root: TreeEntry[] = [];

          for (const { key } of all) {
            const rel = key.slice(prefix.length);
            if (rel === "" || rel.endsWith("/")) continue; // skip markers
            const excluded = excludePatterns.some((p) =>
              minimatch(rel, p, { dot: true }) ||
              minimatch(rel, `**/${p}`, { dot: true }) ||
              minimatch(rel, `**/${p}/**`, { dot: true })
            );
            if (excluded) continue;

            const segs = rel.split("/");
            let level = root;
            for (let i = 0; i < segs.length; i++) {
              const isLast = i === segs.length - 1;
              const segName = segs[i];
              let node = level.find((e) => e.name === segName);
              if (!node) {
                node = isLast
                  ? { name: segName, type: "file" }
                  : { name: segName, type: "directory", children: [] };
                level.push(node);
              }
              if (!isLast) {
                if (!node.children) node.children = [];
                level = node.children;
              }
            }
          }
          return { content: [{ type: "text", text: JSON.stringify(root, null, 2) }] };
        }

        case "move_file": {
          const parsed = MoveFileArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for move_file: ${parsed.error}`);
          }
          const srcKey = ctx.validateKey(parsed.data.source);
          const destKey = ctx.validateKey(parsed.data.destination);

          if (await objectExists(client, bucket, srcKey)) {
            if (await objectExists(client, bucket, destKey)) {
              throw new Error(`Destination already exists: ${parsed.data.destination}`);
            }
            // Copy-then-delete (never delete first) so a failure can't lose data.
            await copyObject(client, bucket, srcKey, destKey);
            await deleteObject(client, bucket, srcKey);
          } else {
            // Treat as a prefix (directory) move: copy every descendant then delete.
            const srcPrefix = `${srcKey}/`;
            const all = await ctx.listAllKeys(srcPrefix);
            if (all.length === 0) {
              throw new Error(`Source does not exist: ${parsed.data.source}`);
            }
            for (const { key } of all) {
              const rest = key.slice(srcPrefix.length);
              await copyObject(client, bucket, key, `${destKey}/${rest}`);
            }
            for (const { key } of all) {
              await deleteObject(client, bucket, key);
            }
          }
          return {
            content: [
              {
                type: "text",
                text: `Successfully moved ${parsed.data.source} to ${parsed.data.destination}`,
              },
            ],
          };
        }

        case "search_files": {
          const parsed = SearchFilesArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for search_files: ${parsed.error}`);
          }
          const results = await ctx.searchFilesWithValidation(
            parsed.data.path,
            parsed.data.pattern,
            { excludePatterns: parsed.data.excludePatterns }
          );
          return {
            content: [
              {
                type: "text",
                text: results.length > 0 ? results.join("\n") : "No matches found",
              },
            ],
          };
        }

        case "get_file_info": {
          const parsed = GetFileInfoArgsSchema.safeParse(args);
          if (!parsed.success) {
            throw new Error(`Invalid arguments for get_file_info: ${parsed.error}`);
          }
          const key = ctx.validateKey(parsed.data.path);
          let info;
          try {
            info = await headObjectInfo(client, bucket, key);
          } catch (error) {
            if (error instanceof NotFoundError) {
              // Not an object — see if it's a non-empty prefix (a "directory").
              const children = await listLevel(`${key}/`);
              if (children.dirs.length === 0 && children.files.length === 0) {
                throw new Error(`Not found: ${parsed.data.path}`);
              }
              info = {
                size: 0,
                created: new Date(0),
                modified: new Date(0),
                accessed: new Date(0),
                isDirectory: true,
                isFile: false,
                permissions: "",
              };
            } else {
              throw error;
            }
          }
          return {
            content: [
              {
                type: "text",
                text: Object.entries(info)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join("\n"),
              },
            ],
          };
        }

        case "list_allowed_directories": {
          return {
            content: [
              {
                type: "text",
                text: `Allowed directories:\n${ctx.getAllowedDirectories().join("\n")}`,
              },
            ],
          };
        }

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return {
        content: [{ type: "text", text: `Error: ${errorMessage}` }],
        isError: true,
      };
    }
  });

  server.oninitialized = async () => {
    const allowedDirs = ctx.getAllowedDirectories();
    if (allowedDirs.length > 0) {
      console.error("Using allowed directories (s3)", allowedDirs);
    } else {
      throw new Error("Server cannot operate: no allowed directories available");
    }
  };

  return server;
};
