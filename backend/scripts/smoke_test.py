#!/usr/bin/env python3
"""Smoke test for the simulated sensing pipeline: sensing_server -> LiveMockSource ->
session_recorder -> JSON output. See /backend/README.md for the pipeline this
exercises.

Starts backend/sensing_server if it isn't already running, records a short session via
LiveMockSource + SessionRecorder, prints a summary, then exits cleanly (stopping the
server only if this script started it).

Usage:
    python backend/scripts/smoke_test.py [--duration 10] [--interval 2]
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SENSING_SERVER_DIR = REPO_ROOT / "backend" / "sensing_server"
SENSING_SERVER_VENV_PYTHON = SENSING_SERVER_DIR / "venv" / "bin" / "python"
BASE_URL = "http://localhost:5001"

sys.path.insert(0, str(REPO_ROOT))

import requests  # noqa: E402

from backend.sensing.live_source import LiveMockSource  # noqa: E402
from backend.sensing.session_recorder import SessionRecorder  # noqa: E402


def _server_is_up() -> bool:
    try:
        response = requests.get(f"{BASE_URL}/api/v1/vital-signs", timeout=1.0)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def _start_server() -> subprocess.Popen:
    python_bin = (
        str(SENSING_SERVER_VENV_PYTHON)
        if SENSING_SERVER_VENV_PYTHON.exists()
        else sys.executable
    )
    return subprocess.Popen(
        [python_bin, "app.py"],
        cwd=str(SENSING_SERVER_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_server(timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _server_is_up():
            return
        time.sleep(0.3)
    raise RuntimeError(f"sensing_server did not come up within {timeout}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--duration", type=float, default=10.0, help="Seconds to record for"
    )
    parser.add_argument(
        "--interval", type=float, default=2.0, help="Seconds between polls"
    )
    args = parser.parse_args()

    started_server = False
    server_proc = None

    if _server_is_up():
        print(f"sensing_server already running at {BASE_URL}, using it.")
    else:
        print(f"sensing_server not running -- starting it from {SENSING_SERVER_DIR} ...")
        server_proc = _start_server()
        started_server = True
        _wait_for_server()
        print("sensing_server is up.")

    try:
        source = LiveMockSource(base_url=BASE_URL)
        session_id = f"smoketest-{time.strftime('%Y%m%dT%H%M%S')}"
        recorder = SessionRecorder(session_id=session_id)

        print(
            f"Recording session '{session_id}' for {args.duration}s "
            f"(every {args.interval}s) ..."
        )
        deadline = time.time() + args.duration
        last_reading = None
        count = 0
        while time.time() < deadline:
            last_reading = source.poll()
            recorder.record(last_reading)
            count += 1
            time.sleep(args.interval)

        if last_reading is None:
            raise RuntimeError("No readings were recorded -- duration too short?")

        derived = recorder.compute_derived_features()

        print("\n--- Smoke test summary ---")
        print(f"Session ID:       {recorder.session_id}")
        print(f"Records written:  {count}")
        print(f"Session file:     {recorder.session_file}")
        print(f"Last raw reading: {json.dumps(last_reading)}")
        print(f"Derived features: {json.dumps(derived)}")
        print(f"source field:     {last_reading['source']!r} (must always be 'mock' here)")

        if last_reading["source"] != "mock":
            raise RuntimeError(
                f"Expected source='mock' from the mock sensing_server, got "
                f"{last_reading['source']!r} instead -- never hide/drop this field."
            )

        print("Smoke test OK.")
    finally:
        if started_server and server_proc is not None:
            print("Stopping sensing_server (this script started it) ...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
                server_proc.wait()
            print("sensing_server stopped.")


if __name__ == "__main__":
    main()
