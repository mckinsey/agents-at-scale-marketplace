import {
  S3Client,
  HeadBucketCommand,
  ListObjectsV2Command,
  ListObjectsV2CommandOutput,
} from "@aws-sdk/client-s3";
import { minimatch } from "minimatch";

// S3 analogue of the filesystem adapter's FilesystemContext. It holds an S3 client,
// the bucket, and a current "base prefix" (analogue of baseDirectory) plus a list of
// allowed prefixes (analogue of allowedDirectories). All path handling is pure
// key-prefix string math — S3 has no symlinks, realpath, or true directories, so none
// of the filesystem path-validation utilities apply. "Directories" are key prefixes.

function stripLeadingSlashes(p: string): string {
  return p.replace(/^\/+/, "");
}

// Resolve "." / ".." segments within a raw key string. Throws if traversal escapes the
// top of the keyspace entirely. Containment against the base prefix is enforced
// separately by isAllowed().
function resolveKey(raw: string): string {
  const stack: string[] = [];
  for (const seg of raw.split("/")) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") {
      if (stack.length === 0) {
        throw new Error("Access denied - path escapes the base prefix");
      }
      stack.pop();
      continue;
    }
    stack.push(seg);
  }
  return stack.join("/");
}

// Normalize a configured prefix to either "" (bucket root) or a value ending in "/".
function normalizePrefix(prefix: string): string {
  const clean = resolveKey(stripLeadingSlashes(prefix));
  return clean === "" ? "" : `${clean}/`;
}

export class S3Context {
  private client: S3Client;
  private bucket: string;
  private rootPrefix: string;
  private basePrefix: string;
  private allowedPrefixes: string[];

  constructor(client: S3Client, bucket: string, keyPrefix: string) {
    this.client = client;
    this.bucket = bucket;
    this.rootPrefix = normalizePrefix(keyPrefix);
    this.basePrefix = this.rootPrefix;
    // Seed with the root prefix so getAllowedDirectories() is never empty (the MCP
    // server's oninitialized hook refuses to operate with no allowed directories).
    this.allowedPrefixes = [this.rootPrefix];
  }

  async initialize(): Promise<void> {
    // Fail fast if the bucket is missing/unreachable, turning a late per-request
    // NoSuchBucket into a clear startup error. Never creates the bucket.
    try {
      await this.client.send(new HeadBucketCommand({ Bucket: this.bucket }));
      console.log(
        `[S3] Using bucket "${this.bucket}" with base prefix "${this.basePrefix || "(root)"}"`
      );
    } catch (error) {
      console.error(
        `[S3] Bucket "${this.bucket}" is not accessible. It must already exist and the credentials must be valid.`,
        error
      );
      throw error;
    }
  }

  getBaseDirectory(): string {
    return this.basePrefix;
  }

  getAllowedDirectories(): string[] {
    return this.allowedPrefixes.map(
      (p) => `${this.bucket}/${p}`.replace(/\/$/, "")
    );
  }

  getClient(): S3Client {
    return this.client;
  }

  getBucket(): string {
    return this.bucket;
  }

  // Sets the working prefix, scoped under the immutable root prefix. Pure metadata —
  // unlike the filesystem adapter there is no directory to create.
  setBaseDirectory(workspace: string): string {
    const clean = resolveKey(stripLeadingSlashes(workspace));
    const newBase = clean === "" ? this.rootPrefix : `${this.rootPrefix}${clean}/`;
    this.basePrefix = newBase;
    if (!this.allowedPrefixes.includes(newBase)) {
      this.allowedPrefixes.push(newBase);
    }
    return newBase;
  }

  private isAllowed(key: string): boolean {
    return this.allowedPrefixes.some((p) => {
      const base = p.replace(/\/$/, "");
      if (base === "") return true; // bucket root allows everything
      return key === base || key.startsWith(`${base}/`);
    });
  }

  // Resolve a client-supplied path to a full, validated S3 object key relative to the
  // current base prefix. Throws on traversal outside the allowed prefixes.
  validateKey(requestedPath: string): string {
    if (requestedPath.includes("\0")) {
      throw new Error("Access denied - null byte in path");
    }
    const combined = `${this.basePrefix}${stripLeadingSlashes(requestedPath)}`;
    const key = resolveKey(combined);
    if (!this.isAllowed(key)) {
      throw new Error(
        `Access denied - key outside allowed prefixes: ${key} not in ${this.allowedPrefixes.join(", ")}`
      );
    }
    return key;
  }

  // The listing prefix for the "directory" named by a path: the object key plus a
  // trailing slash, or the base/root prefix when the path is empty.
  listingPrefix(requestedPath: string): string {
    const key = this.validateKey(requestedPath);
    return key === "" ? "" : `${key}/`;
  }

  // Flat, paginated listing of every key under a prefix (no delimiter). Used by
  // search_files and directory_tree.
  async listAllKeys(prefix: string): Promise<{ key: string; size: number }[]> {
    const out: { key: string; size: number }[] = [];
    let token: string | undefined = undefined;
    do {
      const resp: ListObjectsV2CommandOutput = await this.client.send(
        new ListObjectsV2Command({
          Bucket: this.bucket,
          Prefix: prefix,
          ContinuationToken: token,
        })
      );
      for (const obj of resp.Contents || []) {
        if (obj.Key === undefined) continue;
        out.push({ key: obj.Key, size: obj.Size || 0 });
      }
      token = resp.IsTruncated ? resp.NextContinuationToken : undefined;
    } while (token);
    return out;
  }

  // Glob search mirroring FilesystemContext.searchFilesWithValidation: list everything
  // under rootPath's prefix and minimatch each key's path relative to that prefix.
  async searchFilesWithValidation(
    requestedRoot: string,
    pattern: string,
    options: { excludePatterns?: string[] } = {}
  ): Promise<string[]> {
    const { excludePatterns = [] } = options;
    const rootPrefix = this.listingPrefix(requestedRoot);
    const all = await this.listAllKeys(rootPrefix);
    const results: string[] = [];
    for (const { key } of all) {
      if (key.endsWith("/")) continue; // skip directory markers
      const relative = rootPrefix ? key.slice(rootPrefix.length) : key;
      const excluded = excludePatterns.some((p) =>
        minimatch(relative, p, { dot: true })
      );
      if (excluded) continue;
      if (minimatch(relative, pattern, { dot: true })) {
        results.push(key);
      }
    }
    return results;
  }
}
