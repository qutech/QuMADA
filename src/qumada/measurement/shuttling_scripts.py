import numpy as np


def shuttle_setpoints(offsets, amplitudes, num_periods, phases, sampling_rate, barrier_voltages, duration, reverse = False):
  pulses=[]
  def shuttling_sin(x, offset, amplitude, phase, reverse = False):
      if reverse:
          sign = -1
      else:
          sign = 1
      return amplitude*np.sin(sign*x+phase)+offset
  for i in range(0, 4):
      x_datapoints = np.linspace(0, 2*np.pi*num_periods, int(sampling_rate*duration))
      pulses.append(
          shuttling_sin(x_datapoints, offsets[i], amplitudes[i], phases[i], reverse = reverse)
      )
  for i in range(5, 7):
      pulses.append([barrier_voltages[i-5] for _ in range(int(sampling_rate*duration))])
  return pulses

def ramping_setpoints(starts, stops, duration, sampling_rate):
  setpoints = []
  for start, stop in zip(starts, stops):
    setpoints.append(np.linspace(start, stop, int(duration*sampling_rate)))
  return setpoints

def concatenate_setpoints(setpoint_arrays):

    num_gates = len(setpoint_arrays[0])
    conc_array = [[] for _ in range(num_gates)]
    for i in range(len(setpoint_arrays)):
      for j in range(len(setpoint_arrays[0])):
        for val in setpoint_arrays[i][j]:
          conc_array[j].append(val)

    return conc_array


def Generic_Pulsed_Measurement_w_parameter(device, add_parameter, add_parameter_setpoints, settings):
    """
    Measurement script for buffered measurements with abritary setpoints.
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
    TODO: Add Time!
    """
    meas
    with meas.run() as datasaver:
    for setpoint in add_parameter_setpoints:

        script = Generic_Pulsed_Measurement()
        script.setup()


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
        self.add_parameter  = self.settings.get("add_parameter")
        self.add_parameter_setpoints = self.settings.get("add_parameter_setpoints")
        include_gate_name = self.settings.get("include_gate_name", True)
        sync_trigger = self.settings.get("sync_trigger", None)
        datasets = []
        timer = ElapsedTimeParameter("time")
        self.generate_lists()
        self.measurement_name = naming_helper(self, default_name="nD Sweep")
        if include_gate_name:
            gate_names = [gate["gate"] for gate in self.dynamic_parameters]
            self.measurement_name += f" {gate_names}"

        meas = Measurement(name=self.measurement_name)
        meas.register_parameter(self.add_parameter)
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
