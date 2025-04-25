# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Till Huckeman


import sys
from subprocess import Popen

from qcodes.monitor.monitor import Monitor
from qcodes.station import Station

from qumada.instrument.mapping.base import filter_flatten_parameters
from qumada.measurement.measurement import MeasurementScript


def open_web_gui(parameters):
    """
    Opens Gui from qcodes.monitor.monitor
    parameters: Provides the parameters to display. Has to be Station object,
    QuMADA MeasurementScript object or list of qcodes parameters.
    When a station object is used, all parameters of all components are shown.
    """
    if isinstance(parameters, Station):
        params = [val for val in filter_flatten_parameters(parameters.components).values()]
    elif isinstance(parameters, MeasurementScript):
        params = []
        try:
            channels = [val for val in parameters.gate_parameters.values()]
        except Exception:
            print("Error not yet implemented. Maybe you forgot to do the mapping first?")
            return False
        for gate in channels:
            for item in gate.values():
                params.append(item)
    elif isinstance(parameters, list):
        params = parameters
    else:
        print(
            "The provided parameters are invalid. Please pass as Station \
              object, a Measurement Script (after parameter mapping) or a \
              list of parameters"
        )
        return False
    monitor_process = Popen([sys.executable, "-m", "qcodes.monitor.monitor"], shell=True)
    monitor = Monitor(*params)
    return monitor, monitor_process
