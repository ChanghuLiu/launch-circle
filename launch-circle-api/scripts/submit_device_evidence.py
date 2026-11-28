#!/usr/bin/env python3
"""Attach read-only ADB build facts to actual, externally executed mission evidence.

This adapter does not invent observations or implement a generic core-workflow test.
Read the assigned steps, execute them, then supply their observed results as JSON.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def adb(serial, *args):
    result = subprocess.run(
        ["adb", "-s", serial, *args], capture_output=True, text=True, timeout=30, check=True
    )
    return result.stdout.strip()


def api(base_url, path, token, payload=None):
    request = Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--expected-version", required=True, type=int)
    parser.add_argument("--evidence-file", required=True, type=Path)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Durable request envelope; reuse it with --retry after network failure",
    )
    parser.add_argument(
        "--source", choices=["CODEX_ASSISTED", "AUTOMATED_RUNNER"], default="CODEX_ASSISTED"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retry", action="store_true")
    args = parser.parse_args()
    url = urlsplit(args.base_url)
    if (
        (
            url.scheme != "https"
            and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"})
        )
        or url.username
        or url.password
        or url.query
        or url.fragment
        or not url.hostname
    ):
        parser.error("Use HTTPS, or local loopback HTTP, without URL credentials/query/fragment")
    if not re.fullmatch(r"[A-Za-z0-9_.]+", args.package) or args.expected_version <= 0:
        parser.error("Invalid package or expected version")
    if args.retry:
        envelope = json.loads(args.output.read_text())
        if (
            envelope["base_url"] != args.base_url
            or envelope["mission_id"] != args.mission_id
            or envelope["request"]["package_name"] != args.package
            or envelope["request"]["expected_version_code"] != args.expected_version
        ):
            parser.error("Retry arguments do not match the saved request")
        payload = envelope["request"]
    else:
        if args.output.exists():
            parser.error("Output already exists; use --retry or select a new output")
        evidence = json.loads(args.evidence_file.read_text())
        try:
            if adb(args.serial, "get-state") != "device":
                raise ValueError("Device is not ready")
            package = adb(args.serial, "shell", "dumpsys", "package", args.package)
            version = re.search(r"versionCode=(\d+)", package)
            if not version:
                raise ValueError("App not installed or build could not be read")
            model = adb(args.serial, "shell", "getprop", "ro.product.model")
            api_level = int(adb(args.serial, "shell", "getprop", "ro.build.version.sdk"))
        except (subprocess.SubprocessError, ValueError) as error:
            print(
                json.dumps(
                    {
                        "result": "BLOCKED",
                        "execution_not_started": True,
                        "reason": str(error),
                        "server_run_created": False,
                    }
                )
            )
            return 2
        steps = evidence["steps"]
        result = evidence["result"]
        actual_version = int(version.group(1))
        if actual_version != args.expected_version:
            result = "BLOCKED"
            steps = [
                {
                    **step,
                    "result": "BLOCKED",
                    "actual": f"Wrong installed version: {actual_version}; expected {args.expected_version}",
                }
                for step in steps
            ]
        payload = {
            "idempotency_key": str(uuid4()),
            "execution_source": args.source,
            "result": result,
            "package_name": args.package,
            "version_code": actual_version,
            "expected_version_code": args.expected_version,
            "device_key": hashlib.sha256(args.serial.encode()).hexdigest()[:32],
            "device_model": model,
            "android_api": api_level,
            "steps": steps,
            "note": evidence.get("note", ""),
            "retest_of_id": evidence.get("retest_of_id"),
        }
        # Exclusive creation preserves the original request/key for exact retries.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as output:
            json.dump(
                {"base_url": args.base_url, "mission_id": args.mission_id, "request": payload},
                output,
                indent=2,
            )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "request_saved": str(args.output),
                    "observed_version_code": payload["version_code"],
                    "result": payload["result"],
                }
            )
        )
        return 0
    token = os.environ.get("LAUNCH_CIRCLE_ACCESS_TOKEN")
    if not token:
        parser.error("Set LAUNCH_CIRCLE_ACCESS_TOKEN; do not put it in command arguments")
    try:
        response = api(args.base_url, f"/missions/{args.mission_id}/runs", token, payload)
    except HTTPError as error:
        print(
            json.dumps(
                {
                    "status": error.code,
                    "request_saved": str(args.output),
                    "server_run_confirmed": False,
                }
            )
        )
        return 1
    except OSError:
        print(
            json.dumps(
                {
                    "error": "Transport failed; retry the saved request",
                    "request_saved": str(args.output),
                    "server_run_confirmed": False,
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "run_id": response["id"],
                "result": response["result"],
                "execution_source": response["execution_source"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
