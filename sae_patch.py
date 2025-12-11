"""Switchable refresh_token.txt storage between local file and OSS."""

import __builtin__
import os

from oss_minimal import get_object, put_object


def _storage_mode():
    """Return storage mode: 'oss' or 'local' (default)."""
    return "oss"


def _oss_config():
    """Load OSS configuration from environment."""
    bucket = "imeituan"
    endpoint = "..."
    access_key_id = "..."
    access_key_secret = "..."
    if not (bucket and endpoint and access_key_id and access_key_secret):
        raise RuntimeError(
            "Missing OSS config: set OSS_BUCKET/OSS_ENDPOINT/OSS_ACCESS_KEY_ID/OSS_ACCESS_KEY_SECRET"
        )
    return bucket, endpoint, access_key_id, access_key_secret


def _read_local(filename):
    if not os.path.exists(filename):
        return ""
    with __builtin__.open(filename, "r") as f:  # type: ignore[attr-defined]
        return f.read()


def _write_local(filename, data):
    with __builtin__.open(filename, "w") as f:  # type: ignore[attr-defined]
        f.write(data)


class _OSSFile:
    bucket = ""
    endpoint = ""
    access_key_id = ""
    access_key_secret = ""
    mode = ""
    filename = ""
    log = ""

    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
        self.bucket, self.endpoint, self.access_key_id, self.access_key_secret = _oss_config()

    def read(self):
        data = get_object(
            bucket=self.bucket,
            key=self.filename,
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            endpoint=self.endpoint,
        )
        if "b" in self.mode:
            return data
        return data.decode("utf-8")

    def write(self, data):
        payload = data if isinstance(data, bytes) else str(data).encode("utf-8")
        put_object(
            bucket=self.bucket,
            key=self.filename,
            data=payload,
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
            endpoint=self.endpoint,
            content_type="text/plain",
        )
        return len(payload)

    def seek(self, offset):
        pass

    def close(self):
        pass

    def __enter__(self, *args):
        return self

    def __exit__(self, *args):
        pass


_real_open = __builtin__.open


def fake_open(filename, mode="r", buffering=-1):
    """Fake open that routes refresh_token.txt to OSS when enabled."""
    if filename == "refresh_token.txt":
        return _OSSFile(filename, mode)
    return _real_open(filename, mode, buffering)


def read_refresh_token(filename="refresh_token.txt"):
    """Read refresh token using selected storage."""
    if _storage_mode() == "oss":
        return _OSSFile(filename, "r").read()
    return _read_local(filename)


def write_refresh_token(token, filename="refresh_token.txt"):
    """Write refresh token using selected storage."""
    if _storage_mode() == "oss":
        _OSSFile(filename, "w").write(token)
        return
    _write_local(filename, token)
