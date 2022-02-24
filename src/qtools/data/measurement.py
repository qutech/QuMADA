"""
Representations of domain objects (Measurements).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime as Datetime

from qtools.data.device import Device
from qtools.data.domain import DomainObject
from qtools.data.yaml import DomainYAMLObject


@dataclass
class MeasurementScript(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement script."""

    yaml_tag = "!MeasurementScript"

    language: str
    script: str

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls, name: str, language: str | None = None, script: str | None = None, **kwargs
    ) -> MeasurementScript:
        """Creates a MeasurementScript object."""
        kwargs.update(
            {
                "name": name,
                "language": language,
                "script": script,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementScript")


@dataclass
class MeasurementSettings(DomainObject, DomainYAMLObject):
    """Represents the database entry of the measurement settings."""

    yaml_tag = "!MeasurementSettings"

    settings: str

    @classmethod
    def create(
        cls, name: str, settings: str | None = None, **kwargs
    ) -> MeasurementSettings:
        """Creates a MeasurementSettings object."""
        kwargs.update(
            {
                "name": name,
                "settings": settings,
            }
        )
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[MeasurementSettings]:
        return super()._get_all(fn_name="measurementSettings")

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementSettings")


@dataclass
class MeasurementType(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement type."""

    yaml_tag = "!MeasurementType"

    extractableParameters: str  # pylint: disable=invalid-name
    scriptTemplates: list[MeasurementScript] = field(  # pylint: disable=invalid-name
        default_factory=list
    )

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        extractableParameters: str,
        scriptTemplates: list[MeasurementScript],
        **kwargs
    ) -> MeasurementType:
        """Creates a MeasurementType object."""
        kwargs.update(
            {
                "name": name,
                "extractableParameters": extractableParameters,
                "scriptTemplates": scriptTemplates,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementType")


@dataclass
class ExperimentSetup(DomainObject, DomainYAMLObject):
    """Represents the database entry of an experiment setup."""

    yaml_tag = "!ExperimentSetup"

    temperature: str
    instrumentsChannels: str  # pylint: disable=invalid-name
    standardSettings: str  # pylint: disable=invalid-name
    filters: str

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        temperature: str | None = None,
        instrumentsChannels: str | None = None,
        standardSettings: str | None = None,
        filters: str | None = None,
        **kwargs
    ) -> ExperimentSetup:
        """Creates an ExperimentSetup object."""
        kwargs.update(
            {
                "name": name,
                "temperature": temperature,
                "instrumentsChannels": instrumentsChannels,
                "standardSettings": standardSettings,
                "filters": filters,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateExperimentSetup")


@dataclass
class MeasurementMapping(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement mapping."""

    yaml_tag = "!MeasurementMapping"

    mapping: str

    @classmethod
    def create(
        cls,
        name: str,
        mapping: str | None = None,
        **kwargs,
    ) -> Measurement:
        """Creates an Measurement object."""
        kwargs.update(
            {
                "name": name,
                "mapping": mapping,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementMapping")


@dataclass
class MeasurementSeries(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement series."""

    yaml_tag = "!MeasurementSeries"

    measurements: list[Measurement] = field(default_factory=list)

    # TODO: Incorporate measurements
    @classmethod
    def create(
        cls,
        name: str,
        **kwargs,
    ) -> Measurement:
        """Creates an Measurement object."""
        kwargs.update(
            {
                "name": name,
            }
        )
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[MeasurementSeries]:
        return super()._get_all(fn_name="measurementSeries")

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementSeries")


@dataclass
class MeasurementData(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement data set."""

    yaml_tag = "!MeasurementMData"

    dataType: str  # pylint: disable=invalid-name
    pathToData: str  # pylint: disable=invalid-name

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        dataType: str,
        pathToData: str,
        **kwargs,
    ) -> Measurement:
        """Creates an Measurement object."""
        kwargs.update(
            {
                "name": name,
                "dataType": dataType,
                "pathToData": pathToData,
            }
        )
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[MeasurementData]:
        return super()._get_all(fn_name="measurementData")

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurementData")


@dataclass
class Measurement(DomainObject, DomainYAMLObject):
    """Represents the database entry of a measurement."""

    yaml_tag = "!Measurement"

    device: Device
    measurementType: MeasurementType  # pylint: disable=invalid-name
    settings: MeasurementSettings
    mapping: MeasurementMapping
    experimentSetup: ExperimentSetup  # pylint: disable=invalid-name
    script: MeasurementScript
    series: MeasurementSeries
    datetime: Datetime
    user: str
    valid: bool
    comments: str
    data: list[MeasurementData] = field(default_factory=list)

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        device: Device,
        measurementType: MeasurementType,
        settings: MeasurementSettings,
        mapping: MeasurementMapping,
        experimentSetup: ExperimentSetup,
        script: MeasurementScript,
        series: MeasurementSeries,
        datetime: Datetime,
        user: str,
        valid: bool,
        data: list[MeasurementData],
        comments: str | None = None,
        **kwargs
    ) -> Measurement:
        """Creates a Measurement object."""
        kwargs.update(
            {
                "name": name,
                "device": device,
                "measurementType": measurementType,
                "settings": settings,
                "mapping": mapping,
                "experimentSetup": experimentSetup,
                "script": script,
                "series": series,
                "datetime": datetime,
                "user": user,
                "valid": valid,
                "comments": comments,
                "data": data,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateMeasurement")


@dataclass
class Analysis(DomainObject, DomainYAMLObject):
    """Represents the database entry of an analysis."""

    yaml_tag = "!Analysis"

    method: str
    results: str
    script: str
    softwareFilter: str  # pylint: disable=invalid-name

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        method: str,
        results: str,
        script: str,
        softwareFilter: str,
        **kwargs,
    ) -> Analysis:
        """Creates an Analysis object"""
        kwargs.update(
            {
                "name": name,
                "method": method,
                "results": results,
                "script": script,
                "softwareFilter": softwareFilter,
            }
        )
        return super()._create(**kwargs)

    @classmethod
    def get_all(cls) -> list[Analysis]:
        return super()._get_all(fn_name="analysis")

    def save(self) -> str:
        return super()._save("saveOrUpdateAnalysis")


@dataclass
class AnalysisResult(DomainObject, DomainYAMLObject):
    """Represents the database entry of an analysis result."""

    yaml_tag = "!AnalysisResult"

    extractedParameters: str  # pylint: disable=invalid-name
    extractedValues: str  # pylint: disable=invalid-name
    analysis: Analysis
    measurement: Measurement

    # pylint: disable=invalid-name
    @classmethod
    def create(
        cls,
        name: str,
        extractedParameters: str,
        extractedValues: str,
        analysis: Analysis,
        measurement: Measurement,
        **kwargs,
    ) -> AnalysisResult:
        """Creates an Analysis object"""
        kwargs.update(
            {
                "name": name,
                "extractedParameters": extractedParameters,
                "extractedValues": extractedValues,
                "analysis": analysis,
                "measurement": measurement,
            }
        )
        return super()._create(**kwargs)

    def save(self) -> str:
        return super()._save("saveOrUpdateAnalysisResult")
