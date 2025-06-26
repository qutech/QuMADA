import dataclasses
import itertools

import numpy as np
import pytest

from qumada.measurement.device_object import QumadaDevice

from .conftest import MeasurementTestSetup


@dataclasses.dataclass
class DeviceTestSetup:
    measurement_test_setup: MeasurementTestSetup
    device: QumadaDevice
    parameters: dict
    namespace: dict


@pytest.fixture
def device_test_setup(measurement_test_setup):
    """This fixture is derived from device_object_example"""

    parameters = {
        "ohmic": {
            "current": {"type": "gettable"},
        },
        "gate1": {"voltage": {"type": "static"}},
        "gate2": {"voltage": {"type": "static"}},
    }
    namespace = {}
    device = QumadaDevice.create_from_dict(parameters, station=measurement_test_setup.station, namespace=namespace)

    buffer_settings = {
        "sampling_rate": 512,
        "num_points": 12,
        "delay": 0,
    }

    mapping = {
        "ohmic": {
            "current": measurement_test_setup.dmm.current,
        },
        "gate1": {
            "voltage": measurement_test_setup.dac.ch01.voltage,
        },
        "gate2": {
            "voltage": measurement_test_setup.dac.ch02.voltage,
        },
    }

    # This tells a measurement script how to start a buffered measurement.
    # "Hardware" means that you want to use a hardware trigger. To start a measurement,
    # the method provided as "trigger_start" is called. The "trigger_reset" method is called
    # at the end of each buffered line, in our case resetting the trigger flag.
    # For real instruments, you might have to define a method that sets the output of your instrument
    # to a desired value as "trigger_start". For details on other ways to setup your triggers,
    # check the documentation.

    buffer_script_settings = {
        "trigger_type": "hardware",
        "trigger_start": measurement_test_setup.trigger.set,
        "trigger_reset": measurement_test_setup.trigger.clear,
    }

    device.buffer_script_setup = buffer_script_settings
    device.buffer_settings = buffer_settings

    # device.map_terminals()
    #  - map_terminals_gui(self.station.components, self.instrument_parameters, instrument_parameters)
    device.terminal_parameters = mapping
    #  - self.update_terminal_parameters()
    device.update_terminal_parameters()

    # device.map_triggers()
    measurement_test_setup.dac._qumada_mapping.trigger_in = None
    (measurement_test_setup.dmm._qumada_buffer.trigger,) = measurement_test_setup.dmm._qumada_buffer.AVAILABLE_TRIGGERS

    return DeviceTestSetup(
        measurement_test_setup,
        device,
        parameters,
        namespace,
    )


@pytest.mark.parametrize(
    "buffered,backsweep",
    itertools.product(
        # buffered
        [True, False],
        # backsweep
        [False, True],
    ),
)
def test_measured_ramp(device_test_setup, buffered, backsweep):
    gate1 = device_test_setup.namespace["gate1"]

    plot_args = []

    def plot_backend(*args, **kwargs):
        plot_args.append((args, kwargs))

    from qumada.measurement.measurement import MeasurementScript

    MeasurementScript.DEFAULT_LIVE_PLOTTER = plot_backend

    (qcodes_data,) = gate1.voltage.measured_ramp(0.4, start=-0.3, buffered=buffered, backsweep=backsweep)
    if backsweep:
        assert gate1.voltage() == pytest.approx(-0.3, abs=0.001)
    else:
        assert gate1.voltage() == pytest.approx(0.4, abs=0.001)

    if not buffered:
        # TODO: Why is this necessary???
        (qcodes_data, _, _) = qcodes_data
    xarr = qcodes_data.to_xarray_dataset()

    set_points = xarr.dac_ch01_voltage.values

    if backsweep:
        fwd = np.linspace(-0.3, 0.4, len(set_points) // 2)
        expected = np.concatenate((fwd, fwd[::-1]))
    else:
        expected = np.linspace(-0.3, 0.4, len(set_points))

    if buffered:
        assert len(plot_args) == 1 + int(backsweep)
    else:
        assert len(plot_args) == len(set_points)

    np.testing.assert_almost_equal(expected, set_points)
