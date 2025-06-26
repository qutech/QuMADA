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
# - Bertha Lab Setup
# - Daniel Grothe
# - Max Lennart Oberländer
# - Sionludi Lab
# - Tobias Hangleiter

import logging
from time import sleep, time

import numpy as np
from qcodes.dataset import dond
from qcodes.parameters.specialized_parameters import ElapsedTimeParameter

from qumada.instrument.buffers import is_bufferable
from qumada.measurement.doNd_enhanced.doNd_enhanced import (
    _interpret_breaks,
    do1d_parallel_asym,
    dond_custom,
)
from qumada.measurement.measurement import CustomSweep, MeasurementScript
from qumada.utils.ramp_parameter import ramp_or_set_parameters
from qumada.utils.utils import _validate_mapping, naming_helper

logger = logging.getLogger(__name__)


class Generic_1D_Sweep(MeasurementScript):
    def run(self, **dond_kwargs) -> list:
        """
        Perform 1D sweeps for all dynamic parameters, one after another.

        Dynamic parameters that are not currently active are kept at their
        "value" value.

        Parameters
        ----------
        **dond_kwargs : dict
            Additional keyword arguments passed to the `dond` method.

        Attributes (via settings)
        -------------------------
        wait_time : float, optional
            Wait time (in seconds) between initialization and each measurement.
            Default is 5.
        include_gate_name : bool, optional
            If True, append the name of the ramped gate to the measurement name.
            Default is True.
        ramp_speed : float, optional
            Speed at which parameters are ramped during initialization.
            Default is 0.3.
        ramp_time : float, optional
            Maximum time (in seconds) allowed for ramping each parameter during
            initialization. Default is 10.
        log_idle_params : bool, optional
            If True, record dynamic parameters kept constant during sweeps.
            Default is True.
        backsweep_after_break : bool, optional
            If True, parameter will be ramped through the setpoints set so far
            in reverse order once a break condition is triggered. For normal ramps,
            this results in a backsweep to the starting point. Default is False.

        Returns
        -------
        list
            A list of QCoDeS datasets for each sweep.
        """
        wait_time = self.settings.get("wait_time", 5)
        backsweep_after_break = self.settings.get("backsweep_after_break", False)
        include_gate_name = self.settings.get("include_gate_name", True)
        naming_helper(self, default_name="1D Sweep")
        data = list()
        self.generate_lists()
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
            inactive_channels = [chan for chan in self.dynamic_channels if chan != sweep.param]
            self.initialize(inactive_dyn_channels=inactive_channels)
            sleep(wait_time)
            if backsweep_after_break:
                sweep._setpoints = np.array([*sweep._setpoints, *sweep._setpoints[::-1]])
                sweep._num_points = len(sweep._setpoints)
            data.append(
                self._dond(
                    sweep,
                    *measured_channels,
                    measurement_name=self._measurement_name,
                    break_condition=_interpret_breaks(self.break_conditions),
                    backsweep_after_break=backsweep_after_break,
                    dond_module_path="qumada.measurement.doNd_enhanced.doNd_enhanced",
                    dond_fn_name="dond_custom",
                    **dond_kwargs,
                )
            )

        self.clean_up()
        return data


class Generic_nD_Sweep(MeasurementScript):
    def run(self, **dond_kwargs):
        """
        Perform an n-dimensional sweep for n dynamic parameters.

        Parameters
        ----------
        **dond_kwargs : dict
            Additional keyword arguments passed to the `dond` method.

        Attributes (via settings)
        -------------------------
        wait_time : float, optional
            Wait time (in seconds) between initialization and each measurement.
            Default is 5.
        include_gate_name : bool, optional
            If True, append the names of the ramped gates to the measurement name.
            Default is True.
        ramp_speed : float, optional
            Speed at which parameters are ramped during initialization.
            Default is 0.3.
        ramp_time : float, optional
            Maximum time (in seconds) allowed for ramping each parameter during
            initialization. Default is 10.

        Returns
        -------
        QCoDeS dataset
            Dataset containing measurement data.
        """
        self.buffered = False
        self.initialize()
        wait_time = self.settings.get("wait_time", 5)
        include_gate_name = self.settings.get("include_gate_name", True)
        naming_helper(self, default_name="nD Sweep")
        if include_gate_name:
            measurement_name = f"{self.measurement_name} {[gate['gate'] for gate in self.dynamic_parameters]}"
        else:
            try:
                measurement_name = self.measurement_name
            except Exception:
                measurement_name = "measurement"

        for sweep in self.dynamic_sweeps:
            ramp_or_set_parameters([sweep._param], [sweep.get_setpoints()[0]])
        sleep(wait_time)
        data = dond(
            *tuple(self.dynamic_sweeps),
            *tuple(self.gettable_channels),
            measurement_name=measurement_name,
            break_condition=_interpret_breaks(self.break_conditions),
            use_threads=True,
            **dond_kwargs,
        )
        self.clean_up()
        return data


class Generic_1D_parallel_asymm_Sweep(MeasurementScript):
    def run(self):
        raise Exception(
            "This script was renamed to Generic_1D_parallel_Sweep \
                        and is no longer available. \
                        Please use  Generic_1D_parallel_Sweep instead! \
                        No measurement was started."
        )


class Generic_1D_parallel_Sweep(MeasurementScript):
    """
    Sweeps all dynamic parameters in parallel.

    Supports different sweep rates and setpoints for different parameters.
    All parameters must have the same length.

    Parameters
    ----------
    **kwargs : dict
        Additional keyword arguments:
        - `backsweep_after_break` (bool): Sweeps backwards after a break condition
          is triggered. Default is `False`.
        - `wait_time` (float): Wait time in seconds before starting the sweep. Default is `5`.

    Returns
    -------
    data : Any
        The collected data from the parallel sweep.
    """

    def run(self, **do1d_kwargs):
        naming_helper(self, default_name="Parallel 1D Sweep")
        self.initialize()
        backsweep_after_break = self.settings.get("backsweep_after_break", False)
        wait_time = self.settings.get("wait_time", 5)
        dynamic_params = list()
        for sweep in self.dynamic_sweeps:
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
        self.clean_up()
        return data


