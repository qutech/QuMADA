Examples
==============

Measurement Scripts
--------------------

Qtools comes with a couple of "generic" measurement scripts suitable for most basic applications. 

#####################
Generic_1D_Sweep()
#####################

.. py:class:: Generic_1D_Sweep(MeasurementScript)

This measurement script is used for performing sweeps of individual parameters (e.g. gate voltages) while all other parameters
are kept constant. The script requires one or more dynamic parameters, one or more gettable parameters and an arbitrary amount of static
parameters.
If only one dynamic parameter is provided, this parameter is ramped according to its settings and all gettable parameters will be recorded
at each setpoint. The parameter is ramped to the first setpoint of its sweep prior to starting the measurement, all static parameters are ramped to their
corresponding "value" values in the gate parameters. The Generic_1D_Sweep has an optional "wait_time: float [optional]" argument (passed when calling the setup() method) that defines
the wait time between finishing the initialization and ramping of the parameters and the actual start of the measurement in seconds (default value: 5s).

In case more than one dynamic parameter is provided, one dimensional sweeps are performed for all those parameters, one after another. For each parameter
a new qcodes measurement is created. After each measurement the reset() method is called, which ramps all parameters back to their starting values before the
next measurement is started. Dynamic parameters that are currently not ramped are treated as static parameter and kept at their "value" value. If no "value" 
is provided, the parameters will kept at the starting point of their sweep.

Example:

.. code-block:: yaml

	source drain:
	  amplitude:
		type: static
		value: 0.0001
	  frequency:
		type: static
		value: 173
	  output_enabled:
		type: static
		value: 1
	  current:
		type: gettable
		break_conditions:
		- val > 1e-9
	  phase:
		type: gettable
	Accumulation Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 250
		delay: 0.025
		value: 1.5
	Left Barrier Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 200
		delay: 0.025
	Right Barrier Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 200
		delay: 0.025
	Plunger Gate:
	  voltage:
		type: static
		value: 1.3
		
Those example gate parameters in combination with the Generic_1D_Sweep will perform three 1D sweeps for the Accumulation Gate voltage,
the Left Barrier Gate voltage and the Right Barrier Gate voltage. The Accumulation Gate voltage will be kept at 1.5 V during the 
measurements of the barrier gates whereas the Barrier gates will be set to 0 V during the Accumulation Gate sweep.

The 1D_Generic sweep is very useful for performing pinchoff measurements of many gates.

#########################
Generic_1D_parallel_Sweep()
#########################

.. py:class:: Generic_1D_parallel_Sweep(MeasurementScript)

The Generic_1D_parallel_Sweep is very similar to the "normal" Generic_1D_Sweep and behaves in the same way when only one dynamic
parameter is provided. If more than one dynamic parameter is passed, however, it will not perform multiple sweeps but only one ramping
all dynamic parameters in parallel. In the current version it will use the setpoints of the first dynamic parameter for all dynamic parameters.

.. note::

	We plan to add the possibility to specify factors for all parameters in order to make this measurement script more flexible
	
As the Generic_1D_Sweep is has a wait_time argument to set the wait time between the initialization and the start of the measurement
and additionally the backsweep_after_break: bool [optional][False] parameter. When set to True triggering a break condition will
not abort the measurement but instead start a backsweep to the starting point of the measurement. 

.. note::

	More precise: It will delete all upcoming setpoints from the sweep add all setpoints reached before the break condition 
	was triggered in reverse order. Thus we recommend to use it only for measurements where monotonic behaviour is expected.
	
This feature was implemented to allow for easy accumulation measurements in Si/SiGe samples.

Example:

.. code-block:: yaml

	source drain:
	  amplitude:
		type: static
		value: 0.0001
	  frequency:
		type: static
		value: 173
	  output_enabled:
		type: static
		value: 1
	  current:
		type: gettable
		break_conditions:
		- val > 1e-9
	  phase:
		type: gettable
	Accumulation Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 250
		delay: 0.025
		value: 1.5
	Left Barrier Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 200
		delay: 0.025
	Right Barrier Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 200
		delay: 0.025
	Plunger Gate:
	  voltage:
		type: static
		value: 1.3

