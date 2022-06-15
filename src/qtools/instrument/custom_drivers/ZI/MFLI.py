# -*- coding: utf-8 -*-
"""
Created on Mon May 16 16:42:39 2022

@author: lab
MFLI driver for zhinst-toolkit version 0.3.3 (and above)
"""

import numpy as np
import qcodes as qc
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import ParameterWithSetpoints, Parameter, ParamRawDataType
#import qtools as qt
from zhinst.toolkit import Session
from qcodes.utils.validators import Arrays, ComplexNumbers, Enum, Ints, Numbers, Strings
from typing import Any, MutableMapping, MutableSequence, Union#

class MFLI(Instrument):
    """
    Driver for the Zurich-Instruments lockin based on the zhinst.toolkit driver.
    Adds proper parameters with get and set commands to make the MFLI usable
    with QTools.
    Not finished, most parameters are still missing.
    """
    def __init__(self, name: str, device: str, serverhost: str = "localhost",
                 existing_session: Session = None, **kwargs):
        super().__init__(name, **kwargs)
        if type(existing_session) == Session:
            session = existing_session
        else:
            self.session = session = Session(serverhost)
        self.instr = instr = session.connect_device(device)
        if instr._device_type != "MFLI":
            raise TypeError("The type of instrument you are trying to connect is not supported.")
        
        #self.daq = tk_mfli.DAQModule(self.instr)
        demod0 = self.instr.demods[0]
            
        self.add_parameter(
            "current",
            label = "R",
            unit = "A",
            get_cmd = lambda: np.sqrt(demod0.sample()["x"]**2+demod0.sample()["y"]**2) * np.sqrt(2),
            get_parser = float,
            set_cmd = None,
            docstring = "Absolute current as measured by demod0",
            )
        self.current.signal_name = ("demod0", "r")
        self.add_parameter(
            "current_x_component",
            label = "X",
            unit = "A",
            get_cmd = lambda: demod0.sample()["x"],
            get_parser = float,
            set_cmd = None,
            docstring = "X component of sample measured by demod1"
            )
        self.current_x_component.signal_name = ("demod0", "x")
        
        self.add_parameter(
            name = "phase",
            label = "Phase",
            unit = "rad",
            get_cmd = lambda: demod0.sample()["phase"],
            get_parser = float,
            set_cmd = None,
            docstring = "Phase of the measured current in radians"
            )
        
        self.add_parameter(
            "current_y_component",
            label = "Y",
            unit = "A",
            get_cmd = lambda: demod0.sample()["y"],
            get_parser = float,
            set_cmd = None,
            docstring = "X component of sample measured by demod1")
        self.current_y_component.signal_name = ("demod0", "y")

        self.add_parameter(
            name = "frequency",
            label = "Frequency",
            unit = "Hz",
            get_cmd = lambda: demod0.sample()["frequency"],
            get_parser = float,
            set_cmd = lambda f: self.instr.oscs[0].freq(f),
            docstring = "Frequency of the oscillator"
            )

        self.add_parameter(
            name = "amplitude",
            label = "Amplitude",
            unit = "V",
            get_cmd = lambda : self.instr.sigouts[0].amplitudes[1](),
            get_parser = float,
            set_cmd = lambda a: self.instr.sigouts[0].amplitudes[1](a),
            docstring = "Amplitude of the voltage output"
            )

        self.add_parameter(
            name = "output_enabled",
            label = "Output Enabled",
            get_cmd = lambda: self.instr.sigouts[0].on,
            get_parser = lambda x: int(bool(x)),
            set_cmd = lambda x: self.instr.sigouts[0].on(x),
            docstring = "Turns Output1 on or off"
            )
        
        self.add_parameter(
            name = "output_range",
            label = "Output range",
            unit = "V",
            get_cmd = lambda: self.instr.sigouts[0].range(),
            set_cmd = lambda x: self.instr.sigouts[0].range(x),
            docstring = "Range of the output"
            )

        self.add_parameter(
            name = "demod0_time_constant",
            label="Time constant",
            unit = "s",
            get_cmd = lambda : demod0.timeconstant(),
            get_parser = float,
            set_cmd = lambda t: self.instr.demods[0].timeconstant(t),
            docstring = "Time constant of the low-pass filter of demod0"
            )
        
        self.add_parameter(
            name = "demod0_order",
            label = "Demod0 filter order",
            get_cmd = lambda : demod0.order(),
            set_cmd = lambda x: demod0.order(x),
            docstring = "Gets/Sets the order of the demod 0 filter."
            )
        
            

        
        
        # self.add_parameter(
        #     parameter_class= ChannelBuffer,
        #     channel = 0,
        #     name = "demod_buffer",
        #     vals = Arrays(shape = (1,))
        #     )
        # self.add_parameter(
        #     'buffer_npts',
        #     label = 'Buffer number of points',
        #     unit = '',
        #     # set_cmd = self.daq.grid_cols,
        #     # get_cmd = self.daq.grid_cols
        #     )
        # self.add_parameter(
        #     'buffer_SR',
        #     label='Buffer sample rate',
        #     get_cmd= self.instr.nodetree.demods[0].rate,
        #     set_cmd=self.instr.nodetree.demods[0].rate,
        #     unit='Hz',
        #     vals=Numbers(min_value=1, max_value=857.1e3)
        #     )

                           
        
