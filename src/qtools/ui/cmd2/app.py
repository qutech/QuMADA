import inspect

from cmd2 import Cmd
from qcodes import Station

import qtools.data.db as db
from qtools.data.metadata import Metadata
from qtools.instrument.instrument import is_instrument
from qtools.measurement.measurement import is_measurement_script
from qtools.ui.cmd2.parsers import (
    InstrumentCommandSet,
    MeasurementCommandSet,
    MetadataCommandSet,
)
from qtools.utils.import_submodules import import_submodules
from qtools.utils.resources import import_resources


class QToolsApp(Cmd):
    def __init__(self):
        super().__init__()

        # remove cmd2 builtin commands
        del Cmd.do_edit
        del Cmd.do_shell
        # hide cmd2 builtin commands
        self.hidden_commands.append("alias")
        self.hidden_commands.append("macro")
        self.hidden_commands.append("run_pyscript")
        self.hidden_commands.append("run_script")
        self.hidden_commands.append("shortcuts")

        # import instruments
        modules = import_submodules("qcodes.instrument_drivers")
        self.instrument_drivers = {}
        for _, module in modules.items():
            members = inspect.getmembers(module, is_instrument)
            self.instrument_drivers.update(members)

        # import mappings
        self.mappings = import_resources("qtools.instrument.mapping", "*.json")

        # import scripts
        modules = import_submodules("qtools.measurement.scripts")
        self.measurement_scripts = {}
        for _, module in modules.items():
            members = inspect.getmembers(module, is_measurement_script)
            self.measurement_scripts.update(members)

        # Metadata
        db.api_url = "http://134.61.7.48:9123"
        self.metadata = Metadata()
        self.station = Station()
