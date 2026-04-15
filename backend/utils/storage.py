import shutil
import os
from pathlib import Path
from uuid import uuid4
from abc import ABC, abstractmethod
from typing import Optional

import boto3
from botocore.config import Config
try:
    from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
except ImportError:
    BlobServiceClient = None

from fastapi import UploadFile
from backend.utils.config import get_settings


class StorageProvider(ABC):
    @abstractmethod
    def save_file(self, file_content, remote_path: str) -> str:
        """Saves file and returns the remote path or URL."""
        pass

    @abstractmethod
    def get_url(self, remote_path: str) -> str:
        """Returns a URL/Path for the file (e.g. pre-signed S3 URL)."""
        pass

    @abstractmethod
    def ensure_local_copy(self, remote_path: str) -> Path:
        """Ensures a local copy exists and returns its Path."""
        pass

    @abstractmethod
    def sync_dir_to_remote(self, local_dir: Path, remote_prefix: str):
        """Uploads all files from a local directory to a remote prefix."""
        pass

    @abstractmethod
    def delete_dir(self, remote_dir: str):
        """Deletes a directory/prefix."""
        pass

    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: Path):
        self.root = root

    def save_file(self, file_content, remote_path: str) -> str:
        dest = self.root / remote_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(file_content, "read"):
            with dest.open("wb") as f:
                shutil.copyfileobj(file_content, f)
        else:
            with dest.open("wb") as f:
                f.write(file_content)
        return str(dest.resolve())

    def get_url(self, remote_path: str) -> str:
        # For local, we return a path relative to the storage root or absolute
        return str((self.root / remote_path).resolve())

    def ensure_local_copy(self, remote_path: str) -> Path:
        return (self.root / remote_path).resolve()

    def sync_dir_to_remote(self, local_dir: Path, remote_prefix: str):
        dest = self.root / remote_prefix
        if dest.resolve() != local_dir.resolve():
            shutil.copytree(local_dir, dest, dirs_exist_ok=True)

    def delete_dir(self, remote_dir: str):
        path = self.root / remote_dir
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def exists(self, remote_path: str) -> bool:
        return (self.root / remote_path).exists()


class S3StorageProvider(StorageProvider):
    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str, local_root: Path):
        self.bucket = bucket
        self.local_root = local_root
        self.s3 = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4")
        )

    def save_file(self, file_content, remote_path: str) -> str:
        if hasattr(file_content, "seek"):
            file_content.seek(0)
        self.s3.upload_fileobj(file_content, self.bucket, remote_path)
        return remote_path

    def get_url(self, remote_path: str) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": remote_path},
            ExpiresIn=3600
        )

    def ensure_local_copy(self, remote_path: str) -> Path:
        local_path = self.local_root / "scratch" / remote_path
        if not local_path.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.s3.download_file(self.bucket, remote_path, str(local_path))
        return local_path

    def sync_dir_to_remote(self, local_dir: Path, remote_prefix: str):
        for root_dir, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = Path(root_dir) / file
                relative_path = local_path.relative_to(local_dir)
                remote_path = f"{remote_prefix}/{relative_path}"
                self.s3.upload_file(str(local_path), self.bucket, str(remote_path))

    def delete_dir(self, remote_dir: str):
        # S3 "directories" are just prefixes
        objects_to_delete = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=remote_dir)
        if "Contents" in objects_to_delete:
            delete_keys = [{"Key": obj["Key"]} for obj in objects_to_delete["Contents"]]
            self.s3.delete_objects(Bucket=self.bucket, Delete={"Objects": delete_keys})

    def exists(self, remote_path: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=remote_path)
            return True
        except:
            return False


class AzureStorageProvider(StorageProvider):
    def __init__(self, connection_string: str, container_name: str, local_root: Path):
        self.container_name = container_name
        self.local_root = local_root
        if BlobServiceClient:
            self.service_client = BlobServiceClient.from_connection_string(connection_string)
            self.container_client = self.service_client.get_container_client(container_name)
            if not self.container_client.exists():
                self.container_client.create_container()
        else:
            self.service_client = None

    def save_file(self, file_content, remote_path: str) -> str:
        blob_client = self.container_client.get_blob_client(remote_path)
        if hasattr(file_content, "seek"):
            file_content.seek(0)
        blob_client.upload_blob(file_content, overwrite=True)
        return remote_path

    def get_url(self, remote_path: str) -> str:
        # Generate SAS token for Azure
        from datetime import datetime, timedelta
        blob_client = self.container_client.get_blob_client(remote_path)
        sas_token = generate_blob_sas(
            account_name=self.service_client.account_name,
            container_name=self.container_name,
            blob_name=remote_path,
            account_key=self.service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        return f"{blob_client.url}?{sas_token}"

    def ensure_local_copy(self, remote_path: str) -> Path:
        local_path = self.local_root / "scratch" / remote_path
        if not local_path.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob_client = self.container_client.get_blob_client(remote_path)
            with open(local_path, "wb") as f:
                f.write(blob_client.download_blob().readall())
        return local_path

    def sync_dir_to_remote(self, local_dir: Path, remote_prefix: str):
        for root_dir, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = Path(root_dir) / file
                relative_path = local_path.relative_to(local_dir)
                remote_path = f"{remote_prefix}/{relative_path}"
                blob_client = self.container_client.get_blob_client(remote_path)
                with open(local_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)

    def delete_dir(self, remote_dir: str):
        blobs = self.container_client.list_blobs(name_starts_with=remote_dir)
        for blob in blobs:
            self.container_client.delete_blob(blob.name)

    def exists(self, remote_path: str) -> bool:
        return self.container_client.get_blob_client(remote_path).exists()


def get_storage() -> StorageProvider:
    settings = get_settings()
    mode = settings.storage_backend.upper()
    if mode == "S3":
        return S3StorageProvider(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            local_root=settings.storage_root
        )
    elif mode == "AZURE":
        return AzureStorageProvider(
            connection_string=settings.azure_connection_string,
            container_name=settings.azure_container,
            local_root=settings.storage_root
        )
    else:
        return LocalStorageProvider(settings.storage_root)


# Legacy helpers for minimal refactoring where possible
def ensure_scene_dirs(scene_id: str) -> dict[str, str]:
    """Compatibility helper. For Cloud, these are just prefixes."""
    return {
        "raw_dir": f"raw/{scene_id}",
        "frames_dir": f"frames/{scene_id}",
        "sparse_dir": f"recon/{scene_id}",
        "splats_dir": f"splats/{scene_id}",
        "features_dir": f"features/{scene_id}",
    }


def save_upload(upload: UploadFile, remote_dir: str) -> str:
    storage = get_storage()
    filename = upload.filename or f"upload-{uuid4().hex}"
    remote_path = f"{remote_dir}/{filename}"
    return storage.save_file(upload.file, remote_path)


def purge_scene_data(scene_id: str) -> dict[str, bool]:
    storage = get_storage()
    to_delete = [f"raw/{scene_id}", f"recon/{scene_id}", f"features/{scene_id}"]
    for d in to_delete:
        storage.delete_dir(d)
    return {"purged": True}