class Timetrace(MeasurementScript):
    """
    Timetrace measurement.

    Records data over a specified duration with a given timestep. Note that
    the actual timesteps can vary as the recording time for each datapoint
    is not constant. However, the elapsed time recorded is accurate.

    Parameters
    ----------
    **kwargs : dict
        Additional keyword arguments:
        - `duration` (float): Duration of the measurement in seconds. Default is `300`.
        - `timestep` (float): Time interval between measurements in seconds. Default is `1`.
        - `auto_naming` (bool): If `True`, renames the measurement automatically to "Timetrace". Default is `False`.

    Returns
    -------
    dataset : qcodes.dataset.measurements.Measurement
        The collected dataset containing the recorded measurements.
    """

    def run(self):
        self.initialize(dyn_ramp_to_val=True)
        duration = self.settings.get("duration", 300)
        timestep = self.settings.get("timestep", 1)
        timer = ElapsedTimeParameter("time")
        naming_helper(self, default_name="Timetrace")
        meas = self._new_measurement(name=self.measurement_name)
        meas.register_parameter(timer)
        for parameter in [*self.gettable_channels, *self.dynamic_channels]:
            meas.register_parameter(
                parameter,
                setpoints=[
                    timer,
                ],
            )
        with meas.run() as datasaver:
            timer.reset_clock()
            while timer() < duration:
                now = timer()
                results = [(channel, channel.get()) for channel in [*self.gettable_channels, *self.dynamic_channels]]
                datasaver.add_result((timer, now), *results)
                sleep(timestep)
        dataset = datasaver.dataset
        self.clean_up()
        return dataset


class Timetrace_buffered(MeasurementScript):
    """
    Performs a buffered timetrace measurement.

    The measurement duration and timestep are determined via the buffer settings.
    Dynamic parameters are currently not supported.
    The method does not support "manual" triggering mode, as no ramp is started.
    Using "software" triggering is fine if only one buffered instrument is used;
    otherwise, "hardware" triggering is recommended.
    TODO: Add duration arg

    Parameters
    ----------
    dyn_ramp_to_val : bool, optional
        If True, dynamic parameters are ramped to their respective values during initialization.
    trigger_start : str, optional
        Specifies the trigger start method. Default is "software".
    trigger_reset : callable, optional
        Function to reset the trigger after measurement. Default is None.
    trigger_type : str, optional
        Specifies the type of trigger to use. Can be "software" or "hardware".
        Default is "software".
    auto_naming : bool, optional
        Renames measurement automatically to "Timetrace" if True.

    Returns
    -------
    datasets : list
        A list of QCoDeS datasets containing the measurement results.

    Raises
    ------
    Exception
        If unsupported triggering mode is selected or if a channel cannot be buffered and is not static gettable.

    Notes
    -----
    - Ensure that the buffer settings are properly configured before running the measurement.
    - For "hardware" triggering, the `trigger_start` method must be defined.
    - Dynamic parameters are treated as "static gettable"

    """

    def run(self):
        self.initialize(dyn_ramp_to_val=True)
        # duration = self.settings.get("duration", 300)
        # timestep = self.settings.get("timestep", 1)
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
        naming_helper(self, default_name="Timetrace")
        meas = self._new_measurement(name=self.measurement_name)

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
                    setpoints=[
                        timer,
                    ],
                )
            elif channel in self.static_channels:
                del_channels.append(channel)
                del_params.append(parameter)
                meas.register_parameter(
                    channel,
                    setpoints=[
                        timer,
                    ],
                )
                parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                static_gettables.append((channel, [parameter_value for _ in range(int(self.buffered_num_points))]))
            else:
                raise Exception(f"{channel} cannot be buffered and is not static gettable")
        for channel in del_channels:
            self.gettable_channels.remove(channel)
        for param in del_params:
            self.gettable_parameters.remove(param)
        for parameter, channel in zip(self.dynamic_parameters, self.dynamic_channels):
            parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
            static_gettables.append((channel, [parameter_value for _ in range(int(self.buffered_num_points))]))
        with meas.run() as datasaver:
            # start = timer.reset_clock()
            self.ready_buffers()

            if trigger_type == "manual":
                raise Exception("Manual triggering not supported by Timetrace.")
            if trigger_type == "hardware":
                # Set trigger to high here
                try:
                    trigger_start()
                except Exception:
                    print("Please set a trigger or define a trigger_start method")
                pass

            elif trigger_type == "software":
                for buffer in self.buffers:
                    buffer.force_trigger()

            while not all(buffer.is_finished() for buffer in list(self.buffers)):
                sleep(0.1)
            try:
                trigger_reset()
            except Exception:
                print("No method to reset the trigger defined.")

            results = self.readout_buffers(timestamps=True)
            # TODO: Append values from other dynamic parameters
            datasaver.add_result(
                (timer, results.pop(-1)),
                *results,
                *static_gettables,
            )
            datasets.append(datasaver.dataset)
            self.clean_up()
        return datasets


class Timetrace_with_sweeps(MeasurementScript):
    """
    Performs a timetrace measurement with dynamic sweeps.

    Duration and timestep can be set as keyword arguments, both in seconds.
    Note that the timesteps may vary due to variable recording times per data point.
    The elapsed time recorded is accurate.

    Parameters
    ----------
    duration : int, optional
        Total duration of the measurement in seconds. Default is 300.
    timestep : int, optional
        Time between sweeps in seconds. Default is 1.

    Returns
    -------
    dataset : qcodes.dataset.data_set.DataSet
        A QCoDeS dataset containing the measurement results.

    Notes
    -----
    - Dynamic sweeps are executed at each timestep during the measurement.

    """

    def run(self):
        self.initialize()
        duration = self.settings.get("duration", 300)
        timestep = self.settings.get("timestep", 1)
        # backsweeps = self.settings.get("backsweeps", False)
        timer = ElapsedTimeParameter("time")
        meas = self._new_measurement(name=self.metadata.measurement.name or "timetrace")
        meas.register_parameter(timer)
        setpoints = [timer]
        for parameter in self.dynamic_channels:
            meas.register_parameter(parameter)
            setpoints.append(parameter)
        for parameter in self.gettable_channels:
            meas.register_parameter(parameter, setpoints=setpoints)
        with meas.run() as datasaver:
            timer.reset_clock()
            while timer() < duration:
                for sweep in self.dynamic_sweeps:
                    ramp_or_set_parameters([sweep._param], [sweep.get_setpoints()[0]], ramp_time=timestep)
                now = timer()
                for i in range(0, len(self.dynamic_sweeps[0].get_setpoints())):
                    for sweep in self.dynamic_sweeps:
                        sweep._param.set(sweep.get_setpoints()[i])
                    set_values = [(sweep._param, sweep.get_setpoints()[i]) for sweep in self.dynamic_sweeps]
                    results = [(channel, channel.get()) for channel in self.gettable_channels]
                    datasaver.add_result((timer, now), *set_values, *results)
                # sleep(timestep)
        dataset = datasaver.dataset
        self.clean_up()
        return dataset


