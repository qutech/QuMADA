# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of qtools.
#
# qtools is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# qtools is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# qtools. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Till Huckeman
# - Bertha Lab Setup
# - Daniel Grothe
# - Max Lennart Oberländer
# - Sionludi Lab
# - Tobias Hangleiter

from time import sleep
import logging

from qcodes.dataset import dond
from qcodes.dataset.measurements import Measurement
from qcodes.parameters.specialized_parameters import ElapsedTimeParameter

from qtools.measurement.doNd_enhanced.doNd_enhanced import (
    _dev_interpret_breaks,
    _interpret_breaks,
    do1d_parallel,
    do1d_parallel_asym,
)
from qtools.measurement.measurement import MeasurementScript
from qtools.utils.ramp_parameter import ramp_or_set_parameter
from qtools.utils.utils import _validate_mapping, naming_helper
from qtools.instrument.buffers.buffer import is_bufferable


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
        naming_helper(self, default_name="1D Sweep")
        data = list()
        sleep(wait_time)
        for sweep, dynamic_parameter in zip(self.dynamic_sweeps, self.dynamic_parameters):
            if include_gate_name:
               self._measurement_name = f"{self.measurement_name} {dynamic_parameter['gate']}"
            else:
                self._measurement_name = self.measurement_name
            if self.settings.get("log_idle_params", True):
                idle_channels = [entry for entry in self.dynamic_channels if entry != sweep.param]
                measured_channels = {*self.gettable_channels, *idle_channels}
            else:
                measured_channels = set(self.gettable_channels)
            ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0])
            sleep(wait_time)
            data.append(
                dond(
                    sweep,
                    *measured_channels,
                    measurement_name=self._measurement_name,
                    break_condition=_interpret_breaks(self.break_conditions),
                    **dond_kwargs,
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
        self.buffered = False
        self.initialize()
        wait_time = self.settings.get("wait_time", 5)
        include_gate_name = self.settings.get("include_gate_name", True)
        if include_gate_name:
            measurement_name = (
                f"{self.metadata.measurement.name} Gates: {[gate['gate'] for gate in self.dynamic_parameters]}"
            )
        else:
            measurement_name = self.metadata.measurement.name or "measurement"

        for sweep in self.dynamic_sweeps:
            ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0])
        sleep(wait_time)
        data = dond(
            *tuple(self.dynamic_sweeps),
            *tuple(self.gettable_channels),
            measurement_name=measurement_name,
            break_condition=_interpret_breaks(self.break_conditions),
            use_threads=True,
            **dond_kwargs,
        )
        self.reset()
        return data


class Generic_1D_parallel_asymm_Sweep(MeasurementScript):
    """
    Sweeps all dynamic parameters in parallel, setpoints of first parameter are
    used for all parameters.
    """

    def run(self, **do1d_kwargs):
        naming_helper(self, default_name="Parallel 1D Sweep")
        self.initialize()
        backsweep_after_break = self.settings.get("backsweep_after_break", False)
        wait_time = self.settings.get("wait_time", 5)
        dynamic_params = list()
        for sweep in self.dynamic_sweeps:
            ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0])
            dynamic_params.append(sweep.param)
        sleep(wait_time)
        data = do1d_parallel_asym(
            *tuple(self.gettable_channels),
            param_set=dynamic_params,
            setpoints=[sweep.get_setpoints() for sweep in self.dynamic_sweeps],
            delay=self.dynamic_sweeps[0]._delay,
            measurement_name=self.measurement_name,
            break_condition=_interpret_breaks(self.break_conditions),
            backsweep_after_break=backsweep_after_break,
            **do1d_kwargs,
        )
        return data


