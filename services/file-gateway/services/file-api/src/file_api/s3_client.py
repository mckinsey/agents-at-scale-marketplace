import boto3
from botocore.client import Config
from typing import Dict, Any, Optional

from .config import settings


class ListFilesResponse:
    def __init__(
        self,
        files: list[Dict[str, Any]],
        directories: list[Dict[str, Any]],
        next_token: Optional[str] = None,
    ):
        self.files = files
        self.directories = directories
        self.next_token = next_token


class S3Client:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            config=Config(signature_version="s3v4"),
        )
        self.bucket_name = settings.bucket_name

    def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000,
        continuation_token: Optional[str] = None,
        delimiter: str = "/",
    ) -> ListFilesResponse:
        params = {
            "Bucket": self.bucket_name,
            "Prefix": prefix,
            "MaxKeys": max_keys,
            "Delimiter": delimiter,
        }

        if continuation_token:
            params["ContinuationToken"] = continuation_token

        response = self.client.list_objects_v2(**params)

        files = []
        if "Contents" in response:
            for obj in response["Contents"]:
                files.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "etag": obj["ETag"].strip('"'),
                })

        directories = []
        if "CommonPrefixes" in response:
            for prefix_obj in response["CommonPrefixes"]:
                directories.append({
                    "prefix": prefix_obj["Prefix"],
                })

        next_token = response.get("NextContinuationToken")
        return ListFilesResponse(
            files=files, directories=directories, next_token=next_token
        )

    def delete_file(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=key)

    def delete_prefix(self, prefix: str) -> Dict[str, Any]:
        objects_to_delete = []
        paginator = self.client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    objects_to_delete.append({"Key": obj["Key"]})

        if not objects_to_delete:
            return {"deleted_count": 0}

        response = self.client.delete_objects(
            Bucket=self.bucket_name,
            Delete={"Objects": objects_to_delete}
        )

        deleted_count = len(response.get("Deleted", []))
        return {"deleted_count": deleted_count, "keys": [obj["Key"] for obj in response.get("Deleted", [])]}

    def upload_file(self, file_obj, key: str) -> Dict[str, Any]:
        self.client.upload_fileobj(file_obj, self.bucket_name, key)
        response = self.client.head_object(Bucket=self.bucket_name, Key=key)
        return {
            "key": key,
            "size": response["ContentLength"],
            "last_modified": response["LastModified"].isoformat(),
            "etag": response["ETag"].strip('"'),
        }

    def download_file(self, key: str):
        response = self.client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"]


s3_client = S3Client()
