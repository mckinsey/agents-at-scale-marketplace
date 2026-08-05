import {
  S3Client,
  GetObjectCommand,
  PutObjectCommand,
  HeadObjectCommand,
  DeleteObjectCommand,
  CopyObjectCommand,
} from "@aws-sdk/client-s3";
import { createUnifiedDiff, normalizeLineEndings } from "../filesystem/lib.js";

// Objects larger than this are refused for full-content operations (read_text_file
// full/head/tail, edit_file) to protect the memory-limited pod. Binary/large data
// should go through byte-range-free media reads or be handled out of band.
export const MAX_TEXT_BYTES = 50 * 1024 * 1024;

export interface S3FileInfo {
  size: number;
  created: Date;
  modified: Date;
  accessed: Date;
  isDirectory: boolean;
  isFile: boolean;
  permissions: string;
}

export class NotFoundError extends Error {}

function isNotFound(error: any): boolean {
  const name = error?.name || error?.Code || "";
  const status = error?.$metadata?.httpStatusCode;
  return name === "NoSuchKey" || name === "NotFound" || status === 404;
}

// Read a whole object as UTF-8 text, guarding against oversized objects.
export async function getObjectText(
  client: S3Client,
  bucket: string,
  key: string
): Promise<string> {
  try {
    const resp = await client.send(
      new GetObjectCommand({ Bucket: bucket, Key: key })
    );
    if ((resp.ContentLength || 0) > MAX_TEXT_BYTES) {
      throw new Error(
        `Object ${key} is ${resp.ContentLength} bytes, which exceeds the ${MAX_TEXT_BYTES}-byte limit for text operations`
      );
    }
    return await (resp.Body as any).transformToString("utf-8");
  } catch (error) {
    if (isNotFound(error)) throw new NotFoundError(`Not found: ${key}`);
    throw error;
  }
}

// Read a whole object as base64 (for media files).
export async function getObjectBase64(
  client: S3Client,
  bucket: string,
  key: string
): Promise<string> {
  try {
    const resp = await client.send(
      new GetObjectCommand({ Bucket: bucket, Key: key })
    );
    const bytes = await (resp.Body as any).transformToByteArray();
    return Buffer.from(bytes).toString("base64");
  } catch (error) {
    if (isNotFound(error)) throw new NotFoundError(`Not found: ${key}`);
    throw error;
  }
}

export async function putObjectText(
  client: S3Client,
  bucket: string,
  key: string,
  content: string,
  contentType = "text/plain; charset=utf-8"
): Promise<void> {
  await client.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: key,
      Body: content,
      ContentType: contentType,
    })
  );
}

export async function putEmptyObject(
  client: S3Client,
  bucket: string,
  key: string
): Promise<void> {
  await client.send(
    new PutObjectCommand({ Bucket: bucket, Key: key, Body: "" })
  );
}

export async function deleteObject(
  client: S3Client,
  bucket: string,
  key: string
): Promise<void> {
  await client.send(new DeleteObjectCommand({ Bucket: bucket, Key: key }));
}

export async function copyObject(
  client: S3Client,
  bucket: string,
  sourceKey: string,
  destKey: string
): Promise<void> {
  await client.send(
    new CopyObjectCommand({
      Bucket: bucket,
      CopySource: `${bucket}/${encodeURIComponent(sourceKey).replace(/%2F/g, "/")}`,
      Key: destKey,
    })
  );
}

// HeadObject → FileInfo. S3 has no created/accessed times or POSIX permissions, so
// those are synthesized to keep the output shape stable for agents that parse it.
export async function headObjectInfo(
  client: S3Client,
  bucket: string,
  key: string
): Promise<S3FileInfo> {
  try {
    const resp = await client.send(
      new HeadObjectCommand({ Bucket: bucket, Key: key })
    );
    const modified = resp.LastModified || new Date(0);
    return {
      size: resp.ContentLength || 0,
      created: modified,
      modified,
      accessed: modified,
      isDirectory: false,
      isFile: true,
      permissions: "",
    };
  } catch (error) {
    if (isNotFound(error)) throw new NotFoundError(`Not found: ${key}`);
    throw error;
  }
}

export async function objectExists(
  client: S3Client,
  bucket: string,
  key: string
): Promise<boolean> {
  try {
    await client.send(new HeadObjectCommand({ Bucket: bucket, Key: key }));
    return true;
  } catch (error) {
    if (isNotFound(error)) return false;
    throw error;
  }
}

// First / last N lines of an already-fetched string (S3 has no line-oriented reads).
export function headLines(text: string, numLines: number): string {
  return normalizeLineEndings(text).split("\n").slice(0, numLines).join("\n");
}

export function tailLines(text: string, numLines: number): string {
  const lines = normalizeLineEndings(text).split("\n");
  return lines.slice(Math.max(0, lines.length - numLines)).join("\n");
}

interface FileEdit {
  oldText: string;
  newText: string;
}

// Pure re-implementation of the filesystem adapter's applyFileEdits matching logic,
// operating on an in-memory string instead of a file handle. Returns the new content
// and a git-style diff. Kept behaviourally identical so edit_file works the same way.
export function applyEditsToString(
  originalContent: string,
  edits: FileEdit[],
  filepath: string
): { modifiedContent: string; formattedDiff: string } {
  const content = normalizeLineEndings(originalContent);
  let modifiedContent = content;

  for (const edit of edits) {
    const normalizedOld = normalizeLineEndings(edit.oldText);
    const normalizedNew = normalizeLineEndings(edit.newText);

    if (modifiedContent.includes(normalizedOld)) {
      modifiedContent = modifiedContent.replace(normalizedOld, normalizedNew);
      continue;
    }

    const oldLines = normalizedOld.split("\n");
    const contentLines = modifiedContent.split("\n");
    let matchFound = false;

    for (let i = 0; i <= contentLines.length - oldLines.length; i++) {
      const potentialMatch = contentLines.slice(i, i + oldLines.length);
      const isMatch = oldLines.every(
        (oldLine, j) => oldLine.trim() === potentialMatch[j].trim()
      );

      if (isMatch) {
        const originalIndent = contentLines[i].match(/^\s*/)?.[0] || "";
        const newLines = normalizedNew.split("\n").map((line, j) => {
          if (j === 0) return originalIndent + line.trimStart();
          const oldIndent = oldLines[j]?.match(/^\s*/)?.[0] || "";
          const newIndent = line.match(/^\s*/)?.[0] || "";
          if (oldIndent && newIndent) {
            const relativeIndent = newIndent.length - oldIndent.length;
            return (
              originalIndent +
              " ".repeat(Math.max(0, relativeIndent)) +
              line.trimStart()
            );
          }
          return line;
        });
        contentLines.splice(i, oldLines.length, ...newLines);
        modifiedContent = contentLines.join("\n");
        matchFound = true;
        break;
      }
    }

    if (!matchFound) {
      throw new Error(`Could not find exact match for edit:\n${edit.oldText}`);
    }
  }

  const diff = createUnifiedDiff(content, modifiedContent, filepath);
  let numBackticks = 3;
  while (diff.includes("`".repeat(numBackticks))) {
    numBackticks++;
  }
  const formattedDiff = `${"`".repeat(numBackticks)}diff\n${diff}${"`".repeat(numBackticks)}\n\n`;
  return { modifiedContent, formattedDiff };
}
