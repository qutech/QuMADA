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
# - Till Huckeman

from time import sleep
import logging
import numpy as np

from qcodes.dataset.measurements import Measurement
from qcodes.parameters.specialized_parameters import ElapsedTimeParameter
from qcodes.parameters.parameter import Parameter

from qtools.measurement.measurement import MeasurementScript
from qtools.utils.ramp_parameter import ramp_or_set_parameter
from qtools.utils.utils import _validate_mapping, naming_helper
from qtools.instrument.buffers.buffer import is_bufferable

from qutil.measurement.spectrometer import Spectrometer, daq

class Measure_Spectrum(MeasurementScript):
    """
    kwargs:
        store_timetrace: Bool|True. Stores timetrace as QCoDeS measurement
        store_spectrum: Bool|True:. Stores spectrum as QCoDes measurement
    """
    def run(self) -> list:
        self.initialize()
        naming_helper(self, default_name="Spectrum")
        settings = self.settings
        store_timetrace = settings.get("store_timetrace", True)
        store_spectrum = settings.get("store_spectrum", True)
        module = settings.get("module", "scope" )
        

        #TODO: Check if instrument is supported
        #TODO: Cases for different instruments/modes

        if len(self.gettable_channels) != 1:
            raise AssertionError("For this type of measurement exactly 1 gettable channel is required!")
        instrument = self.gettable_channels[0].root_instrument
        
        # static_gettables = []
        # del_channels = []
        # del_params = []
        # for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
        #     if channel in self.static_channels:
        #         del_channels.append(channel)
        #         del_params.append(parameter)
        #         meas.register_parameter(
        #             channel,
        #             setpoints=[timer,]
        #             )
        #         parameter_value = self.properties[
        #             parameter["gate"]][parameter["parameter"]]["value"]
        #         static_gettables.append(
        #             (channel, 
        #               [parameter_value for _ in range(self.getnumberofpointshere)]
        #               )
        #             )
        # for channel in del_channels:
        #     self.gettable_channels.remove(channel)
        # for param in del_params:
        #     self.gettable_parameters.remove(param)
        # for parameter in self.static_channels:
        #     if parameter in self.gettable_channels:
        #         self.gettable_channels.remove(parameter)                
        #         static_gettables.append(parameter, parameter.)
        

        if settings.get("module", "scope"):
            setup, acquire = daq.zhinst.MFLI_scope(instrument.instr.session, instrument.instr)
        else:
            setup, acquire = daq.zhinst.MFLI_daq(instrument.instr.session, instrument.instr)
        
        try: 
            self.spectrometer = settings.pop("spectrometer")
        except KeyError:
            self.spectrometer = Spectrometer(setup, acquire)
        self.spectrometer.take(self.measurement_name, **settings)
        results=self.spectrometer[-1]
        if store_timetrace:
            self._save_data_to_db(results=results,
                             data_type="timetrace")
        if store_spectrum:
            self._save_data_to_db(results=results,
                             data_type="spectrum")
        return self.spectrometer
    
    def _save_data_to_db(self, 
                         results: dict,
                         data_type: str,
                         ):
        measurement = Measurement(name=f"{self.measurement_name} {data_type}")

        match data_type:    
            case "spectrum":
                frequency = Parameter("frequency",
                                      label = "f",
                                      unit = "Hz")
                independent_param = frequency
                #TODO: Adjust unit/Name to settings
                signal = Parameter("signal",
                                   label = "$\sqrt{S}$",
                                   unit = "$V/\sqrt{Hz}$")
                dependent_param = signal
                
                x = results["f_processed"]
                y = results["S_processed"][0]
            case "timetrace":
                timer = ElapsedTimeParameter("time")
                independent_param = timer
                dependent_param = self.gettable_channels[0]
                #TODO: n_pts is not correct?
                x = np.arange(len(results["timetrace_raw"][0])) / results['settings'].fs
                y = results["timetrace_raw"][0]
            case _:
                raise NameError(f"{data_type} is no valid data_type!")
            
        # for parameter in [*self.gettable_channels]:#, *self.dynamic_channels]:
        #     measurement.register_parameter(
        #         parameter,
        #         setpoints=[
        #             independent_param,
        #         ],
        #     )
        measurement.register_parameter(independent_param)
        measurement.register_parameter(dependent_param,
                                       setpoints=[
                                           independent_param])
        with measurement.run() as datasaver:
            datasaver.add_result((independent_param, x),
                                 (dependent_param, y))
            
                    
            
        
            
        
        
        