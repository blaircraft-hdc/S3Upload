import os
import tempfile
from typing import Optional

import boto3


def get_session(
    profile: Optional[str] = None,
    region: str = "ca-central-1",
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    session_token: Optional[str] = None,
) -> boto3.Session:
    if access_key and secret_key:
        return boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )

    if profile:
        return boto3.Session(profile_name=profile, region_name=region)

    env_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    env_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if env_access_key and env_secret_key:
        return boto3.Session(
            aws_access_key_id=env_access_key,
            aws_secret_access_key=env_secret_key,
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
            region_name=region,
        )

    return boto3.Session(region_name=region)


def list_buckets(session: boto3.Session) -> list[str]:
    s3 = session.client("s3")
    response = s3.list_buckets()
    return [b["Name"] for b in response.get("Buckets", [])]


def list_objects_at_prefix(
    session: boto3.Session, bucket: str, prefix: str = ""
) -> tuple[list[str], list[dict]]:
    """List one level of a bucket, returning (folder_prefixes, file_objects)."""
    s3 = session.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    folders: list[str] = []
    files: list[dict] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/"):
        for cp in page.get("CommonPrefixes", []):
            folders.append(cp["Prefix"])
        for obj in page.get("Contents", []):
            if obj["Key"] != prefix:  # skip folder placeholder objects
                files.append({"key": obj["Key"], "size": obj["Size"]})
    return folders, files


def list_objects(session: boto3.Session, bucket: str) -> list[dict]:
    s3 = session.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    objects = []
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            objects.append({"key": obj["Key"], "size": obj["Size"]})
    return objects


def upload_file(
    session: boto3.Session, bucket: str, file_path: str, key: Optional[str] = None
) -> None:
    s3 = session.client("s3")
    if key is None:
        key = os.path.basename(file_path)
    s3.upload_file(file_path, bucket, key)


def delete_object(session: boto3.Session, bucket: str, key: str) -> None:
    s3 = session.client("s3")
    s3.delete_object(Bucket=bucket, Key=key)


def download_file(session: boto3.Session, bucket: str, key: str) -> str:
    """Download an S3 object to a temp file and return its path."""
    suffix = os.path.splitext(key)[1]
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    s3 = session.client("s3")
    s3.download_file(bucket, key, path)
    return path


def upload_folder(
    session: boto3.Session, bucket: str, folder_path: str, key_prefix: str = ""
) -> tuple[list[str], list[tuple[str, str]]]:
    """Upload all files under folder_path, preserving relative paths as S3 keys.

    Returns (succeeded_keys, [(failed_path, error_message), ...]).
    """
    s3 = session.client("s3")
    succeeded: list[str] = []
    failed: list[tuple[str, str]] = []
    for dirpath, _, filenames in os.walk(folder_path):
        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, os.path.dirname(folder_path))
            key = key_prefix + rel_path.replace(os.sep, "/")
            try:
                s3.upload_file(abs_path, bucket, key)
                succeeded.append(key)
            except Exception as e:
                failed.append((abs_path, str(e)))
    return succeeded, failed
