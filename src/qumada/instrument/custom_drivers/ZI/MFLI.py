# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - 4K User
# - Daniel Grothe
# - Sionludi Lab
# - Till Huckeman
# - Tobias Hangleiter


"""
MFLI driver for zhinst-toolkit version 0.3.3 (and above)
"""

import numpy as np
from qcodes.instrument import Instrument

# import QuMADA as qt
from zhinst.toolkit import Session


class MFLI(Instrument):
    """
    Driver for the Zurich-Instruments lockin based on the zhinst.toolkit driver.
    Adds proper parameters with get and set commands to make the MFLI usable
    with QuMADA.
    Not finished, most parameters are still missing.
    """

    def __init__(
        self, name: str, device: str, serverhost: str = "localhost", existing_session: Session = None, **kwargs
    ):
        super().__init__(name, **kwargs)
        if type(existing_session) == Session:
            session = existing_session
        else:
            self.session = session = Session(serverhost)
        self.instr = instr = session.connect_device(device)
        if instr._device_type != "MFLI":
            raise TypeError("The type of instrument you are trying to connect is not supported.")

        # self.daq = tk_mfli.DAQModule(self.instr)
        demod0 = self.instr.demods[0]

        self.add_parameter(
            "voltage",
            label="V",
            unit="V",
            get_cmd=lambda: np.sqrt(demod0.sample()["x"] ** 2 + demod0.sample()["y"] ** 2) * np.sqrt(2),
            get_parser=float,
            set_cmd=False,
            docstring="Absolute voltage as measured by demod0",
        )
        
        self.voltage.signal_name = ("demod0", "r")
        
        self.add_parameter(
            "voltage_offset",
            label="Voltage Offset",
            unit="V",
            get_cmd=lambda: self.instr.sigouts[0].offset(),
            get_parser=float,
            set_cmd=lambda x: self.instr.sigouts[0].offset(x),
            docstring="Offset to voltage output in V",
        )

        
        self.add_parameter(
            "voltage_y_component",
            label="Y",
            unit="V",
            get_cmd=lambda: demod0.sample()["y"],
            get_parser=float,
            set_cmd=None,
            docstring="X component of sample measured by demod1",
        )
        self.voltage_y_component.signal_name = ("demod0", "y")

        
        self.add_parameter(
            "voltage_x_component",
            label="X",
            unit="V",
            get_cmd=lambda: demod0.sample()["y"],
            get_parser=float,
            set_cmd=None,
            docstring="X component of sample measured by demod1",
        )
        self.voltage_x_component.signal_name = ("demod0", "x")
        
        
        self.add_parameter(
            "current",
            label="R",
            unit="A",
            get_cmd=lambda: np.sqrt(demod0.sample()["x"] ** 2 + demod0.sample()["y"] ** 2) * np.sqrt(2),
            get_parser=float,
            set_cmd=None,
            docstring="Absolute current as measured by demod0",
        )
        self.current.signal_name = ("demod0", "r")
        self.add_parameter(
            "current_x_component",
            label="X",
            unit="A",
            get_cmd=lambda: demod0.sample()["x"],
            get_parser=float,
            set_cmd=None,
            docstring="X component of sample measured by demod1",
        )
        self.current_x_component.signal_name = ("demod0", "x")

        self.add_parameter(
            name="phase",
            label="Phase",
            unit="rad",
            get_cmd=lambda: demod0.sample()["phase"],
            get_parser=float,
            set_cmd=None,
            docstring="Phase of the measured current in radians",
        )
        self.phase.signal_name = ("demod0", "phase")
        self.add_parameter(
            "current_y_component",
            label="Y",
            unit="A",
            get_cmd=lambda: demod0.sample()["y"],
            get_parser=float,
            set_cmd=None,
            docstring="X component of sample measured by demod1",
        )
        self.current_y_component.signal_name = ("demod0", "y")

        self.add_parameter(
            name="frequency",
            label="Frequency",
            unit="Hz",
            get_cmd=lambda: demod0.sample()["frequency"],
            get_parser=float,
            set_cmd=lambda f: self.instr.oscs[0].freq(f),
            docstring="Frequency of the oscillator",
        )

        self.add_parameter(
            name="amplitude",
            label="Amplitude",
            unit="V",
            get_cmd=lambda: self.instr.sigouts[0].amplitudes[1](),
            get_parser=float,
            set_cmd=lambda a: self.instr.sigouts[0].amplitudes[1](a),
            docstring="Amplitude of the voltage output",
        )
        #self.amplitude.signal_name = ("demod0", "y")

        # self.add_parameter(
        #     name = "output_enabled",
        #     label = "Output Enabled",
        #     get_cmd = lambda: self.instr.sigouts[0].on,
        #     get_parser = lambda x: int(bool(x)),
        #     set_cmd = lambda x: self.instr.sigouts[0].on(x),
        #     set_parser = int,
        #     get_parser = bool,
        #     docstring = "Turns Output1 on or off"
        #     )

        self.add_parameter(
            name="output_range",
            label="Output range",
            unit="V",
            get_cmd=lambda: self.instr.sigouts[0].range(),
            set_cmd=lambda x: self.instr.sigouts[0].range(x),
            docstring="Range of the output",
        )

        self.add_parameter(
            name="demod0_time_constant",
            label="Time constant",
            unit="s",
            get_cmd=lambda: demod0.timeconstant(),
            get_parser=float,
            set_cmd=lambda t: self.instr.demods[0].timeconstant(t),
            docstring="Time constant of the low-pass filter of demod0",
        )

        self.add_parameter(
            name="demod0_order",
            label="Demod0 filter order",
            get_cmd=lambda: demod0.order(),
            set_cmd=lambda x: demod0.order(x),
            docstring="Gets/Sets the order of the demod 0 filter.",
        )

        self.add_parameter(
            name="demod0_aux_in_1",
            label="Demod0 AuxIn 1",
            get_cmd=lambda: demod0.sample()["auxin0"],
            set_cmd=None,
            get_parser=float,
            docstring="Aux In 1 of demod0",
        )
        self.demod0_aux_in_1.signal_name = ("demod0", "auxin0")

        self.add_parameter(
            name="demod0_aux_in_2",
            label="Demod0 AuxIn 2",
            get_cmd=lambda: demod0.sample()["auxin1"],
            set_cmd=None,
            get_parser=float,
            docstring="Aux In 2 of demod0",
        )
        self.demod0_aux_in_2.signal_name = ("demod0", "auxin1")
        self.add_parameter(
            name="demod0_trig_in",
            label="Demod0 Trigger Input",
            get_cmd=None,
            set_cmd=None,
            docstring="Gets/Sets the order of the demod 0 filter.",
        )