# class ChannelBuffer(ParameterWithSetpoints):
#     """
#     Parameter class for the two channel buffers

#     Currently always returns the entire buffer
#     TODO (WilliamHPNielsen): Make it possible to query parts of the buffer.
#     The instrument natively supports this in its TRCL call.
#     """

#     def __init__(self, name: str, instrument: 'MFLI', channel: int, **kwargs) -> None:
#         """
#         Args:
#             name: The name of the parameter
#             instrument: The parent instrument
#             channel: The relevant channel (1 or 2). The name should
#                 should match this.
#         """
#         self._valid_channels = (0, 1)

#         if channel not in self._valid_channels:
#             raise ValueError('Invalid channel specifier. SR830 only has '
#                               'channels 1 and 2.')

#         if not isinstance(instrument, MFLI):
#             raise ValueError('Invalid parent instrument. ChannelBuffer '
#                               'can only live on an SR830.')

#         super().__init__(
#             name,
#             #shape=(1,),  # dummy initial shape
#             unit="V",  # dummy initial unit
#             #setpoint_names=("Time",),
#             #setpoint_labels=("Time",),
#             #setpoint_units=("s",),
#             docstring="Holds an acquired (part of the) data buffer of one channel.",
#             instrument=instrument,
#             **kwargs
#         )

#         self.channel = channel

#     def prepare_buffer_readout(self, 
#                                parameters : list[Parameter],
#                                ) -> None:
#         """
#         Function to generate the setpoints for the channel buffer and
#         get the right units
#         """
#         assert isinstance(self.instrument, MFLI)
#         N = self.instrument.buffer_npts.get()  # problem if this is zero?
#         # TODO (WilliamHPNielsen): what if SR was changed during acquisition?
#         SR = self.instrument.buffer_SR.get()
#         if SR == 'Trigger':
#             self.setpoint_units = ('',)
#             self.setpoint_names = ('trig_events',)
#             self.setpoint_labels = ('Trigger event number',)
#             self.setpoints = (tuple(np.arange(0, N)),)
#         else:
#             dt = 1/SR
#             self.setpoint_units = ('s',)
#             self.setpoint_names = ('Time',)
#             self.setpoint_labels = ('Time',)
#             self.setpoints = (tuple(np.linspace(0, N*dt, N)),)

#         self.shape = (N,)

#         params = self.instrument.parameters
#         #We have to use the daq module here
#         #Adding parameters that shall be measured to daq buffer
#         for param in params:
#             if param.signal_name[1] in self.instrument.daq.signals_list(param.signal_name[0]):
#                 self.instrument.daq.add_signals(*param.signal_name)
#             else:
#                 raise Exception()
#         #!TODO: Replace generic Exception (parameter is no valid signal)
#         # YES, it should be: comparing to the string 'none' and not
#         # the None literal
#         if params[f'ch{self.channel}_ratio'].get() != 'none':
#             self.unit = '%'
#         else:
#             disp = params[f'ch{self.channel}_display'].get()
#             if disp == 'Phase':
#                 self.unit = 'deg'
#             else:
#                 self.unit = 'V'

#         if self.channel == 1:
#             self.instrument._buffer1_ready = True
#         else:
#             self.instrument._buffer2_ready = True
    
#     def start_measurement(self):
#         self.instrument.daq.measure()
        
#     def get_raw(self):
#         return self.instrument.daq.results

#     # def get_raw(self) -> ParamRawDataType:
#     #     """
#     #     Get command. Returns numpy array
#     #     """
#     #     assert isinstance(self.instrument, MFLI)
#     #     if self.channel == 0:
#     #         ready = self.instrument._buffer1_ready
#     #     else:
#     #         ready = self.instrument._buffer2_ready

#     #     if not ready:
#     #         raise RuntimeError('Buffer not ready. Please run '
#     #                             'prepare_buffer_readout')
#     #     N = self.instrument.buffer_npts()
#     #     if N == 0:
#     #         raise ValueError('No points stored in SR830 data buffer.'
#     #                           ' Can not poll anything.')

#     #     # poll raw binary data
#     #     self.instrument.write(f"TRCL ? {self.channel}, 0, {N}")
#     #     rawdata = self.instrument.visa_handle.read_raw()

#     #     # parse it
#     #     realdata = np.frombuffer(rawdata, dtype="<i2")
#     #     numbers = realdata[::2] * 2.0 ** (realdata[1::2] - 124)
#     #     if self.shape[0] != N:
#     #         raise RuntimeError(
#     #             f"SR830 got {N} points in buffer expected {self.shape[0]}"
#     #         )
#     #     return numbers
        
        
        