class Timetrace_with_Sweeps_buffered(MeasurementScript):
    """
    Timetrace measurement, duration and timestep are set via the buffer settings.
    It is fine to use software triggering here, as long as only one buffered
    instrument is used, else you should use "hardware".

    Duration and timestep are determined via buffer settings.
    This method does not support dynamic parameters and cannot use
    "manual" triggering mode. Use "software" or "hardware" triggers.

    Parameters
    ----------
    duration : int, optional
        Total duration of the measurement in seconds. Default is 300.
    trigger_start : str, optional
        Trigger start method. Default is "software".
    trigger_reset : callable, optional
        Function to reset the trigger after measurement. Default is None.
    sync_trigger : int, optional
        Number of the used sync trigger (QDacs only). Default is None.
    trigger_type : str, optional
        Type of trigger to use ("software", "hardware", "manual"). Default is "software".

    Returns
    -------
    datasets : list
        A list of QCoDeS datasets containing the measurement results.

    Raises
    ------
    AttributeError
        If the required methods for triggering or ramping are not defined.
    TypeError
        If no reset method for the trigger is defined.

    Notes
    -----
    - Dynamic sweeps are executed at each timestep during the measurement.
    """

    def run(self):
        self.initialize()
        duration = self.settings.get("duration", 300)
        buffer_timeout_multiplier = self.settings.get("buffer_timeout_multiplier", 20)
        # timestep = self.settings.get("timestep", 1)
        timer = ElapsedTimeParameter("time")
        TRIGGER_TYPES = ["software", "hardware", "manual"]
        trigger_start = self.settings.get("trigger_start", "software")  # TODO: this should be set elsewhere
        trigger_reset = self.settings.get("trigger_reset", None)
        sync_trigger = self.settings.get("sync_trigger", None)
        trigger_type = _validate_mapping(
            self.settings.get("trigger_type"),
            TRIGGER_TYPES,
            default="software",
            default_key_error="software",
        )
        self.buffered = True
        datasets = []
        self.generate_lists()
        naming_helper(self, default_name="Timetrace with sweeps")
        meas = self._new_measurement(name=self.measurement_name)
        meas.register_parameter(timer)

        for dynamic_param in self.dynamic_parameters:
            self.properties[dynamic_param["gate"]][dynamic_param["parameter"]]["_is_triggered"] = True
        for dyn_channel in self.dynamic_channels:
            meas.register_parameter(dyn_channel)

        # Block required to log gettable and static parameters that are not
        # buffarable (e.g. Dac Channels)
        static_gettables = []
        for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
            if is_bufferable(channel) and channel not in self.static_gettable_channels:
                meas.register_parameter(channel, setpoints=[timer, *self.dynamic_channels])
            elif channel in self.static_gettable_channels:
                meas.register_parameter(channel, setpoints=[timer, *self.dynamic_channels])
                parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                static_gettables.append((channel, [parameter_value for _ in range(int(self.buffered_num_points))]))
        start = time()
        with meas.run() as datasaver:
            try:
                trigger_reset()
            except TypeError:
                logger.info("No method to reset the trigger defined.")
            while time() - start < duration:
                self.initialize()
                self.ready_buffers()
                t = time() - start
                try:
                    self.trigger_measurement(
                        parameters=self.dynamic_channels,
                        setpoints=[sweep.get_setpoints() for sweep in self.dynamic_sweeps],
                        method="ramp",
                        sync_trigger=sync_trigger,
                    )

                    results = self.readout_buffers(timestamps=True)
                    dynamic_param_results = [
                        (dyn_channel, sweep.get_setpoints())
                        for dyn_channel, sweep in zip(self.dynamic_channels, self.dynamic_sweeps)
                    ]
                    results.pop(-1)  # removes timestamps from results
                    datasaver.add_result(
                        (timer, t),
                        *dynamic_param_results,
                        *results,
                        *static_gettables,
                    )
                except AttributeError as ex:
                    logger.error(
                        "Exception: This instrument probably does not have a \
                          qtools_ramp method. Buffered measurements without \
                          ramp method are no longer supported. \
                          Use the unbuffered script!"
                    )
                    raise ex
                except TimeoutError:
                    logger.error(f"A timeout error occured. Skipping line at time {t}.")
                    # results = self.readout_buffers(timestamps=True)
            self.clean_up()
        datasets.append(datasaver.dataset)
        return datasets