Consequently, the same example gate parameters will start a measurement where the Accumulation Gate and the Barrier Gates are swept at the same time from 0 to 2 V (in 250 steps). 
Unused parameters such as "value" for the Accumulation Gate are simply ignored.


################
Generic_nD_Sweep
################

.. py:class:: Generic_nD_Sweep(MeasurementScript)

This measurement script can be used for arbitrary n-dimensional sweeps. For n dynamic parameters an n-dimensional array of setpoints is created containing all combinations of parameter values.
The setpoint arrays, delays etc. can be chosen individually for each parameter. Our example gate parameters

.. code-block:: yaml

	source drain:
	  amplitude:
		type: static
		value: 0.0001
	  frequency:
		type: static
		value: 173
	  output_enabled:
		type: static
		value: 1
	  current:
		type: gettable
		break_conditions:
		- val > 1e-9
	  phase:
		type: gettable
	Accumulation Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 250
		delay: 0.025
		value: 1.5
	Left Barrier Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 200
		delay: 0.025
	Right Barrier Gate:
	  voltage:
		type: dynamic
		start: 0
		stop: 2
		num_points: 200
		delay: 0.025
	Plunger Gate:
	  voltage:
		type: static
		value: 1.3

will create a 3-dimensional sweep ramping the Accumulation gate from 0 to 2 V and then creating a 2D sweep of the Barrier Gates at each setpoint.
Keep in mind that sweeps with more than two dynamic parameters can take a lot of time. Furthermore, the built-in QCoDeS plotting script (plot_dataset from qcodes.dataset.plotting) cannot handle
more than two independent parameters. You can still use the plottr-inspectr or the QTools plot functions to plot the data.

##################
Timetrace
##################

.. py:class:: Timetrace(MeasurementScript)

The Timetrace measurement script can be used to monitor multiple parameters over a specified amount of time.
You can use the "duration" and "timestep" arguments when calling the setup method to specify duration of the measurement and the time between to setpoints.
All gettable (and static gettable) parameters will be recorded, static and dynamic parameters will be ramped to their "value" value and the kept constant.

.. note::

	The minimum timestep is limited by time it takes to record the measurement values. If you choose small timesteps compared to the measurement speed and communication time it might affect
	the stepsize and duration of the complete measurement. Use custom measurement scripts to perform very fast or high-precision measurements.


#####################################
Writing your own measurement scripts (WIP)
#####################################

Although the generic measurement scripts coming with QTools can handle a lot of different measurements there are certainly cases where you want to define your own measurements.
In general Qtools supports all the freedom the QCoDeS Measurement Context Manager provides. However, in order to make it work with QTools features like the gate mapping you have 
to pay attention to a few things.

All Qtools measurement scripts should be a child class of the Qtools MeasurementScript class. Thus, the script inherits helpful or required methods like initialization() (not to be confused with the __init__) and setup().
Arguments are passed when calling the setup() method of the measurement script.

.. code-block:: python

	setup(parameters: dict, 
		metadata: Metadata, 
		*, 
		add_script_to_metadata: bool = True,
		add_parameters_to_metadata: bool = True,
		**settings: dict,
		)

You can use pass keyword arguments or a settings dictionary for usage in the run() method.
The measurement workflow itself is defined in the run() method.
Here you can define how the measurement is performed in the same way you would do it in QCoDeS.
It is recommended to initially call the initialize() method, which ramps all parameters to their starting points and creates lists of all
dynamic, static and gettable parameters, break conditions and sweeps and relabels all QCoDeS parameters according to their name in the gate parameters, once the run() method is executed. 
You can access these lists as attributes of the measurement script. Furthermore all terminal/gates, their parameters and the corresponding instruments channels are
available in the gate_parameters attribute of the script. You can access them using their name as defined in the gate parameters.

.. note::
	A more precise documentation of the initialize method all inherent attributes is yet to be done. For details we recommend to use the generic measurements script as examples

Another helpful method is the reset() method which works similar to the initialization() method but does no create lists of different parameters types. It just ramps all parameters to their starting values.	
Everything that works with QCoDes will work with Qtools as long as you provide the parameters and the metadata object.