class Generic_1D_parallel_Sweep(MeasurementScript):
    """
    Sweeps all dynamic parameters in parallel, setpoints of first parameter are
    used for all parameters.
    """

    def run(self, **do1d_kwargs):
        self.initialize()
        naming_helper(self, default_name="Parallel 1D Sweep")
        backsweep_after_break = self.settings.get("backsweep_after_break", False)
        wait_time = self.settings.get("wait_time", 5)
        dynamic_params = list()
        for sweep in self.dynamic_sweeps:
            ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0])
            dynamic_params.append(sweep.param)
        sleep(wait_time)
        data = do1d_parallel(
            *tuple(self.gettable_channels),
            param_set=dynamic_params,
            setpoints=self.dynamic_sweeps[0].get_setpoints(),
            delay=self.dynamic_sweeps[0]._delay,
            measurement_name=self.measurement_name,
            break_condition=lambda x: _dev_interpret_breaks(self.break_conditions, x),
            backsweep_after_break=backsweep_after_break,
            **do1d_kwargs,
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
        timer = ElapsedTimeParameter("time")
        naming_helper(self, default_name="Timetrace")
        meas = Measurement(name=self.measurement_name)
        meas.register_parameter(timer)
        for parameter in [*self.gettable_channels, *self.dynamic_channels]:
            meas.register_parameter(
                parameter,
                setpoints=[
                    timer,
                ],
            )
        with meas.run() as datasaver:
            start = timer.reset_clock()
            while timer() < duration:
                now = timer()
                results = [(channel, channel.get()) for channel in [*self.gettable_channels, *self.dynamic_channels]]
                datasaver.add_result((timer, now), *results)
                sleep(timestep)
        dataset = datasaver.dataset
        return dataset
    
class Timetrace_buffered(MeasurementScript):
    """
    Timetrace measurement, duration and timestep are set via the buffer settings.
    Does currently not work with dynamic parameters. 
    Furthermore, you cannot use "manual" triggering mode as now ramp is started.
    It is fine to use software triggering here, as long as only one buffered 
    instrument is used, else you should use "hardware".
    
    kwargs:
        auto_naming: Renames measurement automatically to Timetrace if True.

    """

    def run(self):
        self.initialize()
        #duration = self.settings.get("duration", 300)
        #timestep = self.settings.get("timestep", 1)
        timer = ElapsedTimeParameter("time")
        TRIGGER_TYPES = ["software", "hardware"]
        trigger_start = self.settings.get("trigger_start", "software")  # TODO: this should be set elsewhere
        trigger_reset = self.settings.get("trigger_reset", None)
        trigger_type = _validate_mapping(
            self.settings.get("trigger_type"),
            TRIGGER_TYPES,
            default="software",
            default_key_error="software",
        )
        self.buffered = True
        datasets = []
        
        self.generate_lists()
        naming_helper(self, default_name = "Timetrace")
        meas = Measurement(name=self.measurement_name)
        
        meas.register_parameter(timer)
        for parameter in [*self.gettable_channels, *self.dynamic_channels]:
            meas.register_parameter(
                parameter,
                setpoints=[
                    timer,
                ],
            )
        # Block required to log gettable and static parameters that are not
        # buffarable (e.g. Dac Channels)
        static_gettables = []
        del_channels = []
        del_params = []
        for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
            if is_bufferable(channel):
                meas.register_parameter(
                    channel,
                    setpoints=[timer,]
                )
            elif channel in self.static_channels:
                del_channels.append(channel)
                del_params.append(parameter)
                meas.register_parameter(
                    channel,
                    setpoints=[timer,]
                    )
                parameter_value = self.properties[
                    parameter["gate"]][parameter["parameter"]]["value"]
                static_gettables.append(
                    (channel, 
                      [parameter_value for _ in range(self.buffered_num_points)]
                      )
                    )
        for channel in del_channels:
            self.gettable_channels.remove(channel)
        for param in del_params:
            self.gettable_parameters.remove(param)
            
        with meas.run() as datasaver:
            #start = timer.reset_clock()
            self.ready_buffers()

            if trigger_type == "manual":
                raise Exception("Manual triggering not supported by Timetrace.")
            if trigger_type == "hardware":
                # Set trigger to high here
                try:
                    trigger_start()
                except:
                    print("Please set a trigger or define a trigger_start method")
                pass

            elif trigger_type == "software":
                for buffer in self.buffers:
                    buffer.force_trigger()

            while not all(buffer.is_finished() for buffer in list(self.buffers)):
                sleep(0.1)
            try:
                trigger_reset()
            except:
                print("No method to reset the trigger defined.")

            results = self.readout_buffers(timestamps=True)
            # TODO: Append values from other dynamic parameters
            datasaver.add_result((timer, results.pop(-1)),
                                 *results,
                                 *static_gettables,)
            datasets.append(datasaver.dataset)
        return datasets


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
        timer = ElapsedTimeParameter("time")
        meas = Measurement(name=self.metadata.measurement.name or "timetrace")
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
                    ramp_or_set_parameter(sweep._param, sweep.get_setpoints()[0], ramp_time=timestep)
                now = timer()
                for i in range(0, len(self.dynamic_sweeps[0].get_setpoints())):
                    for sweep in self.dynamic_sweeps:
                        sweep._param.set(sweep.get_setpoints()[i])
                    set_values = [(sweep._param, sweep.get_setpoints()[i]) for sweep in self.dynamic_sweeps]
                    results = [(channel, channel.get()) for channel in self.gettable_channels]
                    datasaver.add_result((timer, now), *set_values, *results)
                # sleep(timestep)
        dataset = datasaver.dataset
        return dataset


class Generic_1D_Sweep_buffered(MeasurementScript):
    """
    WIP Buffer measurement script
    Trigger Types:
            "software": Sends a software command to each buffer and dynamic parameters
                        in order to start data acquisition and ramping. Timing
                        might be off slightly
            "hardware": Expects a trigger command for each setpoint. Can be used
                        with a preconfigured hardware trigger (Todo), a method,
                        that starts a manually adjusted hardware trigger
                        (has to be passed as trigger_start() method to
                         measurement script) or a manual trigger.
            "manual"  : The trigger setup is done by the user. The measurent script will
                        just start the first ramp. Usefull for synchronized trigger outputs
                        as in the QDac.
    trigger_start: A callable that triggers the trigger (called to start the measurement)
                    or the keyword "manual" when triggering is done by user. Defauls is manual.
    trigger_reset (optional): Callable to reset the trigger. Default is NONE.
    include_gate_name (optional): Appends name of ramped gates to measurement name. Default is TRUE.
    """

    def run(self):
        self.buffered = True
        TRIGGER_TYPES = ["software", "hardware", "manual"]
        trigger_start = self.settings.get("trigger_start", "manual")  # TODO: this should be set elsewhere
        trigger_reset = self.settings.get("trigger_reset", None)
        trigger_type = _validate_mapping(
            self.settings.get("trigger_type"),
            TRIGGER_TYPES,
            default="software",
            default_key_error="software",
        )
        include_gate_name = self.settings.get("include_gate_name", True)
        sync_trigger = self.settings.get("sync_trigger", None)
        datasets = []
        self.generate_lists()
        measurement_name = naming_helper(self, default_name= "1D Sweep")
        # meas.register_parameter(timer)
        for dynamic_sweep, dynamic_parameter in zip(self.dynamic_sweeps.copy(), self.dynamic_parameters.copy()):
            self.measurement_name=measurement_name
            if include_gate_name:
                self.measurement_name += f" {dynamic_parameter['gate']}"
            self.properties[
                dynamic_parameter["gate"]][dynamic_parameter["parameter"]
                                           ]["_is_triggered"] = True
            dynamic_param = dynamic_sweep.param
            meas = Measurement(name=self.measurement_name)
            meas.register_parameter(dynamic_param)
            # This next block is required to log static and idle dynamic
            # parameters that cannot be buffered.
            static_gettables = []
            del_channels = []
            del_params = []
            for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
                if is_bufferable(channel):
                    meas.register_parameter(
                        channel,
                        setpoints=[
                            dynamic_param,
                        ],
                    )
                elif channel in self.static_channels:
                    del_channels.append(channel)
                    del_params.append(parameter)
                    parameter_value = self.properties[
                        parameter["gate"]][parameter["parameter"]]["value"]
                    static_gettables.append(
                        (channel, 
                         [parameter_value for _ in range(self.buffered_num_points)]
                         )
                        )
            for parameter, channel in zip(self.dynamic_parameters, self.dynamic_channels):
                if channel != dynamic_param:
                    try:
                        parameter_value = self.properties[
                            parameter["gate"]][parameter["parameter"]]["value"]
                    except KeyError:
                        logging.error("An idle dynamic parameter has no value assigned\
                              and cannot be logged!")
                        break
                    static_gettables.append(
                        (channel, 
                         [parameter_value for _ in range(self.buffered_num_points)]
                         )
                        )
            for param in static_gettables:
                meas.register_parameter(param[0],
                                        setpoints=[
                                            dynamic_param,
                                            ]
                                        )
            for channel in del_channels:
                self.gettable_channels.remove(channel)
            for param in del_params:
                self.gettable_parameters.remove(param)
                
            try:
                trigger_reset()
            except TypeError:
                logging.info("No method to reset the trigger defined.")
                
            with meas.run() as datasaver:
                self.initialize()
                results = []
                self.ready_buffers()
                try:
                    dynamic_param.root_instrument._qtools_ramp(
                        [dynamic_param],
                        start_values = None,
                        end_values=[dynamic_sweep.get_setpoints()[-1]],
                        ramp_time=self.buffer_settings["duration"],
                        sync_trigger=sync_trigger,
                    )
                except AttributeError() as e:
                    print("Exception: This instrument probably does not have a \
                          a qtools_ramp method. Buffered measurements without \
                          ramp method are no longer supported. \
                          Use the unbuffered script!")
                    raise e
                
                if trigger_type == "manual":
                    pass
                if trigger_type == "hardware":
                    try:
                        trigger_start()
                    except AttributeError as e:
                        print("Please set a trigger or define a trigger_start method")
                        raise e

                elif trigger_type == "software":
                    for buffer in self.buffers:
                        buffer.force_trigger()
                    logging.info("You are using software trigger, which \
                                    can lead to significant delays between \
                                    measurement instruments! Only recommended\
                                    for debugging.")
                while not all(buffer.is_finished() for buffer in list(self.buffers)):
                    sleep(0.1)
                try:
                    trigger_reset()
                except TypeError:
                    logging.info("No method to reset the trigger defined.")

                results = self.readout_buffers()
                datasaver.add_result((dynamic_param, dynamic_sweep.get_setpoints()),
                                     *results,
                                     *static_gettables,
                                     )
                datasets.append(datasaver.dataset)
                self.properties[
                    dynamic_parameter["gate"]][dynamic_parameter["parameter"]
                                               ]["_is_triggered"] = False
        return datasets

class Generic_1D_Hysteresis_buffered(MeasurementScript):
    """
    WIP Buffer Hysteresis measurement script
    Malte Neul / 09.01.2023
    Trigger Types:
            "software": Sends a software command to each buffer and dynamic parameters
                        in order to start data acquisition and ramping. Timing
                        might be off slightly
            "hardware": Expects a trigger command for each setpoint. Can be used
                        with a preconfigured hardware trigger (Todo), a method,
                        that starts a manually adjusted hardware trigger
                        (has to be passed as trigger_start() method to
                         measurement script) or a manual trigger.
            "manual"  : The trigger setup is done by the user. The measurent script will
                        just start the first ramp. Usefull for synchronized trigger outputs
                        as in the QDac.
    trigger_start: A callable that triggers the trigger (called to start the measurement)
                    or the keyword "manual" when triggering is done by user. Defauls is manual.
    trigger_reset (optional): Callable to reset the trigger. Default is NONE.
    include_gate_name (optional): Appends name of ramped gates to measurement name. Default is TRUE.
    """
    
    def run(self): 
        self.buffered = True
        TRIGGER_TYPES = ["software", "hardware", "manual"]
        trigger_start = self.settings.get("trigger_start", "manual")  # TODO: this should be set elsewhere
        trigger_reset = self.settings.get("trigger_reset", None)
        trigger_type = _validate_mapping(
            self.settings.get("trigger_type"),
            TRIGGER_TYPES,
            default="software",
            default_key_error="software",
        )
        include_gate_name = self.settings.get("include_gate_name", True)
        sync_trigger = self.settings.get("sync_trigger", None)
        iterations = self.settings.get("iterations", 1)
        iterations*=2
        datasets = []
        self.generate_lists()
        measurement_name = naming_helper(self, default_name= "1D Sweep")
        # meas.register_parameter(timer)
        for dynamic_sweep, dynamic_parameter in zip(self.dynamic_sweeps.copy(), self.dynamic_parameters.copy()):
            self.measurement_name=measurement_name
            if include_gate_name:
                self.measurement_name += f" {dynamic_parameter['gate']}"
            self.properties[
                dynamic_parameter["gate"]][dynamic_parameter["parameter"]
                                           ]["_is_triggered"] = True
            dynamic_param = dynamic_sweep.param
            meas = Measurement(name=self.measurement_name)
            meas.register_parameter(dynamic_param)
            # This next block is required to log static and idle dynamic
            # parameters that cannot be buffered.
            static_gettables = []
            del_channels = []
            del_params = []
            for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
                if is_bufferable(channel):
                    meas.register_parameter(
                        channel,
                        setpoints=[
                            dynamic_param,
                        ],
                    )
                elif channel in self.static_channels:
                    del_channels.append(channel)
                    del_params.append(parameter)
                    parameter_value = self.properties[
                        parameter["gate"]][parameter["parameter"]]["value"]
                    static_gettables.append(
                        (channel, 
                         [parameter_value for _ in range(self.buffered_num_points)]
                         )
                        )
            for parameter, channel in zip(self.dynamic_parameters, self.dynamic_channels):
                if channel != dynamic_param:
                    try:
                        parameter_value = self.properties[
                            parameter["gate"]][parameter["parameter"]]["value"]
                    except KeyError:
                        logging.error("An idle dynamic parameter has no value assigned\
                              and cannot be logged!")
                        break
                    static_gettables.append(
                        (channel, 
                         [parameter_value for _ in range(self.buffered_num_points)]
                         )
                        )
            for param in static_gettables:
                meas.register_parameter(param[0],
                                        setpoints=[
                                            dynamic_param,
                                            ]
                                        )
            for channel in del_channels:
                self.gettable_channels.remove(channel)
            for param in del_params:
                self.gettable_parameters.remove(param)
                
            try:
                trigger_reset()
            except TypeError:
                logging.info("No method to reset the trigger defined.")
                
            with meas.run() as datasaver:
                self.initialize()
                results = []
                
                for iiter in range(0, iterations):
                    
                    self.ready_buffers()
                    if iiter % 2 == 0:
                        set_points = dynamic_sweep.get_setpoints()
                        end_value = dynamic_sweep.get_setpoints()[-1]
                        
                    else:
                        end_value = dynamic_sweep.get_setpoints()[0]
                        set_points = list(reversed(dynamic_sweep.get_setpoints()))
                    try:
                        dynamic_param.root_instrument._qtools_ramp(
                            [dynamic_param],
                            start_values = None,
                            end_values=[end_value],
                            ramp_time=self.buffer_settings["duration"],
                            sync_trigger=sync_trigger,
                        )
                    except AttributeError() as e:
                        print("Exception: This instrument probably does not have a \
                              a qtools_ramp method. Buffered measurements without \
                              ramp method are no longer supported. \
                              Use the unbuffered script!")
                        raise e
                    
                    if trigger_type == "manual":
                        pass
                    if trigger_type == "hardware":
                        try:
                            trigger_start()
                        except AttributeError as e:
                            print("Please set a trigger or define a trigger_start method")
                            raise e
    
                    elif trigger_type == "software":
                        for buffer in self.buffers:
                            buffer.force_trigger()
                        logging.info("You are using software trigger, which \
                                        can lead to significant delays between \
                                        measurement instruments! Only recommended\
                                        for debugging.")
                    while not all(buffer.is_finished() for buffer in list(self.buffers)):
                        sleep(0.1)
                    try:
                        trigger_reset()
                    except TypeError:
                        logging.info("No method to reset the trigger defined.")
    
                    results = self.readout_buffers()
                    datasaver.add_result((dynamic_param, set_points),
                                         *results,
                                         *static_gettables,
                                         )
                datasets.append(datasaver.dataset)
                self.properties[
                    dynamic_parameter["gate"]][dynamic_parameter["parameter"]
                                               ]["_is_triggered"] = False
        return datasets


class Generic_2D_Sweep_buffered(MeasurementScript):
    """
    WIP Buffer measurement script
    Trigger Types:
            "software": Sends a software command to each buffer and dynamic parameters
                        in order to start data acquisition and ramping. Timing
                        might be off slightly
            "hardware": Expects a trigger command for each setpoint. Can be used
                        with a preconfigured hardware trigger (Todo), a method,
                        that starts a manually adjusted hardware trigger
                        (has to be passed as trigger_start() method to
                         measurement script) or a manual trigger.
            "manual"  : The trigger setup is done by the user. The measurent script will
                        just start the first ramp. Usefull for synchronized trigger outputs
                        as in the QDac.
    trigger_start: A callable that triggers the trigger (called to start the measurement)
                    or the keyword "manual" when triggering is done by user. Defauls is manual.
    trigger_reset (optional): Callable to reset the trigger. Default is NONE.
    include_gate_name (optional): Appends name of ramped gates to measurement name. Default is TRUE.
    reset_time: Time for ramping fast param back to the start value.
    reverse_param_order: Switch slow and fast param.
    """

    def run(self):
        self.buffered = True
        TRIGGER_TYPES = ["software", "hardware", "manual"]
        trigger_start = self.settings.get("trigger_start", "manual")  # TODO: this should be set elsewhere
        trigger_reset = self.settings.get("trigger_reset", None)
        trigger_type = _validate_mapping(
            self.settings.get("trigger_type"),
            TRIGGER_TYPES,
            default="software",
            default_key_error="software",
        )
        include_gate_name = self.settings.get("include_gate_name", True)
        sync_trigger = self.settings.get("sync_trigger", None)
        reverse_param_order = self.settings.get("reverse_param_order", False)
        reset_time = self.settings.get("reset_time", 0)
        datasets = []
        
        self.generate_lists()
        
        if len(self.dynamic_sweeps)!=2:
            raise Exception("The 2D workflow takes exactly two dynamic parameters! ")
        self.measurement_name = naming_helper(self, default_name= "2D Sweep")
        if include_gate_name:
            gate_names=[gate["gate"] for gate in self.dynamic_parameters]
            self.measurement_name += f" {gate_names}"
        
        meas = Measurement(name=self.measurement_name)

        if reverse_param_order:
            slow_param = self.dynamic_channels[1]
            slow_sweep = self.dynamic_sweeps[1]
            fast_param = self.dynamic_channels[0]
            fast_sweep = self.dynamic_sweeps[0]
            self.properties[
                self.dynamic_parameters[0]["gate"]][self.dynamic_parameters[0]["parameter"]
                                           ]["_is_triggered"] = True
        else:
            slow_param = self.dynamic_channels[0]
            slow_sweep = self.dynamic_sweeps[0]
            fast_param = self.dynamic_channels[1]
            fast_sweep = self.dynamic_sweeps[1]
            self.properties[
                self.dynamic_parameters[1]["gate"]][self.dynamic_parameters[1]["parameter"]
                                           ]["_is_triggered"] = True
                                                    
        for dynamic_param in self.dynamic_channels:
            meas.register_parameter(dynamic_param)                            
        #-------------------
        static_gettables = []
        del_channels = []
        del_params = []
        for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
            if is_bufferable(channel):
                meas.register_parameter(
                    channel,
                    setpoints=[
                        slow_param, fast_param,
                    ],
                )
            elif channel in self.static_channels:
                del_channels.append(channel)
                del_params.append(parameter)
                meas.register_parameter(
                    channel,
                    setpoints=[slow_param, fast_param,]
                    )
                parameter_value = self.properties[
                    parameter["gate"]][parameter["parameter"]]["value"]
                static_gettables.append(
                    (channel, 
                      [parameter_value for _ in range(self.buffered_num_points)]
                      )
                    )
        for channel in del_channels:
            self.gettable_channels.remove(channel)
        for param in del_params:
            self.gettable_parameters.remove(param)
        #--------------------------
        
        self.initialize()            
        try:
            trigger_reset()
        except:
            pass
        with meas.run() as datasaver:
            results = []
            slow_setpoints = slow_sweep.get_setpoints()
            for setpoint in slow_setpoints:
                slow_param.set(setpoint)
                if reset_time >0:
                    ramp_or_set_parameter(fast_param, 
                                          fast_sweep.get_setpoints()[0], 
                                          ramp_rate=None,
                                          ramp_time=reset_time)
                else:
                    fast_param.set(fast_sweep.get_setpoints()[0])
                if reset_time<slow_sweep._delay:
                    sleep(slow_sweep._delay-reset_time)
                self.ready_buffers()
                try:
                    fast_param.root_instrument._qtools_ramp(
                        [fast_param],
                        end_values=[fast_sweep.get_setpoints()[-1]],
                        ramp_time=self.buffer_settings["duration"],
                        sync_trigger=sync_trigger,
                    )
                except AttributeError() as e:
                    print("Exception: This instrument probably does not have a \
                          a qtools_ramp method. Buffered measurements without \
                          ramp method are no longer supported. \
                          Use the unbuffered script!")
                    raise e
                    
                if trigger_type == "manual":
                    pass
    
                if trigger_type == "hardware":
                    try:
                        trigger_start()
                    except NameError as e:
                        print("Please set a trigger or define a trigger_start method")
                        raise e
    
                elif trigger_type == "software":
                    for buffer in self.buffers:
                        buffer.force_trigger()
                    logging.info("You are using software trigger, which \
                                    can lead to significant delays between \
                                    measurement instruments! Only recommended\
                                    for debugging.")
                        
                while not all(buffer.is_finished() for buffer in list(self.buffers)):
                    sleep(0.1)
                try:
                    trigger_reset()
                except:
                    logging.info("No method to reset the trigger defined. \
                        As you are doing a 2D Sweep, this can have undesired \
                        consequences!")
    
                results = self.readout_buffers()
                datasaver.add_result((slow_param, setpoint),
                                     (fast_param, fast_sweep.get_setpoints()),
                                     *results,
                                     *static_gettables,)
        datasets.append(datasaver.dataset)
        return datasets

    