class Generic_1D_Sweep_buffered(MeasurementScript):
    """
    Executes a buffered 1D sweep measurement. Works only with ramps (no pulses). Supports compensation.

    - "software": Sends a software command to each buffer and dynamic parameter to start data acquisition.
                   Timing might have slight offsets.
    - "hardware": Runs trigger_start to start the measurement., either preconfigured or started manually.
    - "manual"  : User-controlled trigger setup, useful for synchronized trigger outputs (e.g., with QDac).

    Parameters
    ----------
    trigger_start : str or callable, optional
        A callable to start the measurement or the keyword "manual" for user-triggered setup.
        Default is "manual".
    trigger_reset : callable, optional
        A callable to reset the trigger after measurement. Default is None.
    trigger_type : str, optional
        Type of trigger to use ("software", "hardware", "manual"). Default is "software".
    include_gate_name : bool, optional
        If True, appends the name of the ramped gates to the measurement name. Default is True.
    sync_trigger : int, optional
        Number of the used sync trigger (QDacs only). Default is None.

    Returns
    -------
    datasets : list of qcodes.dataset.data_set.DataSet
        A list of datasets containing the measurement results.

    Raises
    ------
    AttributeError
        If a required method (e.g., for ramping) is missing.
    TypeError
        If no reset method for the trigger is defined.
    Exception
        If setpoints of a parameter exceed defined limits.

    Notes
    -----
    - This script supports buffered measurements, with dynamic and static parameters.
    - It ensures that all setpoints and compensating channels remain within their defined limits.
    - Proper configuration of buffers and triggers is essential for accurate results.
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
        measurement_name = naming_helper(self, default_name="1D Sweep")
        # meas.register_parameter(timer)

        for i in range(len(self.dynamic_sweeps.copy())):
            # dynamic_sweep and dynamic_parameter are from copy and not
            # affected by changes made to parameter in original list!
            self.measurement_name = measurement_name
            dynamic_parameter = self.dynamic_parameters[i]
            if include_gate_name:
                self.measurement_name += f" {dynamic_parameter['gate']}"
            self.properties[dynamic_parameter["gate"]][dynamic_parameter["parameter"]]["_is_triggered"] = True

            dynamic_param = self.dynamic_sweeps[i].param
            inactive_channels = [chan for chan in self.dynamic_channels if chan != dynamic_param]
            self.initialize(inactive_dyn_channels=inactive_channels)
            meas = self._new_measurement(name=self.measurement_name)
            meas.register_parameter(dynamic_param)
            for c_param in self.active_compensating_channels:
                meas.register_parameter(
                    c_param,
                    setpoints=[
                        dynamic_param,
                    ],
                )
            static_gettables = []
            for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
                if is_bufferable(channel) and channel not in self.static_gettable_channels:
                    meas.register_parameter(
                        channel,
                        setpoints=[
                            dynamic_param,
                        ],
                    )
                elif channel in self.static_gettable_channels:
                    parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                    parameter_value = channel.get()
                    static_gettables.append((channel, [parameter_value for _ in range(int(self.buffered_num_points))]))
            for parameter, channel in zip(self.dynamic_parameters, self.dynamic_channels):
                if channel != dynamic_param:
                    try:
                        parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                    except KeyError:
                        logger.error(
                            "An idle dynamic parameter has no value assigned\
                              and cannot be logged!"
                        )
                        break
                    static_gettables.append((channel, [parameter_value for _ in range(int(self.buffered_num_points))]))
            for param in static_gettables:
                meas.register_parameter(
                    param[0],
                    setpoints=[
                        dynamic_param,
                    ],
                )
            active_comping_sweeps = []
            for j in range(len(self.active_compensating_channels)):
                index = self.compensating_parameters.index(self.active_compensating_parameters[j])
                active_comping_setpoints = self.compensating_parameters_values[index] + sum(
                    [sweep.get_setpoints() for sweep in self.compensating_sweeps[j]]
                )
                if min(active_comping_setpoints) < min(self.compensating_limits[index]) or max(
                    active_comping_setpoints
                ) > max(self.compensating_limits[index]):
                    raise Exception(f"Setpoints of {self.compensating_parameters[index]} exceed limits!")
                sweep_delay = self.compensating_sweeps[j][-1]._delay
                active_comping_sweeps.append(
                    CustomSweep(
                        param=self.active_compensating_channels[j],
                        setpoints=active_comping_setpoints,
                        delay=sweep_delay,
                    )
                )

            meas.write_period = 0.5

            with meas.run() as datasaver:

                dynamic_sweep = self.dynamic_sweeps[i]
                try:
                    trigger_reset()
                except TypeError:
                    logger.info("No method to reset the trigger defined.")
                results = []
                self.ready_buffers()
                self.trigger_measurement(
                    parameters=[dynamic_param, *self.active_compensating_channels],
                    setpoints=[
                        dynamic_sweep.get_setpoints(),
                        *[sweep.get_setpoints for sweep in active_comping_sweeps],
                    ],
                    method="ramp",
                    sync_trigger=sync_trigger,
                )

                results = self.readout_buffers()
                comp_results = []
                for ch, sw in zip(self.active_compensating_channels, active_comping_sweeps):
                    comp_results.append((ch, sw.get_setpoints()))
                datasaver.add_result(
                    (dynamic_param, dynamic_sweep.get_setpoints()),
                    *comp_results,
                    *results,
                    *static_gettables,
                )
                datasets.append(datasaver.dataset)
                self.properties[dynamic_parameter["gate"]][dynamic_parameter["parameter"]]["_is_triggered"] = False
                self.clean_up()
        return datasets


class Generic_1D_Hysteresis_buffered(MeasurementScript):
    """
    Performs a buffered 1D hysteresis measurement (back and foresweeps).
    Each iteration corresponds to one fore- and one backsweep.

    This measurement supports dynamic and static parameters and handles multiple
    triggering methods:

    - "software": Sends a software command to each buffer and dynamic parameters
                   to start data acquisition and ramping. Timing might be slightly off.
    - "hardware": Runs trigger_start to start the measurement.. Can be preconfigured
                   or manually adjusted (requires `trigger_start` callable).
    - "manual": Trigger setup is user-defined, useful for synchronized trigger outputs.

    Parameters
    ----------
    iterations : int
        Defines how many sweeps are done. Each iteration corresponds to one fore- and one backsweep.
    trigger_start : str or callable, optional
        A callable to start the measurement or "manual" for user-triggered setup.
        Default is "manual".
    trigger_reset : callable, optional
        A callable to reset the trigger after measurement. Default is None.
    trigger_type : str, optional
        Type of trigger to use ("software", "hardware", "manual"). Default is "software".
    sync_trigger : int, optional
        Number of the used sync trigger (QDacs only). Default is None.
    include_gate_name : bool, optional
        If True, appends the name of the ramped gates to the measurement name. Default is True.

    Returns
    -------
    datasets : list of qcodes.dataset.data_set.DataSet
        A list of datasets containing the measurement results.

    Raises
    ------
    AttributeError
        If a required method (e.g., for ramping) is missing.
    TypeError
        If no reset method for the trigger is defined.
    Exception
        If static or dynamic parameters have invalid configurations.

    Notes
    -----
    - This script performs back-and-forth sweeps (hysteresis) for dynamic parameters.
    - Proper configuration of buffers and triggers is required for accurate results.
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
        iterations *= 2
        datasets = []
        self.generate_lists()
        measurement_name = naming_helper(self, default_name="1D Sweep")
        # meas.register_parameter(timer)
        for dynamic_sweep, dynamic_parameter in zip(self.dynamic_sweeps.copy(), self.dynamic_parameters.copy()):
            self.measurement_name = measurement_name
            if include_gate_name:
                self.measurement_name += f" {dynamic_parameter['gate']}"
            self.properties[dynamic_parameter["gate"]][dynamic_parameter["parameter"]]["_is_triggered"] = True
            dynamic_param = dynamic_sweep.param
            meas = self._new_measurement(name=self.measurement_name)
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
                    parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                    static_gettables.append((channel, [parameter_value for _ in range(int(self.buffered_num_points))]))
            for parameter, channel in zip(self.dynamic_parameters, self.dynamic_channels):
                if channel != dynamic_param:
                    try:
                        parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                    except KeyError:
                        logger.error(
                            "An idle dynamic parameter has no value assigned\
                              and cannot be logged!"
                        )
                        break
                    static_gettables.append((channel, [parameter_value for _ in range(int(self.buffered_num_points))]))
            for param in static_gettables:
                meas.register_parameter(
                    param[0],
                    setpoints=[
                        dynamic_param,
                    ],
                )
            for channel in del_channels:
                self.gettable_channels.remove(channel)
            for param in del_params:
                self.gettable_parameters.remove(param)

            try:
                trigger_reset()
            except TypeError:
                logger.info("No method to reset the trigger defined.")

            with meas.run() as datasaver:
                inactive_channels = [chan for chan in self.dynamic_channels if chan != dynamic_param]
                self.initialize(inactive_dyn_channels=inactive_channels)
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
                        dynamic_param.root_instrument._qumada_ramp(
                            [dynamic_param],
                            start_values=None,
                            end_values=[end_value],
                            ramp_time=self._burst_duration,
                            sync_trigger=sync_trigger,
                        )
                    except AttributeError as ex:
                        logger.error(
                            "Exception: This instrument probably does not have a \
                              a qumada_ramp method. Buffered measurements without \
                              ramp method are no longer supported. \
                              Use the unbuffered script!"
                        )
                        raise ex

                    if trigger_type == "manual":
                        pass
                    if trigger_type == "hardware":
                        try:
                            trigger_start()
                        except AttributeError as ex:
                            print("Please set a trigger or define a trigger_start method")
                            raise ex

                    elif trigger_type == "software":
                        for buffer in self.buffers:
                            buffer.force_trigger()
                        logger.info(
                            "You are using software trigger, which \
                                        can lead to significant delays between \
                                        measurement instruments! Only recommended\
                                        for debugging."
                        )
                    while not all(buffer.is_finished() for buffer in list(self.buffers)):
                        sleep(0.1)
                    try:
                        trigger_reset()
                    except TypeError:
                        logger.info("No method to reset the trigger defined.")

                    results = self.readout_buffers()
                    datasaver.add_result(
                        (dynamic_param, set_points),
                        *results,
                        *static_gettables,
                    )
                datasets.append(datasaver.dataset)
                self.properties[dynamic_parameter["gate"]][dynamic_parameter["parameter"]]["_is_triggered"] = False
                self.clean_up()
        return datasets


