from abc import ABC, abstractmethod
from typing import Any, Dict


class SensingSource(ABC):
    """Common interface for anything that produces vital-signs readings (02-trd.md
    section 6.3). Every implementation's poll() returns one reading in the canonical
    schema shape (02-trd.md section 3): breathing_rate_bpm (value + variability),
    motion_index, sleep_fragmentation_index, sleep_onset_latency, presence_confidence,
    heart_rate_bpm (nullable), and source. The feature extractor, classifier, and
    dashboard consume this shape identically regardless of which concrete source
    produced it -- that's what makes swapping sources a configuration change rather
    than a rewrite.
    """

    @abstractmethod
    def poll(self) -> Dict[str, Any]:
        """Return the latest reading, in the canonical schema shape."""
        raise NotImplementedError