Let us create a custom script that repeatedly sweeps a couple of parameters for a specified amount of time as an example.
If you know all parameters and what to with them in advance you can simply hardcode all the parameters in your measurement script and maybe add a few arguments to adjust the duration of the measurement and the sweeps of the parameters, 
as you would do it when using QCoDeS. However, this is not the QTools way. Using Qtools, you can create a flexible and reusable measurement script in the same amount of time.

.. code-block:: python
	
	from qcodes.instrument.specialized_parameters import ElapsedTimeParameter
	
	class Timetrace_with_sweeps(MeasurementScript):
	
		def run(self):
			self.initialize()
			duration = self.settings.get("duration", 300)
			timestep = self.settings.get("timestep", 1)
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
						datasaver.add_result(
							(timer, now),
							*set_values,
							*results
							)

			dataset = datasaver.dataset
			return dataset

We only have to define the run() method, all other methods are part of the MeasurementScript parent class. Let's start by calling the self.initialize() method to automatically create a couple of handy lists containing all required parameters and settings
and to make sure everything is ramped to the starting values.

We then define all settings we want to be able to change later on when calling the setup() method. The settings contain all settings regarding the measurement script except for those 
directly linked to the gates/terminals and their parameters (e.g. the voltage applied etc.) In order to record the time we use the predefined specialized_parameter "ElapsedTimeParameter" and create 
an additional parameter called "timer".
The next few lines are for setting up the QCoDeS measurement context manager. We can simply get the measurement name from our metadata object and then register independent parameters - the timer and all
dynamic parameters - to the measurement. Note that we can simply access the latter from the dynamic_channels list automatically created when the initialize() method is called. We add all of them to a setpoints list
that we can use to specify the dependencies when registering the dependent parameters in the next step. Again, we can simply use the gettable_channels list as the gettable parameters are the ones we want to measure.
The "_channels" refer to the actual QCoDeS parameters whereas the "dynamic_parameters"/"gettable_parameters"/"static_parameters" lists contain dictionaries with the gate/terminal names and the parameter names.
The following "with" block contains the measurement procedure. Initially, we want to reset the clock and then run our sweeps until the elapsed time is longer than the duration we specified.
For each step we first want to quickly ramp all parameters back to the starting point of the corresponding sweeps, then measure the current time and start the sweeps.

.. note::
	
	This is of course not perfectly accurate, as the sweeps will take some time. However, this is just an example and having one timestamp for each sweep makes plotting the data a lot easier.
	
Again we can use an automatically generated list to set all the dynamic parameters, the dynamic_sweeps list. The contained sweep-objects are QCoDeS objects containing all relevant data of a sweep and were
originally used in QCoDeS donD-methods. Alternatively, we could use self.dynamic_parameters to get the channels from the gate_parameters attribute.
Finally, we can add all the parameters and their values to the datasaver and are done.
Note that this code can be used with an arbitrary set of dynamic, static and gettable parameters.


#############################
Working with gate_parameters
#############################

In many cases changing a lot of entries in the gate_parameters.yaml file is tideous. However, as you the gate_parameters are basically
a dictionary once loaded into python, you can use keywords to modify the parameters easily.
Therefore, we included some useful method in the "utils" section of QTools.



Buffered Measurements
----------------------

Currently, QTools supports only basic buffered measurements with simple 1D Sweeps and data acquisition with either the SR 830 or the Zurich Instruments MFLI lockins.

#############################
Buffered 1D Measurements
#############################

Buffered measurements are required, as the communication between the measurement PC and the measurement hardware can slow down measurement significantly. For unbuffered measurements, QTools has to send get and set commands to the measurement hardware for every datapoints,
whereas buffered measurements just require communication for starting the measurement and for reading the data after it finished.
In Qtools buffered measurements are setup similarily to unbuffered ones. As for the gate mapping to get rid of driver specific commands for normal measurements, Qtools comes with a generic buffer class that maps the buffer and trigger settings
to the used instruments. This requires a few changes to the way the measurement station is setup:

.. code-block:: python
	from qtools.instrument.buffered_instruments import BufferedMFLI as MFLI
	from qcodes.instrument_drivers.Harvard.Decadac import Decadac
	from qtools.instrument.mapping import (
    add_mapping_to_instrument,
    MFLI_MAPPING
    )
	from qtools.instrument.mapping.Harvard.Decadac import DecadacMapping
	from qtools.instrument.mapping.base import map_gates_to_instruments
	
	station = qc.Station
	
	dac = Decadac(
    "dac",
    "ASRL6::INSTR",
    min_val=-10,
    max_val=10,
    terminator="\n")
	add_mapping_to_instrument(dac, mapping = DecadacMapping())
	station.add_component(dac)
	
	mfli = MFLI("mfli", "DEV4121", "169.254.40.160")
	add_mapping_to_instrument(mfli, path = MFLI_MAPPING)
	station.add_component(mfli)

(This code block expects you to do the basci qcodes and qtools imports on your own)

For the MFLI the BufferedMFLI class is used instead of the normal driver. It inherits from the normal MFLI class but adds the _qtools_buffer property, which incorporates the Qtools buffer, to the MFLI.
The Qtools buffer has methods to setup the buffer and triggers as well as to start, stop and readout measurements. Using a instrument for buffered measurements requires a wrapper mapping the instruments driver specific commands
to the Qtools ones. Currently, QTools supports the MFLI and the SR830 (more to come), how to add additional instruments by yourself will be covered in a different section.

The DecaDac's is required to do a smooth ramp, which requires usage of the built in ramp method. As this cannot be mapped by using the normal Qtools mapping.json file, we use the DecadacMapping class and pass it as the mapping-kwarg 
(instead of "path") to "add_mapping_to_instrument". This does not only add the normal mapping but includes the _qtools_ramp() method which is used in Qtools' buffered measurement scripts for ramping channels. This method makes use of the
built-in ramp method, but standardizes the input parameters so that different instruments can be used with the same measurement script. Note that instruments without built-in ramps can be used for the buffered measurements as well, but then require communication at 
each setpoint, which slows down the measurement and can lead to asynchronicity.

..Note
	In some cases it is possible to add trigger channels to the _qtools_ramp method. Those are triggered, as soon as the ramp starts. However, this feature is still WIP and can lead to significat offsets due to time delays.
	
Setting up the buffer in Qtools is done via a settings dict (which can also be serialized into a yaml or json file). The parameters are:

trigger_mode [str]:      
		continuous,
        edge,
        tracking_edge,
        pulse,
        tracking_pulse,
        digital.
		
		Note that some of those modes may not be available by some instruments. Furthermore, the trigger mode is changed automatically by the buffer class in some cases after the trigger input is assigned. For example using the trigger inputs of the MFLI
		requires the digital trigger mode. 
trigger_mode_polarity [str]: 
		positive,
		negative,
		both
		
		Defines for edge triggers if rising or falling flanks trigger and for pulse triggers if negative or positive pulses.

trigger_threshold [float]: 
		Defines the voltage level required to start trigger event. Any number, range is limited by instrument specifications.
		
grid_interpolation [str]:
		linear
		nearest
		exact
		
		Defines the interpolation between setpoints for 2D sweeps (Details in MFLI Documentation, TODO)	
		
delay [float]:  
		Defines the time delay between the trigger signal and the start of the measurement. Some instruments (e.g. the MFLI) support negative delays, others don't support delays at all.
		
num_points [int]: 
		Specify the number of points for the measurement. You can only define two of num_points, burst_duration and sampling_rate, the third one is calculated from the other two. Limited by buffer size.

sampling_rate [float]:
		The rate at which data is recorded. You can only define two of num_points, burst_duration and sampling_rate, the third one is calculated from the other two. Limited by instrument specifications.
		
duration [float]:
		Overall duration of the measurement. In the future multiple burst are possible, right now duration shoult be the same as burst_duration. Limited by buffer size and sampling_rate.

burst_duration [float]:
		Duration of each measurement bursts. Right now, only one burst per measurement is possible, shoult be the same as duration. You can only define two of num_points, burst_duration and sampling_rate, the third one is calculated from the other two.


	

	







 










