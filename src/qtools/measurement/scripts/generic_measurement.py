from time import sleep

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
from qtools.utils.utils import _validate_mapping


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
        sleep(wait_time)
        for sweep, dynamic_parameter in zip(self.dynamic_sweeps, self.dynamic_parameters):
            if include_gate_name:
                measurement_name = f"{self.metadata.measurement.name} {dynamic_parameter['gate']}"
            else:
                measurement_name = self.metadata.measurement.name or "measurement"
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
                    measurement_name=measurement_name,
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
            measurement_name=self.metadata.measurement.name or "measurement",
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
            measurement_name=self.metadata.measurement.name or "measurement",
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
        auto_naming = self.settings.get("auto_naming", False)
        if auto_naming:
            self.metadata.measurement.name = "Timetrace"
        meas = Measurement(name=self.metadata.measurement.name or "Timetrace")
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
        
        # meas.register_parameter(timer)
        for dynamic_sweep, dynamic_parameter in zip(self.dynamic_sweeps, self.dynamic_parameters):
            if include_gate_name:
                if self.metadata is None:
                    measurement_name = f"1D Sweep {dynamic_parameter['gate']}"
                else: 
                    measurement_name = f"{self.metadata.measurement.name} {dynamic_parameter['gate']}"
            else:
                measurement_name = self.metadata.measurment.name or "Buffered 1D Sweep"
            # if self.settings.get("log_idle_params", True):
            #     idle_channels = [entry for entry  in self.dynamic_channels if entry!=sweep.param]
            #     measured_channels = set((*self.gettable_channels, *idle_channels))
            # else:
            #     measured_channels = set(self.gettable_channels)
            #TODO: Find more elegant solution, maybe refactor initialize and lists?
            self.properties[
                dynamic_parameter["gate"]][dynamic_parameter["parameter"]
                                           ]["_is_triggered"] = True
            dynamic_param = dynamic_sweep.param
            meas = Measurement(name=measurement_name)
            meas.register_parameter(dynamic_param)

            for parameter in self.gettable_channels:
                meas.register_parameter(
                    parameter,
                    setpoints=[
                        dynamic_param,
                    ],
                )
                # Set trigger to low here
            with meas.run() as datasaver:
                self.initialize()
                data = {}
                results = []
                # start = timer.reset_clock()
                # Add check if all gettable parameters have buffer?
                self.ready_buffers()

                if trigger_type == "manual":
                    try:
                        dynamic_param.root_instrument._qtools_ramp(
                            [dynamic_param],
                            end_values=[dynamic_sweep.get_setpoints()[-1]],
                            ramp_time=self.buffer_settings["duration"],
                            sync_trigger=sync_trigger,
                        )
                    except AttributeError:
                        print("No ramp method found. Setting setpoints manually")
                        print(
                            "It is strongly advised to use unbuffered measurements, when no ramp method is available!"
                        )
                        for v in dynamic_sweep.get_setpoints():
                            dynamic_param.set(v)
                            sleep(dynamic_sweep._delay)

                if trigger_type == "hardware":
                    # Set trigger to high here
                    dynamic_param.root_instrument._qtools_ramp(
                        [dynamic_param],
                        end_values=[dynamic_sweep.get_setpoints()[-1]],
                        ramp_time=self.buffer_settings["duration"],
                    )
                    try:
                        trigger_start()
                    except AttributeError:
                        print("Please set a trigger or define a trigger_start method")
                    pass

                elif trigger_type == "software":
                    dynamic_param.root_instrument._qtools_ramp(
                        [dynamic_param],
                        end_values=[dynamic_sweep.get_setpoints()[-1]],
                        ramp_time=self.buffer_settings["duration"],
                    )
                    for buffer in self.buffers:
                        buffer.force_trigger()

                while not list(self.buffers)[0].is_finished():
                    sleep(0.1)
                try:
                    trigger_reset()
                except:
                    print("No method to reset the trigger defined.")

                results = self.readout_buffers()
                # TODO: Append values from other dynamic parameters
                datasaver.add_result((dynamic_param, dynamic_sweep.get_setpoints()), *results)
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

        datasets = []
        self.initialize()
        # meas.register_parameter(timer)
        for dynamic_sweep, dynamic_parameter in zip(self.dynamic_sweeps, self.dynamic_parameters):
            if include_gate_name:
                if self.metadata is None:
                    measurement_name = f"1D Sweep {dynamic_parameter['gate']}"
                else: 
                    measurement_name = f"{self.metadata.measurement.name} {dynamic_parameter['gate']}"
            else:
                measurement_name = self.metadata.measurment.name or "Buffered 1D Sweep"
            # if self.settings.get("log_idle_params", True):
            #     idle_channels = [entry for entry  in self.dynamic_channels if entry!=sweep.param]
            #     measured_channels = set((*self.gettable_channels, *idle_channels))
            # else:
            #     measured_channels = set(self.gettable_channels)
            dynamic_param = dynamic_sweep.param
            meas = Measurement(name=measurement_name)
            meas.register_parameter(dynamic_param)

            for parameter in self.gettable_channels:
                meas.register_parameter(
                    parameter,
                    setpoints=[
                        dynamic_param,
                    ],
                )
                # Set trigger to low here
            self.ready_buffers()
            with meas.run() as datasaver:
                data = {}
                results = []
                set_points = []
                for iiter in range(0, iterations):
                    for buffer in self.buffers:
                        buffer.start()
                    if iiter % 2 == 0:
                        end_value = dynamic_sweep.get_setpoints()[-1]
                        set_points.extend(dynamic_sweep.get_setpoints())
                    else:
                        end_value = dynamic_sweep.get_setpoints()[0]
                        _revers = list(reversed(dynamic_sweep.get_setpoints()))
                        set_points.extend(_revers)

                    # Add check if all gettable parameters have buffer?
                    if trigger_type == "manual":
                        try:
                            dynamic_param.root_instrument._qtools_ramp(
                                [dynamic_param],
                                end_values=[end_value],
                                ramp_time=self.buffer_settings["duration"],
                                sync_trigger=sync_trigger,
                            )
                        except AttributeError:
                            print("No ramp method found. Setting setpoints manually")
                            print(
                                "It is strongly advised to use unbuffered measurements, when no ramp method is available!"
                            )
                            for v in dynamic_sweep.get_setpoints():
                                dynamic_param.set(v)
                                sleep(dynamic_sweep._delay)

                    if trigger_type == "hardware":
                        # Set trigger to high here
                        try:
                            trigger_start()
                        except:
                            print("Please set a trigger or define a trigger_start method")
                        pass

                    elif trigger_type == "software":
                        dynamic_param.root_instrument._qtools_ramp(
                            [dynamic_param],
                            end_values=[end_value],
                            ramp_time=self.buffer_settings["duration"],
                        )
                        for buffer in self.buffers:
                            buffer.force_trigger()

                    while not list(self.buffers)[0].is_finished():
                        sleep(0.1)
                    try:
                        trigger_reset()
                    except:
                        print("No method to reset the trigger defined.")
                    _temp = self.readout_buffers()
                    if iiter == 0:
                        results = _temp
                    else:
                        for ii in range(len(_temp)):
                            results[ii][1].extend(_temp[ii][1])
                    # TODO: Append values from other dynamic parameters

                datasaver.add_result((dynamic_param, set_points), *results)
                datasets.append(datasaver.dataset)
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
        # meas.register_parameter(timer)
        if self.metadata is None:
            measurement_name = "2D Sweep"
        else: 
            measurement_name = f"{self.metadata.measurement.name}"

        if include_gate_name:
            gate_names=[gate["gate"] for gate in self.dynamic_parameters]
            measurement_name += str(gate_names)
        
        meas = Measurement(name=measurement_name)
            
        if reverse_param_order:
            slow_param = self.dynamic_channels[1]
            slow_sweep = self.dynamic_sweeps[1]
            fast_param = self.dynamic_channels[0]
            fast_sweep = self.dynamic_sweeps[0]
            self.properties[
                self.dynamic_parameters[1]["gate"]][self.dynamic_parameters[1]["parameter"]
                                           ]["_is_triggered"] = True
        else:
            slow_param = self.dynamic_channels[0]
            slow_sweep = self.dynamic_sweeps[0]
            fast_param = self.dynamic_channels[1]
            fast_sweep = self.dynamic_sweeps[1]
            self.properties[
                self.dynamic_parameters[0]["gate"]][self.dynamic_parameters[0]["parameter"]
                                           ]["_is_triggered"] = True
        
        self.initialize()            

        for dynamic_param in self.dynamic_channels:
            meas.register_parameter(dynamic_param)

        for parameter in self.gettable_channels:
            meas.register_parameter(
                parameter,
                setpoints=[slow_param, fast_param,],
            )
                # Set trigger to low here
        with meas.run() as datasaver:
            data = {}
            results = []
            # start = timer.reset_clock()
            # Add check if all gettable parameters have buffer?
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

                if trigger_type == "manual":
                    try:
                        fast_param.root_instrument._qtools_ramp(
                            [fast_param],
                            end_values=[fast_sweep.get_setpoints()[-1]],
                            ramp_time=self.buffer_settings["duration"],
                            sync_trigger=sync_trigger,
                        )
                    except:
                        print("No ramp method found. Setting setpoints manually")
                        print(
                            "It is strongly advised to use unbuffered \measurements, when no ramp method is available!"
                        )
                        for v in fast_sweep.get_setpoints():
                            fast_param.set(v)
                            sleep(fast_sweep._delay)
    
                if trigger_type == "hardware":
                    # Set trigger to high here
                    try:
                        trigger_start()
                    except:
                        print("Please set a trigger or define a trigger_start method")
                    pass
    
                elif trigger_type == "software":
                    fast_param.root_instrument._qtools_ramp(
                        [fast_param],
                        end_values=[fast_sweep.get_setpoints()[-1]],
                        ramp_time=self.buffer_settings["duration"],
                    )
                    for buffer in self.buffers:
                        buffer.force_trigger()
    
                while not list(self.buffers)[0].is_finished():
                    sleep(0.1)
                try:
                    trigger_reset()
                except:
                    print("No method to reset the trigger defined. \
                          As you are doing a 2D Sweep, this can have undesired \
                              consequences!")
    
                results = self.readout_buffers()
                # TODO: Append values from other dynamic parameters
                datasaver.add_result((slow_param, setpoint),
                                     (fast_param, fast_sweep.get_setpoints()),
                                     *results)
                datasets.append(datasaver.dataset)
        return datasets
