import os
from typing import Optional

import boto3


def get_session(profile: Optional[str] = None, region: str = "ca-central-1") -> boto3.Session:
    if profile:
        return boto3.Session(profile_name=profile, region_name=region)

    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        return boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
            region_name=region,
        )

    return boto3.Session(region_name=region)


def list_buckets(session: boto3.Session) -> list[str]:
    s3 = session.client("s3")
    response = s3.list_buckets()
    return [b["Name"] for b in response.get("Buckets", [])]


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
