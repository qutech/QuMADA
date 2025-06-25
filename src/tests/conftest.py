import dataclasses
import pathlib
import tempfile
import threading
import time

import pytest
from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.station import Station

from qumada.instrument.buffered_instruments import BufferedDummyDMM as DummyDmm
from qumada.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
from qumada.instrument.mapping import (
    DUMMY_DMM_MAPPING,
    add_mapping_to_instrument,
)
from qumada.instrument.mapping.Dummies.DummyDac import DummyDacMapping
from qumada.utils.load_from_sqlite_db import load_db


@dataclasses.dataclass
class MeasurementTestSetup:
    trigger: threading.Event

    station: Station
    dmm: DummyDmm
    dac: DummyDac

    db_path: pathlib.Path


@pytest.fixture
def measurement_test_setup(tmp_path):
    trigger = threading.Event()

    # Setup qcodes station
    station = Station()

    # The dummy instruments have a trigger_event attribute as replacement for
    # the trigger inputs of real instruments.

    dmm = DummyDmm("dmm", trigger_event=trigger)
    add_mapping_to_instrument(dmm, mapping=DUMMY_DMM_MAPPING)
    station.add_component(dmm)

    dac = DummyDac("dac", trigger_event=trigger)
    add_mapping_to_instrument(dac, mapping=DummyDacMapping())
    station.add_component(dac)

    db_path = tmp_path / "test.db"
    load_db(str(db_path))
    load_or_create_experiment("test", "dummy_sample")

    yield MeasurementTestSetup(trigger, station, dmm, dac, db_path)
    station.close_all_registered_instruments()
