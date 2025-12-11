"""Minimal read/write helpers for Aliyun OSS without using any SDK.

The helpers sign requests with Signature V2:
- Only standard libraries and `requests` are required.
- Supports simple GET and PUT against a bucket endpoint.

Example:
    from oss_minimal import get_object, put_object

    put_object(
        bucket="my-bucket",
        key="path/to/file.txt",
        data=b"hello",
        access_key_id="AKID",
        access_key_secret="SECRET",
        endpoint="oss-cn-hangzhou.aliyuncs.com",
    )
    content = get_object(
        bucket="my-bucket",
        key="path/to/file.txt",
        access_key_id="AKID",
        access_key_secret="SECRET",
        endpoint="oss-cn-hangzhou.aliyuncs.com",
    )
"""

import base64
import datetime as _dt
import hashlib
import hmac

import requests


def _rfc1123_now():
    """Return current time in GMT formatted per RFC 1123."""
    return _dt.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


def _canonicalized_headers(headers):
    """Build CanonicalizedOSSHeaders string from headers starting with x-oss-."""
    items = []
    for name, value in headers.items():
        lname = name.lower()
        if lname.startswith("x-oss-"):
            items.append("%s:%s" % (lname, value.strip()))
    items.sort()
    return "\n".join(items)


def _sign(
    method,
    content_md5,
    content_type,
    date,
    canonicalized_headers,
    canonicalized_resource,
    access_key_id,
    access_key_secret,
):
    """Return Authorization header value for OSS V2."""
    parts = [
        method,
        content_md5 or "",
        content_type or "",
        date,
    ]
    if canonicalized_headers:
        parts.append(canonicalized_headers)
    parts.append(canonicalized_resource)
    string_to_sign = "\n".join(parts)
    signature = hmac.new(
        access_key_secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    encoded = base64.b64encode(signature).decode("utf-8")
    return "OSS %s:%s" % (access_key_id, encoded)


def _object_url(bucket, endpoint, key):
    return "https://%s.%s/%s" % (bucket, endpoint, key.lstrip("/"))


def put_object(
    bucket,
    key,
    data,
    access_key_id,
    access_key_secret,
    endpoint,
    content_type="application/octet-stream",
    extra_headers=None,
    timeout=15,
):
    """Upload bytes to OSS via PUT.

    Raises requests.HTTPError on non-2xx responses.
    """
    md5_b64 = base64.b64encode(hashlib.md5(data).digest()).decode("utf-8")
    date = _rfc1123_now()
    headers = {
        "Content-MD5": md5_b64,
        "Content-Type": content_type,
        "Date": date,
    }
    if extra_headers:
        headers.update(extra_headers)
    canonicalized = _canonicalized_headers(headers)
    resource = "/%s/%s" % (bucket, key.lstrip("/"))
    headers["Authorization"] = _sign(
        method="PUT",
        content_md5=md5_b64,
        content_type=content_type,
        date=date,
        canonicalized_headers=canonicalized,
        canonicalized_resource=resource,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
    )
    resp = requests.put(
        _object_url(bucket, endpoint, key),
        data=data,
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()


def get_object(
    bucket,
    key,
    access_key_id,
    access_key_secret,
    endpoint,
    extra_headers=None,
    timeout=15,
):
    """Download object bytes via GET.

    Raises requests.HTTPError on non-2xx responses.
    """
    date = _rfc1123_now()
    headers = {"Date": date}
    if extra_headers:
        headers.update(extra_headers)
    canonicalized = _canonicalized_headers(headers)
    resource = "/%s/%s" % (bucket, key.lstrip("/"))
    headers["Authorization"] = _sign(
        method="GET",
        content_md5="",
        content_type="",
        date=date,
        canonicalized_headers=canonicalized,
        canonicalized_resource=resource,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
    )
    resp = requests.get(
        _object_url(bucket, endpoint, key),
        headers=headers,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.content


__all__ = ["put_object", "get_object"]