#!/usr/bin/env python3
"""Minimal UniFi API client. Read-only by default: non-GET requests require --allow-write."""
import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

CLOUD_BASE = "https://api.ui.com"
LOCAL_PREFIX = "/proxy/network/integration"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env(Path(__file__).with_name(".env"))

    parser = argparse.ArgumentParser(description="UniFi API client (read-only by default)")
    parser.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    parser.add_argument("path", help="API path, e.g. /v1/hosts")
    parser.add_argument("--local", action="store_true", help="use local controller Integration API")
    parser.add_argument("--data", help="JSON body for write requests")
    parser.add_argument("--allow-write", action="store_true",
                        help="permit non-GET requests (ONLY with explicit user approval)")
    args = parser.parse_args()

    if args.method != "GET" and not args.allow_write:
        print(f"BLOCKED: {args.method} змінює дані. Потрібен явний дозвіл користувача і прапорець --allow-write.",
              file=sys.stderr)
        return 2

    ctx = None
    if args.local:
        host = os.environ.get("UNIFI_LOCAL_HOST", "").rstrip("/")
        key = os.environ.get("UNIFI_LOCAL_API_KEY", "")
        if not host or not key:
            print("Не задано UNIFI_LOCAL_HOST / UNIFI_LOCAL_API_KEY у .env", file=sys.stderr)
            return 1
        url = host + LOCAL_PREFIX + args.path
        if os.environ.get("UNIFI_LOCAL_VERIFY_SSL", "0") == "0":
            ctx = ssl._create_unverified_context()
    else:
        key = os.environ.get("UNIFI_API_KEY", "")
        if not key:
            print("Не задано UNIFI_API_KEY у .env", file=sys.stderr)
            return 1
        url = CLOUD_BASE + args.path

    body = args.data.encode() if args.data else None
    req = urllib.request.Request(url, data=body, method=args.method, headers={
        "X-API-KEY": key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode(errors='replace')}", file=sys.stderr)
        return 1

    try:
        print(json.dumps(json.loads(raw), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(raw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
