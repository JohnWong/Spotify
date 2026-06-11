"""Switchable file storage between local filesystem and Google Cloud Storage."""

import os


def _storage_mode():
    """Return storage mode: 'gcs' or 'local'. Defaults to 'gcs'."""
    return os.environ.get("STORAGE_MODE", "gcs")


def _gcs_bucket_name():
    bucket = os.environ.get("GCS_BUCKET")
    if not bucket:
        raise RuntimeError("Missing GCS_BUCKET environment variable")
    return bucket


def _read_local(filename):
    if not os.path.exists(filename):
        return ""
    with open(filename, "r") as f:
        return f.read()


def _write_local(filename, data):
    with open(filename, "w") as f:
        f.write(data)


def read_refresh_token(filename="refresh_token.txt"):
    """Read a file from GCS or local filesystem."""
    if _storage_mode() == "gcs":
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(_gcs_bucket_name())
        blob = bucket.blob(filename)
        try:
            return blob.download_as_text(encoding="utf-8")
        except Exception:
            return ""
    return _read_local(filename)


def write_refresh_token(token, filename="refresh_token.txt"):
    """Write a file to GCS or local filesystem."""
    if _storage_mode() == "gcs":
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(_gcs_bucket_name())
        blob = bucket.blob(filename)
        data = token if isinstance(token, bytes) else token.encode("utf-8")
        blob.upload_from_string(data, content_type="text/plain")
        return
    _write_local(filename, token)
