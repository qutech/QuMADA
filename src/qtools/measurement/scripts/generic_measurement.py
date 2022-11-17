import time
from copy import deepcopy
from time import sleep

import qcodes as qc
from qcodes.dataset.measurements import Measurement
from qcodes.instrument.specialized_parameters import ElapsedTimeParameter
from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.instrument import Parameter
from qcodes.utils.dataset.doNd import LinSweep, do1d, do2d, dond
from qtools.measurement.doNd_enhanced.doNd_enhanced import _interpret_breaks, do1d_parallel, do1d_parallel_asym
from qtools.measurement.measurement import MeasurementScript
from qtools.utils.ramp_parameter import ramp_or_set_parameter
#from qtools.utils.utils import _validate_mapping

class Generic_1D_Sweep(MeasurementScript):
    def run(self, **dond_kwargs) -> list:
        """
        Peform 1D sweeps for all dynamic parameters, one after another. Dynamic
        parameters that are not currently active are kept at their "value" value.

        Parameters
        ----------
        **dond_kwargs : Kwargs to pass to the dond method when it is called.
        **settings[dict]: Kwargs passed during setup(). Details below:
                wait_time[float]: Wait time between initialization and each measurement,
                                    default = 5 sek
                include_gate_name[Bool]: Append name of ramped gate to measurement
                                    name. Default True.
                ramp_speed[float]: Speed at which parameters are ramped during 
                                    initialization in units. Default = 0.3
                ramp_time[float]: Amount of time in s ramping of each parameter during 
                                    initialization may take. If the ramp_speed is
                                    too small it will be increased to match the
                                    ramp_time. Default = 10
                log_idle_params[bool]: Record dynamic parameters that are kept constant
                                    during the sweeps of other parameters as gettable
                                    params. Default True.

        Returns
        -------
        list
            List with all QCoDeS Datasets.

        """
        self.initialize()
        wait_time = self.settings.get("wait_time", 5)
        include_gate_name = self.settings.get("include_gate_name", True)
        data = list()
        time.sleep(wait_time)
        for sweep, dynamic_parameter in zip(self.dynamic_sweeps, self.dynamic_parameters):
            if include_gate_name:
                measurement_name = f"{self.metadata.measurement.name} {dynamic_parameter['gate']}"            
            else:
                measurement_name = self.metadata.measurment.name or "measurement"
            if self.settings.get("log_idle_params", True):
                idle_channels = [entry for entry  in self.dynamic_channels if entry!=sweep.param]
                measured_channels = set((*self.gettable_channels, *idle_channels))
            else:
                measured_channels = set(self.gettable_channels)
            ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0])
            time.sleep(wait_time)
            data.append(
                dond(sweep,
                     *measured_channels,
                     measurement_name = measurement_name,
                     break_condition = _interpret_breaks(self.break_conditions),
                     **dond_kwargs
                     )
                )
            self.reset()
        return data


class Generic_nD_Sweep(MeasurementScript):

    def run(self, **dond_kwargs):
        """
        Perform n-dimensional sweep for n dynamic parameters.

        Parameters
        ----------
        **dond_kwargs : Kwargs to pass to the dond method when it is called.
        **settings[dict]: Kwargs passed during setup(). Details below:
                wait_time[float]: Wait time between initialization and each measurement,
                                    default = 5 sek
                include_gate_name[Bool]: Append name of ramped gates to measurement
                                    name. Default True.
                ramp_speed[float]: Speed at which parameters are ramped during 
                                    initialization in units. Default = 0.3
                ramp_time[float]: Amount of time in s ramping of each parameter during 
                                    initialization may take. If the ramp_speed is
                                    too small it will be increased to match the
                                    ramp_time. Default = 10

        Returns
        -------
        data : QCoDeS dataset with measurement data
        """
        
        self.initialize()
        wait_time = self.settings.get("wait_time", 5)
        include_gate_name = self.settings.get("include_gate_name", True)
        if include_gate_name:
            measurement_name = f"{self.metadata.measurement.name} Gates: {[gate['gate'] for gate in self.dynamic_parameters]}"
        else:
            measurement_name = self.metadata.measurement.name or "measurement"
         
        for sweep in self.dynamic_sweeps:
            ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0])
        time.sleep(wait_time)
        data = dond(*tuple(self.dynamic_sweeps),
                    *tuple(self.gettable_channels),
                    measurement_name=measurement_name,
                    break_condition=_interpret_breaks(self.break_conditions),
                    use_threads=True,
                    **dond_kwargs)
        self.reset()
        return data

