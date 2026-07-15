from typing import Any, Dict

from .base import SensingSource
from .live_source import DEFAULT_BASE_URL


class LiveHardwareSource(SensingSource):
    """Reserved for the real ESP32-CSI hardware sensing source (02-trd.md sections 6.1
    and 7). No hardware exists in-hand yet -- every method below raises
    NotImplementedError until it does. This docstring is the full spec for what each
    method will do once it's filled in; per 02-trd.md section 6.3, filling in these
    method bodies is meant to be the *entire* integration task -- nothing else in the
    codebase (feature extractor, classifier, dashboard) should need to change.

    Hardware/software path (02-trd.md section 7):
      - Two ESP32 WROOM-32E boards, one flashed with Espressif's official `esp-csi`
        `csi_send` example (transmitter), one with `csi_recv` (receiver).
      - __init__ will open/manage whatever transport exposes the receiver's CSI frame
        stream (e.g. its serial port or a small local relay process) instead of an
        HTTP base_url -- the constructor keeps the same signature as LiveMockSource for
        interface symmetry, but `base_url` is expected to be repurposed into that
        transport's address once the real transport is chosen.
      - poll() will read the latest raw CSI amplitude frames from that receiver and run
        them through the Pulse-Fi-style processing pipeline (UC Santa Cruz methodology,
        via its open community replication github.com/nickbild/csi_hr): amplitude
        conversion, noise removal, pulse extraction/shaping, segmentation, then a small
        LSTM for heart_rate_bpm; simpler bandpass + peak detection for
        breathing_rate_bpm and motion_index. It will return the same canonical schema
        shape as LiveMockSource.poll(), with "source": "esp32_csi" instead of "mock".
      - heart_rate_bpm is the hardest field here (needs the MAX30102 calibration step
        and a trained model) and is treated as a stretch goal, not a blocking
        dependency, per the implementation plan -- poll() may return
        heart_rate_bpm: None until that calibration/model work is done, same as the
        mock server did before Prompt 2 added simulated values.
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 2.0) -> None:
        raise NotImplementedError(
            "LiveHardwareSource.__init__ is not implemented -- no ESP32 hardware "
            "exists in-hand yet (02-trd.md section 7). See this class's docstring for "
            "what it will do once hardware arrives."
        )

    def poll(self) -> Dict[str, Any]:
        raise NotImplementedError(
            "LiveHardwareSource.poll is not implemented -- requires the ESP32 esp-csi "
            "transmit/receive setup and the Pulse-Fi-style processing pipeline "
            "(02-trd.md section 7). See this class's docstring for what it will do "
            "once hardware arrives."
        )