class Generic_2D_Sweep_buffered(MeasurementScript):
    """
    Executes a buffered 2D sweep measurement. Supports compensation.
    By default fist dynamic parameter is stepped (unbuffered) and the second one
    ramped.

    This script supports two dynamic parameters and multiple triggering methods:

    - "software": Sends a software command to each buffer and dynamic parameters
                   to start data acquisition and ramping. Timing might be slightly off.
    - "hardware": Runs trigger_start to start the measurement.. Can be preconfigured
                   or manually adjusted (requires `trigger_start` callable).
    - "manual": Trigger setup is user-defined, useful for synchronized trigger outputs.

    Parameters
    ----------
    trigger_start : str or callable, optional
        A callable to start the measurement.
    trigger_reset : callable, optional
        A callable to reset the trigger after measurement. Default is None.
    trigger_type : str, optional
        Type of trigger to use ("software", "hardware", "manual"). Default is "software".
    include_gate_name : bool, optional
        If True, appends the names of the ramped gates to the measurement name. Default is True.
    reset_time : float, optional
        Time to ramp the fast parameter back to the start value. Default is 0.
    reverse_param_order : bool, optional
        If True, switches the order of slow and fast parameters. Default is False.
    buffer_timeout_multiplier : int, optional
        Multiplier for buffer timeout duration relative to burst duration. Default is 20.

    Returns
    -------
    datasets : list of qcodes.dataset.data_set.DataSet
        A list of datasets containing the measurement results.

    Raises
    ------
    AttributeError
        If a required method (e.g., for ramping) is missing.
    TimeoutError
        If buffers fail to finish within the timeout duration.
    Exception
        If static or dynamic parameters have invalid configurations.

    Notes
    -----
    - Proper configuration of buffers and triggers is required for accurate results.
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
        buffer_timeout_multiplier = self.settings.get("buffer_timeout_multiplier", 20)
        datasets = []

        self.generate_lists()

        if len(self.dynamic_sweeps) != 2:
            raise Exception("The 2D workflow takes exactly two dynamic parameters! ")
        self.measurement_name = naming_helper(self, default_name="2D Sweep")
        if include_gate_name:
            gate_names = [gate["gate"] for gate in self.dynamic_parameters]
            self.measurement_name += f" {gate_names}"

        meas = self._new_measurement(name=self.measurement_name)

        if reverse_param_order:
            slow_param = self.dynamic_parameters[1]
            slow_channel = self.dynamic_channels[1]
            slow_sweep = self.dynamic_sweeps[1]
            fast_param = self.dynamic_parameters[0]
            fast_channel = self.dynamic_channels[0]
            fast_sweep = self.dynamic_sweeps[0]
            self.properties[self.dynamic_parameters[0]["gate"]][self.dynamic_parameters[0]["parameter"]][
                "_is_triggered"
            ] = True
        else:
            slow_param = self.dynamic_parameters[0]
            slow_channel = self.dynamic_channels[0]
            slow_sweep = self.dynamic_sweeps[0]
            fast_param = self.dynamic_parameters[1]
            fast_channel = self.dynamic_channels[1]
            fast_sweep = self.dynamic_sweeps[1]
            self.properties[self.dynamic_parameters[1]["gate"]][self.dynamic_parameters[1]["parameter"]][
                "_is_triggered"
            ] = True

        for dynamic_param in self.dynamic_channels:
            meas.register_parameter(dynamic_param)
        # -------------------
        static_gettables = []
        del_channels = []
        del_params = []
        for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
            if is_bufferable(channel):
                meas.register_parameter(
                    channel,
                    setpoints=[
                        slow_channel,
                        fast_channel,
                    ],
                )
            elif channel in self.static_channels:
                del_channels.append(channel)
                del_params.append(parameter)
                meas.register_parameter(
                    channel,
                    setpoints=[
                        slow_channel,
                        fast_channel,
                    ],
                )
                parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                static_gettables.append((channel, [parameter_value for _ in range(int(self.buffered_num_points))]))
        for channel in del_channels:
            self.gettable_channels.remove(channel)
        for param in del_params:
            self.gettable_parameters.remove(param)
        # --------------------------
        self.initialize()
        # ####################Sensor compensation#####################
        for c_param in self.active_compensating_channels:
            meas.register_parameter(
                c_param,
                setpoints=[
                    slow_channel,
                    fast_channel,
                ],
            )
        try:
            trigger_reset()
        except TypeError:
            logger.info("No method to reset the trigger defined.")
        with meas.run() as datasaver:
            results = []
            slow_setpoints = slow_sweep.get_setpoints()
            for setpoint in slow_setpoints:
                slow_channel.set(setpoint)
                if reset_time > 0:
                    ramp_or_set_parameters(
                        [fast_channel], [fast_sweep.get_setpoints()[0]], ramp_rate=None, ramp_time=reset_time
                    )
                else:
                    fast_channel.set(fast_sweep.get_setpoints()[0])
                if reset_time < slow_sweep._delay:
                    sleep(slow_sweep._delay - reset_time)

                comping_results = []
                active_comping_sweeps = []
                for j in range(len(self.active_compensating_channels)):
                    index = self.compensating_parameters.index(self.active_compensating_parameters[j])
                    active_comping_setpoints = np.array(
                        [self.compensating_parameters_values[index] for _ in range(len(fast_sweep.get_setpoints()))],
                        dtype=float,
                    )
                    try:
                        slow_index = self.compensated_parameters[j].index(slow_param)
                        active_comping_setpoints -= float(self.compensating_leverarms[j][slow_index]) * (
                            float(setpoint) - float(slow_sweep.get_setpoints()[0])
                        )
                    except ValueError:
                        pass
                    try:
                        fast_index = self.compensated_parameters[j].index(fast_param)
                        active_comping_setpoints += self.compensating_sweeps[j][fast_index].get_setpoints()
                    except ValueError:
                        pass

                    if min(active_comping_setpoints) < min(self.compensating_limits[index]) or max(
                        active_comping_setpoints
                    ) > max(self.compensating_limits[index]):
                        raise Exception(f"Setpoints of {self.compensating_parameters[index]} exceed limits!")
                    sweep_delay = self.compensating_sweeps[j][-1]._delay
                    active_comping_sweeps.append(
                        CustomSweep(
                            param=self.active_compensating_channels[j],
                            setpoints=active_comping_setpoints,
                            delay=sweep_delay,
                        )
                    )
                    comping_results.append((self.active_compensating_channels[j], active_comping_setpoints))

                self.ready_buffers()
                try:
                    fast_channel.root_instrument._qumada_ramp(
                        [fast_channel, *self.active_compensating_channels],
                        start_values=[
                            fast_sweep.get_setpoints()[0],
                            *[sweep.get_setpoints()[0] for sweep in active_comping_sweeps],
                        ],
                        end_values=[
                            fast_sweep.get_setpoints()[-1],
                            *[sweep.get_setpoints()[-1] for sweep in active_comping_sweeps],
                        ],
                        ramp_time=self._burst_duration,
                        sync_trigger=sync_trigger,
                    )
                except AttributeError as ex:
                    logger.error(
                        "Exception: This instrument probably does not have a \
                          a qumada_ramp method. Buffered measurements without \
                          ramp method are no longer supported. \
                          Use the unbuffered script!"
                    )
                    raise ex

                if trigger_type == "manual":
                    pass

                if trigger_type == "hardware":
                    try:
                        trigger_start()
                    except NameError as ex:
                        print("Please set a trigger or define a trigger_start method")
                        raise ex

                elif trigger_type == "software":
                    for buffer in self.buffers:
                        buffer.force_trigger()
                    logger.warning(
                        "You are using software trigger, which \
                        can lead to significant delays between \
                        measurement instruments! Only recommended\
                        for debugging."
                    )
                timer = 0
                while not all(buffer.is_finished() for buffer in list(self.buffers)):
                    timer += 0.1
                    sleep(0.1)
                    if timer >= buffer_timeout_multiplier * self._burst_duration:
                        raise TimeoutError
                try:
                    trigger_reset()
                except TypeError:
                    logger.info(
                        "No method to reset the trigger defined. \
                        As you are doing a 2D Sweep, this can have undesired \
                        consequences!"
                    )

                results = self.readout_buffers()
                datasaver.add_result(
                    (slow_channel, setpoint),
                    (fast_channel, fast_sweep.get_setpoints()),
                    *comping_results,
                    *results,
                    *static_gettables,
                )
        datasets.append(datasaver.dataset)
        self.clean_up()
        return datasets


class Generic_Pulsed_Measurement(MeasurementScript):
    """
    Executes a buffered pulsed measurement with arbitrary setpoints.
    All setpoint arrays have to have the same length!

    Triggering methods:

    - "software": Sends a software command to each buffer and dynamic parameters
                   to start data acquisition and ramping. Timing might be slightly off.
    - "hardware": Runs trigger_start to start the measurement.. Can be preconfigured
                   or manually adjusted (requires `trigger_start` callable).
    - "manual": Trigger setup is user-defined, useful for synchronized trigger outputs.

    Parameters
    ----------
    trigger_start : str or callable, optional
        A callable to start the measurement or "manual" for user-triggered setup.
        Default is "manual".
    trigger_reset : callable, optional
        A callable to reset the trigger after measurement. Default is None.
    trigger_type : str, optional
        Type of trigger to use ("software", "hardware", "manual"). Default is "software".
    include_gate_name : bool, optional
        If True, appends the name of the ramped gates to the measurement name. Default is True.
    buffer_timeout_multiplier : int, optional
        Multiplier for buffer timeout duration relative to burst duration. Default is 20.
    sync_trigger : callable, optional
        Method for synchronized triggering. Default is None.

    Returns
    -------
    datasets : list of qcodes.dataset.data_set.DataSet
        A list of datasets containing the measurement results.

    Raises
    ------
    AttributeError
        If a required method (e.g., for pulsing) is missing.
    TimeoutError
        If buffers fail to finish within the timeout duration.
    Exception
        If static or dynamic parameters have invalid configurations.

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
        buffer_timeout_multiplier = self.settings.get("buffer_timeout_multiplier", 20)
        include_gate_name = self.settings.get("include_gate_name", True)
        sync_trigger = self.settings.get("sync_trigger", None)
        datasets = []
        timer = ElapsedTimeParameter("time")
        self.generate_lists()
        self.measurement_name = naming_helper(self, default_name="nD Sweep")
        if include_gate_name:
            gate_names = [gate["gate"] for gate in self.dynamic_parameters]
            self.measurement_name += f" {gate_names}"

        meas = self._new_measurement(name=self.measurement_name)
        meas.register_parameter(timer)
        for parameter in self.dynamic_parameters:
            self.properties[parameter["gate"]][parameter["parameter"]]["_is_triggered"] = True
        for dynamic_param in self.dynamic_channels:
            meas.register_parameter(
                dynamic_param,
                setpoints=[
                    timer,
                ],
            )

        # -------------------
        static_gettables = []
        del_channels = []
        del_params = []
        for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
            if is_bufferable(channel):
                meas.register_parameter(
                    channel,
                    setpoints=[
                        timer,
                    ],
                )
            elif channel in self.static_channels:
                del_channels.append(channel)
                del_params.append(parameter)
                meas.register_parameter(
                    channel,
                    setpoints=[
                        timer,
                    ],
                )
                parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                static_gettables.append((channel, [parameter_value for _ in range(self.buffered_num_points)]))
        for channel in del_channels:
            self.gettable_channels.remove(channel)
        for param in del_params:
            self.gettable_parameters.remove(param)
        # --------------------------

        self.initialize()
        for c_param in self.active_compensating_channels:
            meas.register_parameter(
                c_param,
                setpoints=[
                    timer,
                ],
            )

        instruments = {param.root_instrument for param in self.dynamic_channels}
        time_setpoints = np.linspace(0, self._burst_duration, int(self.buffered_num_points))
        setpoints = [sweep.get_setpoints() for sweep in self.dynamic_sweeps]
        compensating_setpoints = []
        for i in range(len(self.active_compensating_channels)):
            index = self.compensating_channels.index(self.active_compensating_channels[i])
            active_setpoints = sum([sweep.get_setpoints() for sweep in self.compensating_sweeps[i]])
            active_setpoints += float(self.compensating_parameters_values[index])
            compensating_setpoints.append(active_setpoints)
            if min(active_setpoints) < min(self.compensating_limits[index]) or max(active_setpoints) > max(
                self.compensating_limits[index]
            ):
                raise Exception(f"Setpoints of compensating gate {self.compensating_parameters[index]} exceed limits!")
        try:
            trigger_reset()
        except TypeError:
            logger.info("No method to reset the trigger defined.")
        with meas.run() as datasaver:
            results = []
            self.ready_buffers()
            for instr in instruments:
                try:
                    instr._qumada_pulse(
                        parameters=[*self.dynamic_channels, *self.active_compensating_channels],
                        setpoints=[*setpoints, *compensating_setpoints],
                        delay=self._burst_duration / self.buffered_num_points,
                        sync_trigger=sync_trigger,
                    )
                except AttributeError as ex:
                    logger.error(
                        f"Exception: {instr} probably does not have a \
                            a qumada_pulse method. Buffered measurements without \
                            ramp method are no longer supported. \
                            Use the unbuffered script!"
                    )
                    raise ex

            if trigger_type == "manual":
                logger.warning(
                    "You are using manual triggering. If you want to pulse parameters on multiple"
                    "instruments this can lead to delays and bad timing!"
                )

            if trigger_type == "hardware":
                try:
                    trigger_start()
                except NameError as ex:
                    print("Please set a trigger or define a trigger_start method")
                    raise ex

            elif trigger_type == "software":
                for buffer in self.buffers:
                    buffer.force_trigger()
                logger.warning(
                    "You are using software trigger, which \
                    can lead to significant delays between \
                    measurement instruments! Only recommended\
                    for debugging."
                )
            timeout_timer = 0
            while not all(buffer.is_finished() for buffer in list(self.buffers)):
                timeout_timer += 0.1
                sleep(0.1)
                if timeout_timer >= buffer_timeout_multiplier * self._burst_duration:
                    raise TimeoutError
            try:
                trigger_reset()
            except TypeError:
                logger.info("No method to reset the trigger defined.")

            results = self.readout_buffers()

            datasaver.add_result(
                (timer, time_setpoints),
                *(zip(self.dynamic_channels, setpoints)),
                *(zip(self.active_compensating_channels, compensating_setpoints)),
                *results,
                *static_gettables,
            )
        datasets.append(datasaver.dataset)
        self.clean_up()
        return datasets


