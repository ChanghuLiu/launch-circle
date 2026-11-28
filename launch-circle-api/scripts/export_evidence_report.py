"""Export an owner-scoped pilot report; credentials stay in the environment."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from scripts.submit_device_evidence import api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--output-directory", required=True, type=Path)
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
        parser.error("Use HTTPS or loopback HTTP without URL credentials/query/fragment")
    token = os.environ.get("LAUNCH_CIRCLE_ACCESS_TOKEN")
    if not token:
        parser.error("Set LAUNCH_CIRCLE_ACCESS_TOKEN")
    report = api(args.base_url, f"/apps/{args.app_id}/evidence-report", token)
    summary = report["summary"]
    lines = [
        "# Launch Circle pilot evidence",
        "",
        f"App: {summary['package_name']}",
        f"Candidate version code: {summary['candidate_version_code']}",
        f"Generated: {report['generated_at']}",
        "",
        "This report records observations; Google eligibility is not confirmed.",
        "",
        "## Summary",
        "",
    ]
    lines.extend(
        "    " + line for line in json.dumps(summary, ensure_ascii=False, indent=2).splitlines()
    )
    lines.extend(["", "## Recorded runs", ""])
    for run in report["runs"]:
        lines.extend(
            [
                f"### {run['id']}",
                "",
                (
                    f"Result: {run['result']}; source: {run['execution_source']}; "
                    f"version code: {run['version_code']}"
                ),
                "",
            ]
        )
        lines.extend(
            "    " + line
            for line in json.dumps(run["details"], ensure_ascii=False, indent=2).splitlines()
        )
        lines.append("")
    args.output_directory.mkdir(parents=True, exist_ok=True)
    for name, content in [
        ("evidence-report.json", json.dumps(report, ensure_ascii=False, indent=2)),
        ("evidence-report.md", "\n".join(lines)),
    ]:
        fd = os.open(args.output_directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
    print(
        json.dumps(
            {"report_directory": str(args.output_directory), "recorded_runs": len(report["runs"])}
        )
    )


if __name__ == "__main__":
    main()
