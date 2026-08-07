import { S3Client } from "@aws-sdk/client-s3";

// Builds an S3 client configured the same way the file-api's boto3 client is
// (see services/file-gateway/services/file-api/src/file_api/s3_client.py): it points
// at an S3-compatible endpoint (VersityGW in-cluster, or real S3) and uses path-style
// addressing. forcePathStyle is REQUIRED for VersityGW / MinIO-style endpoints reached
// by service DNS, otherwise the SDK builds a virtual-host URL (bucket.<host>) that
// won't resolve.
export function createS3Client(): S3Client {
  const endpoint = process.env.AWS_ENDPOINT_URL || undefined;
  const region = process.env.AWS_REGION || "us-east-1";

  return new S3Client({
    endpoint,
    region,
    forcePathStyle: true,
    // Credentials come from the standard AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY /
    // AWS_SESSION_TOKEN environment variables via the SDK's default provider chain, so
    // both static and IRSA/pod-identity credentials work without extra wiring.
  });
}

export const BUCKET_NAME = process.env.BUCKET_NAME || "";

// Optional key prefix under which all operations are scoped (analogue of the
// filesystem adapter's BASE_DATA_DIR). Empty means the bucket root, so the MCP shares
// the same keyspace as the file-api.
export const KEY_PREFIX = process.env.S3_KEY_PREFIX || "";