class Generic_Pulsed_Repeated_Measurement(MeasurementScript):
    """
    Executes a buffered pulsed measurement with repeated acquisitions.
    Results of the acquisitions are averaged. All setpoint arrays need to have
    the same length.

    Triggering methods:

    - "software": Sends a software command to each buffer and dynamic parameters
                   to start data acquisition and ramping. Timing might be slightly off.
    - "hardware": Runs trigger_start to start the measurement. Can be preconfigured
                   or manually adjusted (requires `trigger_start` callable).
    - "manual": Trigger setup is user-defined, useful for synchronized trigger outputs.

    Parameters
    ----------
    trigger_start : str or callable, optional
        A callable to start the measurement or "manual" for user-triggered setup.
        Default is "manual".
    trigger_reset : callable, optional
        A callable to reset the trigger after measurement. Default is None.
    trigger_type : str, optional
        Type of trigger to use ("software", "hardware", "manual"). Default is "software".
    include_gate_name : bool, optional
        If True, appends the name of the ramped gates to the measurement name. Default is True.
    repetitions : int, optional
        Number of repeated measurements to perform. Default is 1.
    sync_trigger : callable, optional
        Method for synchronized triggering. Default is None.

    Returns
    -------
    datasets : list of qcodes.dataset.data_set.DataSet
        A list of datasets containing the measurement results.

    Raises
    ------
    AttributeError
        If a required method (e.g., for pulsing) is missing.
    Exception
        If static or dynamic parameters have invalid configurations.

    Notes
    -----
    - Results are averaged across repetitions.s<
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
        self.repetitions = self.settings.get("repetitions", 1)
        include_gate_name = self.settings.get("include_gate_name", True)
        sync_trigger = self.settings.get("sync_trigger", None)
        datasets = []
        timer = ElapsedTimeParameter("time")
        self.generate_lists()
        self.measurement_name = naming_helper(self, default_name="nD Sweep")
        if include_gate_name:
            gate_names = [gate["gate"] for gate in self.dynamic_parameters]
            self.measurement_name += f" {gate_names}"

        meas = self._new_measurement(name=self.measurement_name)
        meas.register_parameter(timer)
        for parameter in self.dynamic_parameters:
            self.properties[parameter["gate"]][parameter["parameter"]]["_is_triggered"] = True
        for dynamic_param in self.dynamic_channels:
            meas.register_parameter(
                dynamic_param,
                setpoints=[
                    timer,
                ],
            )

        # -------------------
        static_gettables = []
        del_channels = []
        del_params = []
        for parameter, channel in zip(self.gettable_parameters, self.gettable_channels):
            if is_bufferable(channel):
                meas.register_parameter(
                    channel,
                    setpoints=[
                        timer,
                    ],
                )
            elif channel in self.static_channels:
                del_channels.append(channel)
                del_params.append(parameter)
                meas.register_parameter(
                    channel,
                    setpoints=[
                        timer,
                    ],
                )
                parameter_value = self.properties[parameter["gate"]][parameter["parameter"]]["value"]
                static_gettables.append((channel, [parameter_value for _ in range(self.buffered_num_points)]))
        for channel in del_channels:
            self.gettable_channels.remove(channel)
        for param in del_params:
            self.gettable_parameters.remove(param)
        # --------------------------

        self.initialize()
        for c_param in self.active_compensating_channels:
            meas.register_parameter(
                c_param,
                setpoints=[
                    timer,
                ],
            )

        instruments = {param.root_instrument for param in self.dynamic_channels}
        time_setpoints = np.linspace(0, self._burst_duration, int(self.buffered_num_points))
        setpoints = [sweep.get_setpoints() for sweep in self.dynamic_sweeps]
        compensating_setpoints = []
        for i in range(len(self.active_compensating_channels)):
            index = self.compensating_channels.index(self.active_compensating_channels[i])
            active_setpoints = sum([sweep.get_setpoints() for sweep in self.compensating_sweeps[i]])
            active_setpoints += float(self.compensating_parameters_values[index])
            compensating_setpoints.append(active_setpoints)
            if min(active_setpoints) < min(self.compensating_limits[index]) or max(active_setpoints) > max(
                self.compensating_limits[index]
            ):
                raise Exception(f"Setpoints of compensating gate {self.compensating_parameters[index]} exceed limits!")
        results = []
        with meas.run() as datasaver:
            for k in range(self.repetitions):
                self.initialize()
                try:
                    trigger_reset()
                except TypeError:
                    logger.info("No method to reset the trigger defined.")
                self.ready_buffers()
                for instr in instruments:
                    try:
                        instr._qumada_pulse(
                            parameters=[*self.dynamic_channels, *self.active_compensating_channels],
                            setpoints=[*setpoints, *compensating_setpoints],
                            delay=self._burst_duration / self.buffered_num_points,
                            sync_trigger=sync_trigger,
                        )
                    except AttributeError as ex:
                        logger.error(
                            f"Exception: {instr} probably does not have a \
                                a qumada_pulse method. Buffered measurements without \
                                ramp method are no longer supported. \
                                Use the unbuffered script!"
                        )
                        raise ex

                if trigger_type == "manual":
                    logger.warning(
                        "You are using manual triggering. If you want to pulse parameters on multiple"
                        "instruments this can lead to delays and bad timing!"
                    )

                if trigger_type == "hardware":
                    try:
                        trigger_start()
                    except NameError as ex:
                        print("Please set a trigger or define a trigger_start method")
                        raise ex

                elif trigger_type == "software":
                    for buffer in self.buffers:
                        buffer.force_trigger()
                    logger.warning(
                        "You are using software trigger, which \
                        can lead to significant delays between \
                        measurement instruments! Only recommended\
                        for debugging."
                    )

                while not all(buffer.is_finished() for buffer in list(self.buffers)):
                    sleep(0.1)
                try:
                    trigger_reset()
                except TypeError:
                    logger.info("No method to reset the trigger defined.")

                results.append(self.readout_buffers())
            average_results = []
            for i in range(len(results[0])):
                helper_array = np.zeros(len(results[0][0][1]))
                for meas_results in results:
                    helper_array += meas_results[i][1]
                helper_array /= self.repetitions
                average_results.append((meas_results[i][0], helper_array))

            datasaver.add_result(
                (timer, time_setpoints),
                *(zip(self.dynamic_channels, setpoints)),
                *(zip(self.active_compensating_channels, compensating_setpoints)),
                *average_results,
                *static_gettables,
            )
        datasets.append(datasaver.dataset)
        self.clean_up()
        return datasets
