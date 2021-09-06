#!/usr/bin/env python3


from qtools.data.device import Wafer, Device, Sample, Design


def create_metadata_device() -> Device:
    """
    Creates a test metadata structure and returns it.

    Returns:
        Device: Testdevice
    """
    wafer = Wafer.load_from_db("081b0ae8-e0e1-45f9-84e7-9779340343b4")
    sample = Sample.create("S4", "Testsample 4", wafer)
    design = Design.load_from_db("7d333741-d52e-4237-aa31-66869f1bbcce")
    device = Device.create("Device6", design, sample)
    return device