class Generic_1D_parallel_asymm_Sweep(MeasurementScript):
    """
    Sweeps all dynamic parameters in parallel, setpoints of first parameter are
    used for all parameters.
    """
    def run(self, **do1d_kwargs):
        self.initialize()
        backsweep_after_break = self.settings.get("backsweep_after_break", False)
        wait_time = self.settings.get("wait_time", 5)
        dynamic_params = list()
        for sweep in self.dynamic_sweeps:
            ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0])
            dynamic_params.append(sweep.param)
        time.sleep(wait_time)
        data = do1d_parallel_asym(*tuple(self.gettable_channels),
                            param_set=dynamic_params,
                            setpoints = [sweep.get_setpoints() for sweep in self.dynamic_sweeps],
                            delay = self.dynamic_sweeps[0]._delay,
                            measurement_name=self.metadata.measurement.name or "measurement",
                            break_condition = _interpret_breaks(self.break_conditions),
                            backsweep_after_break = backsweep_after_break,
                            **do1d_kwargs
                            )
        return data
    
class Generic_1D_parallel_Sweep(MeasurementScript):
    """
    Sweeps all dynamic parameters in parallel, setpoints of first parameter are
    used for all parameters.
    """
    def run(self, **do1d_kwargs):
        self.initialize()
        backsweep_after_break = self.settings.get("backsweep_after_break", False)
        wait_time = self.settings.get("wait_time", 5)
        dynamic_params = list()
        for sweep in self.dynamic_sweeps:
            ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0])
            dynamic_params.append(sweep.param)
        time.sleep(wait_time)
        data = do1d_parallel(*tuple(self.gettable_channels),
                            param_set=dynamic_params,
                            setpoints = self.dynamic_sweeps[0].get_setpoints(),
                            delay = self.dynamic_sweeps[0]._delay,
                            measurement_name=self.metadata.measurement.name or "measurement",
                            break_condition = _interpret_breaks(self.break_conditions),
                            backsweep_after_break = backsweep_after_break,
                            **do1d_kwargs
                            )
        return data

class Timetrace(MeasurementScript):
    """
    Timetrace measurement, duration and timestep can be set as keyword-arguments,
    both in seconds.
    Be aware that the timesteps can vary as the time it takes to record a
    datapoint is not constant, the argument only sets the wait time. However,
    the recorded "elapsed time" is accurate.
    kwargs: 
        auto_naming: Renames measurement automatically to Timetrace if True.
        
    """
    def run(self):
        self.initialize()
        duration = self.settings.get("duration", 300)
        timestep = self.settings.get("timestep", 1)
        timer = ElapsedTimeParameter('time')
        auto_naming = self.settings.get("auto_naming", False)
        if auto_naming:
            self.metadata.measurement.name = "Timetrace"
        meas = Measurement(name = self.metadata.measurement.name or "Timetrace")
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

class Timetrace_with_sweeps(MeasurementScript):
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
        backsweeps = self.settings.get("backsweeps", False)
        timer = ElapsedTimeParameter('time')
        meas = Measurement(name = self.metadata.measurement.name or "timetrace")
        meas.register_parameter(timer)
        setpoints = [timer]
        for parameter in self.dynamic_channels: 
            meas.register_parameter(parameter)            
            setpoints.append(parameter)
        for parameter in self.gettable_channels:
            meas.register_parameter(parameter, setpoints=setpoints)
        with meas.run() as datasaver:
            start = timer.reset_clock()
            while timer() < duration:
                for sweep in self.dynamic_sweeps:
                    ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0], ramp_time = timestep)
                now = timer()
                for i in range(0,len(self.dynamic_sweeps[0].get_setpoints())):
                    for sweep in self.dynamic_sweeps:
                        sweep._param.set(sweep.get_setpoints()[i])
                    set_values = [(sweep._param, sweep.get_setpoints()[i]) for sweep in self.dynamic_sweeps]
                    results = [(channel, channel.get()) for channel in self.gettable_channels]
                    datasaver.add_result((timer, now),
                                         *set_values,
                                         *results)
                #time.sleep(timestep)
        dataset = datasaver.dataset
        return dataset