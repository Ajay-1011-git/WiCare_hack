"""LiveMockSource: polls backend/sensing_server (built in Prompts 1-2) and maps its
response into the canonical schema. Also doubles as a CLI smoke test:

    python -m backend.sensing.live_source --poll 5
"""

import argparse
import time
from typing import Any, Dict

import requests

from .base import SensingSource

DEFAULT_BASE_URL = "http://localhost:5001"


class LiveMockSource(SensingSource):
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 2.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def poll(self) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/api/v1/sensing/latest", timeout=self.timeout
        )
        response.raise_for_status()
        return self._map(response.json())

    @staticmethod
    def _map(payload: Dict[str, Any]) -> Dict[str, Any]:
        # sensing_server already emits the canonical schema directly, so this is close
        # to 1:1. Kept as an explicit field-by-field step (rather than returning
        # payload as-is) so LiveHardwareSource has an obvious equivalent to fill in
        # once it's mapping raw CSI-pipeline output instead of an already-canonical
        # JSON body.
        return {
            "breathing_rate_bpm": payload["breathing_rate_bpm"],
            "motion_index": payload["motion_index"],
            "sleep_fragmentation_index": payload["sleep_fragmentation_index"],
            "sleep_onset_latency": payload["sleep_onset_latency"],
            "presence_confidence": payload["presence_confidence"],
            "heart_rate_bpm": payload.get("heart_rate_bpm"),
            "source": payload["source"],
        }


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Poll LiveMockSource N times, printing mapped canonical-schema dicts."
    )
    parser.add_argument("--poll", type=int, default=5, help="Number of polls to perform")
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="sensing_server base URL"
    )
    parser.add_argument(
        "--interval", type=float, default=1.0, help="Seconds to sleep between polls"
    )
    args = parser.parse_args()

    source = LiveMockSource(base_url=args.base_url)
    for i in range(args.poll):
        print(source.poll())
        if i < args.poll - 1:
            time.sleep(args.interval)


if __name__ == "__main__":
    _main()
