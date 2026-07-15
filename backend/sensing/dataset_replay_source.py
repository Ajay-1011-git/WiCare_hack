from typing import Any, Dict

from .base import SensingSource


class DatasetReplaySource(SensingSource):
    """Reserved for the later Sleep-EDF SC + CAP batch pipeline (02-trd.md sections 1
    and 4): EDF parsing, per-epoch feature extraction, ground-truth validation against
    hypnograms, cached to Parquet/JSON, then streamed here at the schema's cadence.

    TODO(dataset-pipeline): that pipeline does not exist yet -- no EDF parsing, no
    cached feature files, nothing to replay. Do not implement poll()'s internals until
    it does. This class is a stub only, matching the SensingSource shape so the rest of
    the architecture (feature extractor, classifier, dashboard) can already be wired
    against it.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "DatasetReplaySource is a stub -- the Sleep-EDF SC/CAP feature-extraction "
            "pipeline (02-trd.md section 4) has not been built yet. See this class's "
            "docstring."
        )

    def poll(self) -> Dict[str, Any]:
        raise NotImplementedError(
            "DatasetReplaySource is a stub -- the Sleep-EDF SC/CAP feature-extraction "
            "pipeline (02-trd.md section 4) has not been built yet. See this class's "
            "docstring."
        )
