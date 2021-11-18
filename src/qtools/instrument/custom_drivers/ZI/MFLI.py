# -*- coding: utf-8 -*-
"""
Created on Fri Nov 12 13:59:11 2021

@author: lab
Workaround to make the MFLI Driver usable with QCoDeS
"""


import numpy as np
import qcodes as qc
from qcodes.instrument.base import Instrument
import qtools as qt
import zhinst.toolkit.control.drivers.mfli as tk_mfli



class MFLI(Instrument):
    """
    Driver for the Zurich-Instruments lockin based on the zhinst.toolkit driver.
    Adds proper parameters with get and set commands to make the MFLI usable
    with QTools. 
    Not finished, most parameters are still missing.
    """
    def __init__(self, name: str, device: str, **kwargs):
        super().__init__(name, **kwargs)
        self.instr = instr = tk_mfli.MFLI(name, device)
        instr.setup()
        instr.connect_device()
        
        self.add_parameter(
            "current",
            label = "R",
            unit = "A",
            get_cmd = self.instr.nodetree.demods[0].sample,
            get_parser = np.abs,
            set_cmd = None,
            docstring= "Absolute current as measured by demod1"
            )
        
        self.add_parameter(
            name = "phase",
            label = "Phase",
            unit = "rad",
            get_cmd = self.instr.nodetree.demods[0].sample,
            get_parser = np.angle,
            set_cmd = None,
            docstring = "Phase of the measured current in radians"
            )
        
        self.add_parameter(
            name = "amplitude",
            label = "Amplitude",
            unit = "V",
            get_cmd = self.instr.nodetree.sigout.amplitude,
            get_parser = float,
            set_cmd = self.instr.nodetree.sigout.amplitude,
            docstring = "Amplitude of the voltage output"
            )
        
        self.add_parameter(
            name = "frequency",
            label = "Frequency",
            unit = "Hz",
            get_cmd = self.instr.nodetree.osc.freq,
            get_parser = float,
            set_cmd = self.instr.nodetree.osc.freq,
            docstring = "Frequency of the oscillator"
            )
        
        self.add_parameter(
            name = "output_enabled",
            label = "Output Enabled",
            get_cmd = self.instr.nodetree.sigout.on,
            get_parser = bool,
            set_cmd = self.instr.nodetree.sigout.on,
            docstring = "Turns Output1 on or off"
            )
        
        
        