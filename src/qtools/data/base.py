#!/usr/bin/env python3

from qcodes.dataset.experiment_container import Experiment as qcExperiment

from qtools.data.device import Design, Device, Sample, Wafer
from qtools.data.measurement import Experiment as metaExperiment
from qtools.data.measurement import MeasurementType


def create_metadata_device() -> Device:
    """
    Creates a test metadata structure and returns it.

    Returns:
        Device: Testdevice
    """
    wafer = Wafer.get_by_id("081b0ae8-e0e1-45f9-84e7-9779340343b4")
    sample = Sample.create("S4", "Testsample 4", wafer)
    design: Design = Design.get_by_id("7d333741-d52e-4237-aa31-66869f1bbcce")
    device = Device.create("Device6", design, sample)
    return device


def create_metadata_from_experiment(exp: qcExperiment = None) -> metaExperiment:
    """
    Creates the experiment metadata structure from QCoDeS.
    It is expected, that the experiment has been created/loaded in QCoDeS.

    Args:
        exp: QCoDeS experiment object.

    Returns:
        Experiment: Experiment metadata
    """
    name = exp.name if exp else ""
    desc = ""
    user = ""
    group = ""
    measurement_type = MeasurementType.load_from_db("pid")
    filters = ""
    return metaExperiment.create(name, desc, user, group, measurement_type, filters, [])
