from __future__ import annotations

from qtools.data.metadata import Metadata
from qtools.measurement.measurement import MeasurementScript


class Job:
    def __init__(
        self,
        metadata: Metadata | None = None,
        script: MeasurementScript | None = None,
        parameters: dict | None = None,
    ):
        self._metadata: Metadata = metadata or Metadata()
        self._script: MeasurementScript = script
        self._parameters: dict = parameters or {}
