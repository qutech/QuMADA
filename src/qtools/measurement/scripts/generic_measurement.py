import time
from copy import deepcopy

import qcodes as qc
from qcodes.dataset.measurements import Measurement
from qcodes.instrument.specialized_parameters import ElapsedTimeParameter
from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.instrument import Parameter
from qcodes.utils.dataset.doNd import LinSweep, do1d, do2d, dond
from qtools.measurement.doNd_enhanced.doNd_enhanced import _interpret_breaks, do1d_parallel
from qtools.measurement.measurement import MeasurementScript


class Generic_1D_Sweep(MeasurementScript):
    def run(self) -> list:
        """
        Perform 1D sweeps for all dynamic parameters
        """
        self.initialize()
        wait_time = self.settings.get("wait_time", 5)
        data = list()
        time.sleep(wait_time)
        i=0
        for sweep in self.dynamic_sweeps:  
            # if self.settings.get("include_gate_name", False):
            #     measurement_name = self.metadata.measurement.name + f" {sweep['gate']}"
            sweep._param.set(sweep.get_setpoints()[0])
            time.sleep(wait_time)
            data.append(
                dond(sweep,
                     *tuple(self.gettable_channels),
                     measurement_name=self.metadata.measurement.name or "measurement",
                     break_condition = _interpret_breaks(self.break_conditions)
                     )
                )
            self.reset()
            i+=1
        return data


class Generic_nD_Sweep(MeasurementScript):
    """
    Perform n-Dimensional sweep with n dynamic parameters.
    """

    def run(self):

        self.initialize()
        wait_time = self.settings.get("wait_time", 5)
        for sweep in self.dynamic_sweeps:
            sweep._param.set(sweep.get_setpoints()[0])
        time.sleep(wait_time)
        data = dond(*tuple(self.dynamic_sweeps),
                    *tuple(self.gettable_channels),
                    measurement_name=self.metadata.measurement.name or "measurement",
                    break_condition=_interpret_breaks(self.break_conditions)
                     )
        self.reset()
        return data
    
class Generic_1D_parallel_Sweep(MeasurementScript):
    """
    Sweeps all dynamic parameters in parallel, setpoints of first parameter are
    used for all parameters.
    """
    def run(self):
        self.initialize()
        backsweep_after_break = self.settings.get("backsweep_after_break", False)
        wait_time = self.settings.get("wait_time", 5)
        dynamic_params = list()
        for sweep in self.dynamic_sweeps:
            sweep._param.set(sweep.get_setpoints()[0])
            dynamic_params.append(sweep.param)
        time.sleep(wait_time)
        data = do1d_parallel(*tuple(self.gettable_channels),
                            param_set=dynamic_params,
                            setpoints = self.dynamic_sweeps[0].get_setpoints(),
                            delay = self.dynamic_sweeps[0]._delay,
                            measurement_name=self.metadata.measurement.name or "measurement",
                            break_condition = _interpret_breaks(self.break_conditions),
                            backsweep_after_break = backsweep_after_break
                            )
        return data
    
class Timetrace(MeasurementScript):
    """
    Timetrace measurement, duration and timestep can be set as keyword-arguments,
    both in seconds.
    Be aware that the timesteps can vary as the time it takes to record a 
    datapoint is not constant, the argument only sets the wait time. However,
    the recorded "elapsed time" is accurate.
    """
    def run(self):
        self.initialize()
        duration = self.settings.get("duration", 300)
        timestep = self.settings.get("timestep", 1)
        timer = ElapsedTimeParameter('time')
        meas = Measurement(name = self.metadata.measurement.name or "timetrace")
        meas.register_parameter(timer)
        for parameter in self.gettable_channels:
            meas.register_parameter(parameter, setpoints=[timer,])
        with meas.run() as datasaver:
            start = timer.reset_clock()
            while timer() < duration:
                now = timer()
                results = [(channel, channel.get()) for channel in self.gettable_channels]
                datasaver.add_result((timer, now),
                                     *results)
                time.sleep(timestep)
        dataset = datasaver.dataset
        return dataset
                
            
    