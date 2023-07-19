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

from qumada.measurement.measurement import MeasurementScript
from qumada.utils.ramp_parameter import ramp_or_set_parameter
from qumada.utils.utils import _validate_mapping, naming_helper
from qumada.instrument.buffers.buffer import is_bufferable

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
            if self.priorities == {}:
                raise AssertionError("For this type of measurement exactly 1 gettable channel is required!")
            else:
                candidates = self.priorities[min(self.priorities.keys())]["channels"]
                intersect  = [ch for ch in self.gettable_channels if ch in candidates]
                assert len(intersect) == 1 
                self.dependent_param = intersect[0]
                instrument = self.dependent_param.root_instrument
        else:    
            self.dependent_param = self.gettable_channels[0]
            instrument = self.dependent_param.root_instrument
        
        if settings.get("module", "scope") == "scope":
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
        self.settings["spectrometer"] = self.spectrometer
        return self.spectrometer
    
    def _save_data_to_db(self, 
                         results: dict,
                         data_type: str,
                         ):
        measurement = Measurement(name=f"{self.measurement_name} {data_type}")
        
        if data_type == "spectrum":    
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
        elif data_type == "timetrace":
            timer = ElapsedTimeParameter("time")
            independent_param = timer
            dependent_param = self.dependent_param
            #TODO: n_pts is not correct?
            x = np.arange(len(results["timetrace_raw"][0])) / results['settings'].fs
            y = results["timetrace_raw"][0]
        else:
            raise NameError(f"{data_type} is no valid data_type!")
                
        measurement.register_parameter(independent_param)
        measurement.register_parameter(dependent_param,
                                       setpoints=[
                                           independent_param])
        static_gettables = []
        for parameter, channel in zip(self.static_gettable_parameters, self.static_gettable_channels):
                measurement.register_parameter(
                    channel,
                    setpoints=[independent_param,]
                    )
                parameter_value = self.properties[
                    parameter["gate"]][parameter["parameter"]]["value"]
                static_gettables.append(
                    (channel, 
                      [parameter_value for _ in range(len(x))]
                      )
                    )


        with measurement.run() as datasaver:
            datasaver.add_result((independent_param, x),
                                 (dependent_param, abs(y)),
                                 *static_gettables,)
        #TODO: Check if absolut is ok
            
    # def save_data_to_db(self,
    #                     results,
    #                     indices: int|list,
    #                     data_type: str = "both"):
    #     if type(indices)==int:
    #         self._save_data_to_db(
    #             results=results[indices]):
    #             data_type="spectrum")
    
            
                    
            
        
            
        
        
        