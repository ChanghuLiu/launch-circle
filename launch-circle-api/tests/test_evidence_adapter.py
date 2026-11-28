import json
import subprocess
import sys

import pytest

from scripts import submit_device_evidence as adapter


def args(tmp_path, extra=None):
    evidence = tmp_path / "observations.json"
    evidence.write_text(
        json.dumps(
            {
                "result": "PASS",
                "steps": [
                    {
                        "instruction": "Observed core step",
                        "expected": "Saved result",
                        "actual": "Saved result was observed",
                        "result": "PASS",
                    }
                ],
            }
        )
    )
    return [
        "submit_device_evidence.py",
        "--base-url",
        "http://127.0.0.1:8786",
        "--serial",
        "synthetic-device",
        "--mission-id",
        "synthetic-mission",
        "--package",
        "com.evidence.pilot",
        "--expected-version",
        "4",
        "--evidence-file",
        str(evidence),
        "--output",
        str(tmp_path / "request.json"),
        "--dry-run",
        *(extra or []),
    ]


def fake_adb(_serial, *command):
    if command == ("get-state",):
        return "device"
    if command[:3] == ("shell", "dumpsys", "package"):
        return "versionCode=4 minSdk=27"
    if command[-1] == "ro.product.model":
        return "Synthetic Device"
    if command[-1] == "ro.build.version.sdk":
        return "27"
    raise AssertionError(command)


def test_retry_uses_the_original_request_not_new_device_facts(tmp_path, monkeypatch):
    argv = args(tmp_path)
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(adapter, "adb", fake_adb)
    assert adapter.main() == 0
    first = (tmp_path / "request.json").read_text()
    monkeypatch.setattr(sys, "argv", [*argv, "--retry"])
    monkeypatch.setattr(adapter, "adb", lambda *_args: pytest.fail("Retry must not rerun ADB"))
    assert adapter.main() == 0
    assert (tmp_path / "request.json").read_text() == first


def test_device_failure_does_not_fabricate_a_version_or_create_a_run(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", args(tmp_path))

    def offline(*_args):
        raise subprocess.CalledProcessError(1, "adb")

    monkeypatch.setattr(adapter, "adb", offline)
    assert adapter.main() == 2
    assert not (tmp_path / "request.json").exists()


def test_wrong_build_is_blocked_even_when_observation_file_claims_pass(tmp_path, monkeypatch):
    argv = args(tmp_path)
    argv[argv.index("--expected-version") + 1] = "5"
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(adapter, "adb", fake_adb)
    assert adapter.main() == 0
    request = json.loads((tmp_path / "request.json").read_text())["request"]
    assert request["version_code"] == 4
    assert request["expected_version_code"] == 5
    assert request["result"] == "BLOCKED"
    assert all(step["result"] == "BLOCKED" for step in request["steps"])


def test_plain_http_remote_endpoint_rejected_before_reading_device_or_token(tmp_path, monkeypatch):
    argv = args(tmp_path)
    argv[argv.index("--base-url") + 1] = "http://example.com"
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as error:
        adapter.main()
    assert error.value.code == 2
