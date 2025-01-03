Tutorials
=========

First steps: Example Measurements
---------------------------------

QuMada is a QCoDeS based measurement framework that helps you to perform measurements easily and furthermore supports the QTools metadata-database (not public) for easy metadata storage.
Note that it is not required to use the metadata-db at all to use most of the QuMada features.
Before you start with this basic tutorial make sure to get familiar with QCoDeS, we recommend to work through the 15-Minute-To-QCoDeS tutorial to learn about setting up
a database for the measurement data, Experiment containers, the measurement context manager and the station object.
In this tutorial we assume that you already set up a QCoDeS database and created an experiment.

This tutorial will show you how to setup basic measurements in QuMada. It roughly follows the example_main_1.py in src/examples.
It contains a couple of blocks for the steps you have to do in order to set up the measurement and run it. This tutorial focuses on running measurements based on measurement scripts and
a parameter dictionary. Whereas this is not the most comfortable way to use QuMada it helps to understand the underlying mechanics. Make sure to go through the :ref:`DeviceObject` documentation
to make the best use of QuMada.

We start by setting up the usual imports (including some QCoDeS imports for handling the measurement data and the instruments.
This example runs with Dummy Instruments.

.. code-block:: python

	# %% Experiment Setup

	import threading #Only needed for the dummy instruments

	import numpy as np
	from qcodes.dataset import (
		Measurement,
		experiments,
		initialise_or_create_database_at,
		load_by_run_spec,
		load_or_create_experiment,
	)
	from qcodes.station import Station

	from qumada.instrument.buffered_instruments import BufferedDummyDMM as DummyDmm
	from qumada.instrument.custom_drivers.Dummies.dummy_dac import DummyDac
	from qumada.instrument.mapping import (
		DUMMY_DMM_MAPPING,
		add_mapping_to_instrument,
		map_terminals_gui,
	)
	from qumada.instrument.mapping.Dummies.DummyDac import DummyDacMapping
	from qumada.measurement.scripts import (
		Generic_1D_parallel_asymm_Sweep,
		Generic_1D_Sweep,
		Generic_nD_Sweep,
		Timetrace,
	)
	from qumada.utils.generate_sweeps import generate_sweep
	from qumada.utils.load_from_sqlite_db import load_db

#################
Station and Instruments
#################


Now we can start with setting up the QCoDeS station object and the measurement instruments.
In difference to QCoDeS measurements, QuMADA measurements scripts are largely independent of the instruments used. Nonetheless, it is still required to create a QCoDeS station
object and specify the instruments used, which is done by providing name and the address of the instrument using the corresponding QCoDeS methods. One can use custom instrument drivers (such as our Dummy Instruments)
as long as they follow the QCoDeS standards.
In addition to this, we want to add an instrument mapping to each instrument. As QCoDeS drivers are supplied by many different people, the parameters of instruments are named
inconsistently. The voltage parameter of a Keithley 2400 DMM is addressed via Keithley.volt, the parameter of a Keithley 2450 via Keithley.source.voltage and the
voltage of a QDevil QDac channel via QDac.Ch01.v. When using QCoDeS, it is necessary to alter the measurement script accordingly whenever a different instrument is used. QuMADA deals with this issue
by introducing an additional abstraction layer, the gate_mapping. QuMADA uses predefined names for similar parameters making sure you can reuse your measurement scripts and do not have to browse through instrument
drivers in order to look up the right command.

.. note::

	The names are specified in a json-file in src/qumada/instrument/instrument_whitelists. In case you need to add parameter names you can add your own json-file.

Adding the mapping is easily done by using the "add_mapping_to_instrument" command:

.. py:function:: add_mapping_to_instrument(instrument, mapping)

	Applies the mapping specified to the instrument

   :instrument: Instrument

   :mapping: Mapping, has to be imported from qumada.instrument.mapping and be listed in the corresponding __init__ file.
	Can be either an instance of the InstrumentMapping class or a string pointing to a mapping json-file.

   :return: None

.. code-block:: python

	# Setup qcodes station and load instruments
	station = Station()

	# Creating QCoDeS Instrument. For buffered instruments we have to use the QuMada buffered version.
	dmm = DummyDmm("dmm")
	# Adding the QuMada mapping
	add_mapping_to_instrument(dmm, mapping=DUMMY_DMM_MAPPING)
	# Add QCoDes Instrument to station
	station.add_component(dmm)

	dac1 = DummyDac("dac1")
	add_mapping_to_instrument(dac1, mapping=DummyDacMapping())
	station.add_component(dac1)

	dac2 = DummyDac("dac2")
	add_mapping_to_instrument(dac2, mapping=DummyDacMapping())
	station.add_component(dac2)

In this sample we just add a couple of dummy instrument that come with QuMada. Be aware, that the Dummy Dmm only returns random values between
0 and 1.

#############
Metadata (Optional, WIP)
#############


In the next step, we want to create a metadata object. The object contains all the metadata to store in the metadatabase and is furthermore used to supply
the metadata for the measurement script and the QCoDeS-database. Thus, you have to provide sample name and measurement name even if you do not intend to use
the metadatabase.

The easiest way to create the metadata-object is by entering the data into the metadata web-ui.

.. code-block:: python

	#%% Metadata Setup
	from qtools_metadata.metadata import create_metadata, save_metadata_object_to_db

	db.api_url = "http://134.61.7.48:9124"
	metadata = create_metadata()


.. note::

	There are currently some issues with the metadata-database and it is not available for public use. You can pass "insert_metadata_into_db=False" into the run-method of the script
	when you do not want to save the measurement into the metadatabase and otherwise ignore the metadata-db related parts of this tutorial. There might be some warnings popping up when you run the measurement,
	feel free to ignore them.

The connection to the metadabase is required for loading information of already existing samples and measurements (so you do not have to enter them again) and
- of course - for storing the data. Right now, we are only interested in creating the metadata object for usage in our measurements.


###########################################
Specifying the database for storing the data
###########################################

In case you have not already initialized a QCoDeS database you can easily do so by using the load_db(path_to_db [optional) method, which either takes the path to the database you want to use or, when no argument is supplied,
opens an open-file prompt allowing you to simply pick the database you want to use (be aware that the prompt might pop up behind other windows). Alternatively, you can provide a valid path and a filename as input argument
to create a new database. Feel free to use the initialise_or_create_database_at method from QCoDeS and do not forget to setup an experiment
container in case you created a new database (more details in the QCoDeS documentation).

At this point we have taken care of all preliminary steps required before defining the measurement.
Except for changing the measurement name in the metadata object, you will have to do those steps only when exchanging the sample or altering the setup.

From now on, we will go through a typical workflow for characterizing a gate-defined Single Electron Transistor (SET) in a semiconductor heterostructure such as Si/SiGe or Si MOS.
Measurements in QuMADA are mainly defined by two things: The terminal_parameters and the measurement script used.


###############################
Terminal parameters
###############################

The Terminal_parameters are part of each measurement script and contain a list of all physical terminals of the device under test (DUT) such as gates or ohmic contacts and information about what to do with them during the measurement.
The Terminal_parameters can also be loaded from a yaml-file (or json-file if you prefer to double-check brackets all the time...). Here, we simply define a dictionary.:

.. code-block:: python

	# This dictionary defines your device. "ohmic", "gate1" and "gate2" are terminals, representing parts of your
	# device.
	# Each terminal can have multiple parameters that represent values of the terminals
	# (here "current" and "voltage"). A real Ohmic connected to a lockin-amplifier could for example have
	# additional parameters such as "amplitude" or "frequency". As our dummy_dmm doesn't have those parameters,
	# we cannot use them here. Each parameter has to be mapped to a parameter of a QCoDeS instrument later.

	parameters = {
		"ohmic": {
			"current": {
				"type": "gettable",
				"break_conditions": ["val > 0.95"],
			},
		},
		"topgate": {
			"voltage": {
				"type": "dynamic",
				"setpoints": np.linspace(0, 0.5, 100),
				"delay": 0.01,
			}
		},
		"barriers": {
			"voltage": {
				"type": "dynamic",
				"setpoints": np.linspace(0, 0.4, 100),
				"delay": 0.01,
			},
		},
	}

In our example the SET consists source and drain contact, a global topgate and interconnected barriers controlled by only one voltage.
In a first step, we want to ramp all the gates in parallel to check whether we can accumulate charges and open a current path through the quantum well by
measuring the current flowing through the ohmics using our Dummy Dmm.
(in a reality you would probably apply a bias voltage. You can do that by simply adding a "voltage" parameter to the ohmic and set it to "static". Our simple Dummy Dmm does not have a voltage output).

Each terminal or gate in QuMADA can have one or more parameters corresponding to physical properties such as a voltage or current.


.. note::
	It is still necessary to think about the capabilities and parameters of you instrument. Many instruments are have specific settings that are not properly mapped and not in the list of allowed parameters as they
	are not frequently used. You can either change them manually using the QCoDeS parameter or add them to the list of allowed parameters. Keep in mind that adding parameters like "output_enabled" to all terminals might
	make the dictionary much harder to read and it might be advisable to have separate functions to setup all instruments properly.

All parameters defined as "static" or "dynamic" will be ramped to their value or the first setpoint, respectively, before a measurement starts by QuMada!
Parameters that cannot be ramped (e.g. because they have booleans as values) are set.


Each parameter has a specific type: "dynamic", "static" and/or "gettable".

Dynamic parameters are ramped during the measurement, they require either an array of (arbitrary) setpoints or "start", "stop" and "num_points" values specifying a linear sweep.
Here we also provide a delay representing a wait time between setpoints (in sec, 0 by default).
Dynamic parameters are automatically recorded during the measurement.

Static parametes are kept constant during the measurement, they only require a "value" to be set to. Float-valued parameters are ramped to their corresponding starting point at the beginning of a measurement, other parameters are simple set.
Static parameters usually correspond to settings or static gates.

Gettable parameters do not require any additional settings, their value is recorded at each setpoint during the measurement. Nonetheless, you can add "break_conditions" to gettable parameters, which are checked at each setpoint and
will raise an exception and (in most cases) stop the measurement when fulfilled. At the moment only break conditions checking whether the value of a parameters is larger or smaller than the value specified are supported. Break conditions are added
as a list of strings (you can have multiple break conditions) consisting of the "val" keyword (to indicate you are interested in the value of the parameters, more to come), a comparator ("<", ">", "=") and a value. The parts of the strings have to
be separated by blanks.

.. note::

	Note that parameters can be both, gettable and static ("type": "static gettable"). This might be counter intuitive at first as you always know the value of static parameters. However, static parameters are not recorded
	in the QCoDeS database but only stored in the metadata (and the station snapshot) and it might be handy to have the corresponding values together with the measurement data instead of having to search for them elsewhere.
	Static gettable parameters are not actually recorded, but instead it is assumed that they are just constantly at their "value". This speeds up unbuffered measurements significantly due to the reduced communication between PC
	and measurement instrument and also allows to add the values of not bufferable parameters (e.g. DAC voltages) in buffered measurements.

In our case we added a maximum current as we want to stop the measurement when the current becomes to large (e.g. we want to stop once we see accumulation).
For the Dummy DMM and its random values the measurement will stop at a random point of course.

In case you want to ignore a parameter during a measurement, simply make its type an empty string "".


###################
Measurement Scripts
###################

Obviously, the measurement is not yet completely defined. We still have to a create measurement script or -more precisely- a measurement_script object.
In QuMADA all information relevant for the measurement are stored in this object, including the terminal_parameters and their mapping to the used instruments,
the details about how the measurement has to be performed and some metadata such as a sample and measurement name. Set metadata to None in case you have no connection to the metadata db.
QuMada will automatically name your measurement, if neither metadata nor a measurement name is provided based on the gates involved and the type of the measurement.

.. code-block:: python

	script = Generic_1D_parallel_asymmetric_Sweep()
	script.setup(parameters, metadata = None, ramp_rate = 0.5, back_after_break = True)

For our first measurement we use the Generic_1D_parallel_asymmetric_Sweep method, which ramps all dynamic parameter in parallel.

.. note::

	Parallel sweeps require the same number of setpoints for all dynamic parameters.


Note that we do not directly pass the arguments when creating the object but use the built-in "setup" method. It is required to pass the parameters and optionally a metadata object.
All measurement_script objects have an initialize method, which takes care of ramping/setting all parameters to the correct values and furthermore creates a couple of attributes,
like lists of all sweeps, different parameters and so on. Furthermore, they will automatically relabel the parameters in the QCoDeS datasets to match the gate names you specified. If your plotting tool uses the
"label" attribute of parameters for its plot, the axis will thus be labeled correctly.
When using the predefined measurement scripts that come with QuMADA those steps are automatically performed whenever you run the measurement. In case you define your own measurement scripts, you are free to use those built-in methods as you need them.
Furthermore, measurement scripts can have keyword arguments specifying details on how the measurement is performed. In this case we set the ramp_rate, which is again built-in into all measurement script objects and defines the ramp_speed used to ramp all parameters
to their starting value as well as the back_after_break parameter, which automatically adds a backsweep to the measurement once a break condition is fulfilled. This is particulary handy for accumulation curves including hysteresis investigations.

At this point we have a well defined measurement script that has a list terminals and parameters and knows what to do with them. The last step is now to assign the terminals to their corresponding instrument channels.


##################################
Mapping terminals to instruments
##################################

Assigning the terminals to their correspoing instruments channels can be either done manually or by passing an already existing terminal mapping. The terminal mapping is stored inside the measurement script and can be accessed via measurement_scipt.gate_parameter.
The gate mapping can be performed either per function or using a GUI (it is strongly recommend to use the latter):

.. autofunction:: qumada.instrument.mapping.base.map_gates_to_instruments

.. autofunction:: qumada.instrument.mapping.mapping_gui.map_terminals_gui

In our case we can simply pass station.components containing all the measurement instruments and their parameters and script.gate_parameters. If we already had a mapping from a previous measurement, we could simply pass it as third argument. Map_gates_to_instruments is also
capable of handling existing mappings with different parameters than the current measurement script, you only have to add the changed parameters manually then.

.. code-block:: python

	map_terminals_gui(station.components, script.gate_parameters) #script.gate_parameters will be renamed to terminal_parameters in a coming update

You are now asked for each registered gate/terminal to specify an instrument (or instrument channel) to map to. You can use drag and drop to map the parameters (or complete terminals) to their corresponding channels.
Check the section regarding the mapping GUI for more information (:ref:`MappingGui`).


########################################
Save and load mapped terminal parameters
########################################

For recurring measurements with the same terminals and instruments, it is possible to save terminal parameters and the mapped instrument parameters to a file and later load the mapping again. With this, the mapping process is only needed once.

.. autofunction:: qumada.instrument.mapping.base.save_mapped_terminal_parameters

.. autofunction:: qumada.instrument.mapping.base.load_mapped_terminal_parameters

.. note:

	The loading feature is currently only functional if the parameters you want to load match the ones in the saved mapping exactly. Otherwise an exception will occur. In case you want to add terminals or parameters, you can work around that
	issue by first loading the mapping for the original, unchanged parameters. Once you have loaded the mapping to a script or device object, alter the parameters dictionary and update the script or device object.
	If you now run the mapping GUI again, add the mapping (script.gate_parameters for scripts) as third input argument, you only have to map the new terminals/parameters instead of all of them. You can then save the mapped terminal parameters to a new file for
	usage with the new parameters.


###################
Run the measurement
###################

Finally you can use

.. py:function:: script.run()

to start the measurement.

#####################################################
Accessing Measurent Data and Plotting the Measurement
#####################################################

QuMADA does not have separate live-plotting tool so far, instead you have to use the plottr-inspectr as described in the `QCoDeS documentation <https://qcodes.github.io/Qcodes/examples/plotting/How-to-use-Plottr-with-QCoDeS-for-live-plotting.html>`_.
However, the "utils section" has a couple of tools that make working with the QCoDeS database, in which the data is stored, easier.



##########################
2nd Measurement: 1D-Sweeps
##########################

As a second example measurement and to understand the concept of QuMada measurements better let us perform 1D sweeps with the two gates separately.
While we sweep one of the gates, the other one should remain at a voltage at which it is still accumulating, otherwise we cannot see any signal.
Obviously, we could simply create two new parameter dictionaries. In the first one, we set the topgate to "dynamic" and the barriers to "static" with some "value" (let's say 0.4 V) and in the second we swap the types.

This can be uncomfortable for more complex devices with many gates, so QuMada provides a simpler solution. We can define the parameters as follows:

.. code-block:: python

	parameters = {
		"ohmic": {
			"current": {
				"type": "gettable",
			},
		},
		"topgate": {
			"voltage": {
				"type": "dynamic",
				"setpoints": np.linspace(0, 0.5, 100),
				"value": 0.5
			}
		},
		"barriers": {
			"voltage": {
				"type": "dynamic",
				"setpoints": np.linspace(0, 0.4, 100),
				"value": 0.4
			},
		},
	}

In comparison to the original parameters we removed the break condition (we do not need it anymore), the delay (to keep things simple, it is 0 by default and the communication time between PC and instruments is usually so large, that delays are not required),
and added values to the topgate and the barriers.
Instead of using the Generic_1D_parallel_asymmetric_Sweep we now use the Generic_1D_Sweep.


.. code-block:: python

	mapping = script.gate_parameters  # We can reuse the already existing mapping. It is stored in script.gate_parameters
	script = Generic_1D_Sweep()
	script.setup(parameters, metadata = None)
	map_terminals_gui(station.components, script.gate_parameters, mapping)
	script.run()

Note, that we first store the mapping from the last measurement to a different variable, as we are overwriting the first script. We can pass the existing mapping on to the new script as 3rd argument of map_terminals_gui, so we do not have to do it again.

The Generic_1D_Sweep start one measurement for each dynamic parameters, so we will end up with two measurements in this case. In each measurement, one of the dynamic parameters is ramped (or more precisely set to its setpoints, one could use arbitrary setpoints here) while all other
dynamic parameters are treated as "static gettable" and thus keep constant. As usual, QuMada will ramp all of those parameters to their "value" at the beginning of each measurement.
In the first measurement, the topgate is ramped and the barriers are kept at 0.4 V. In the second measurement, the barrier are ramped from 0 V to 0.4 V and the topgate is kept constant at 0.5 V.

###########################
3rd Measurement: 2D-Sweep
###########################

As last measurement in this tutorial, we will create a 2D barrier-barrier scan. For this purpose, we assume that we now have two individually controllable barriers.
Our parameters dictionary could look like this.



.. code-block:: python

	parameters = {
		"ohmic": {
			"current": {
				"type": "gettable",
			},
		},
		"topgate": {
			"voltage": {
				"type": "static gettable",
				"setpoints": np.linspace(0, 0.5, 100), #The setpoints are ignored if a parameter is not dynamic
				"value": 0.5
			}
		},
		"barrier 1": {
			"voltage": {
				"type": "dynamic",
				"setpoints": np.linspace(0, 0.4, 100),
			},
		},
		"barrier 2": {
			"voltage": {
				"type": "dynamic",
				"setpoints": np.linspace(0, 0.4, 100),
			},
		},
	}

We set the topgate to static gettable, as we want to keep it constant, but might want to easily check its voltage at a later time after the measurement. "static gettable" will add its value to the measurement data.
Note that we did not delete the setpoints for the topgate. They are not evaluated for parameters that are not dynamic. It is often convenient to copy&paste or simply alter parameter dictionaries and it is
often faster not to delete all unrequired parameters.
This time, we are using the Generic_nD_Sweep(). Instead of ramping all parameters individually, it goes through all combinations of setpoints. In our case this will result in the desired barrier-barrier scan.
While higher dimensions are possible by simply adding more dynamic parameters, be aware that plotting them with the plotter-inspector might not work.
By default, the first occuring dynamic is the "fast" parameter ("sweep"-parameter, inner loop) while the out one is the "slow" parameter ("step"-parameter, outer loop). For details on how to change that without
altering the order of the parameters, check the sections about groups and priorities (REF MISSING).


.. code-block:: python

	script = Generic_nD_Sweep()
	script.setup(parameters, metadata = None)
	map_terminals_gui(station.components, script.gate_parameters, mapping)
	script.run()

Again, we used the existing mapping to make the mapping process easier. As we changed the parameters dictionary this time -we removed the barriers and added barrier 1 and barrier 2- the mapping GUI will open up.
Note that the unaltered parameters from the topgate and the ohmics are still mapped, we only have to map the two new parameters.

Running the script should then start the desired measurement.

You are now able run simple measurements with QuMada. Again, we want to point out that this is not the most comfortable to run measurements in QuMada, we highly recommend that you have a look at the :ref:`DeviceObject`.

Other insteresting sections to follow up are the ones regarding :ref:`BufferedMeasurements` and a more detailed documentation of the different :ref:`MeasurementScripts`.





Adding the QuMADA Buffer Class to Instruments (WIP)
-----------------------------------------------------------------------

Using QuMADA for doing buffered measurements requires the measurement instruments to have a QuMADA "Buffered" Class.
In analogy to the gate mapping it will map the instrument's buffer's properties and functions to a common QuMADA interface.

In this tutorial we will go through the most important steps for writing such a class using a Dummy DMM.
The Dummy DMMs Driver can be found in qumada/instrument/custom_drivers/Dummies/dummy_dmm.py.

Our custom buffer inherits from

.. py:class:: Buffer(ABC)

Buffer() contains list of allowed setting names, trigger modes, triggers, etc. required to validate the input parameters.
Furthermore, a couple of required properties and (abstract)methods are defined. This is required to ensure compatibility of custom buffer classes
with QuMADA measurements.

.. code-block:: python

	class DummyDMMBuffer(Buffer):

		"""Buffer for Dummy DMM"""

		AVAILABLE_TRIGGERS: list[str] = ["software"]

		def __init__(self, device: DummyDmm):
			self._device = device
			self._trigger: str | None = None
			self._subscribed_parameters: set[Parameter] = set()
			self._num_points: int | None = None

Our buffer class requires a list of valid triggers (for real instrument those represent different trigger inputs), a trigger property, which is set later during the measurement,
a set of subscribed parameters, which will later contain the parameters you want to measure and the number of datapoints to be stored in the buffer. This value is set when mapping the instruments
to the gate parameters, but is required to compare the number of setpoints with the buffer length.

Now we can add the other required methods and parameters:

.. py:function:: num_points

A num_points property is required a represents the number of setpoints of the measurements. It tells QCodes how many datapoints have to be read out and allows
it to return only the relevant data. Depending on the measurement instrument it is necessary to pass this information on to the driver/the instrument, however, this is done in the setup
method below.
Keep in mind that the buffer settings can contain any combination of two of the parameters sampling_rate, burst_duration and num_points.
In some cases it is required to calculate the num_points from the other two. A possible implementation could look as follows.

.. code-block:: python

	@property
	def num_points(self) -> int | None:
		return self._num_points

	@num_points.setter
    def num_points(self, num_points) -> None:
        if num_points > 16383:
            raise Exception("Dummy Dacs Buffer is to small for this measurement. Please reduce the number of data points or the delay")
        self._num_points = int(num_points)

    def _set_num_points(self) -> None:

        if all(k in self.settings for k in ("sampling_rate", "burst_duration", "num_points")):
            raise Exception("You cannot define sampling_rate, burst_duration and num_points at the same time")
        elif self.settings.get("num_points", False):
            self.num_points = self.settings["num_points"]
        elif all(k in self.settings for k in ("sampling_rate", "burst_duration")):
                    self.num_points = int(
                        np.ceil(self.settings["sampling_rate"] * self.settings["burst_duration"])

.. py:function:: subscribe(self, parameters: list[Parameter]) -> None

We have to tell the QuMADA Buffer as well as the instruments which parameters shall be measured. Therefore, we need a subscribe method.
It requires a list of parameters to add. The subscribe method has to make sure that the chosen parameters are valid (part of the instrument and
usable in combination with the buffer and each other), tell the measurement instrument to write the parameters' measurement values into its buffer and
add the parameters to the _subscribed_parameters property of the buffer class.

.. code-block:: python

    def subscribe(self, parameters: list[Parameter]) -> None:
        assert type(parameters) == list
        for parameter in parameters:
            self._device.buffer.subscribe(parameter)
            self._subscribed_parameters.add(parameter)

.. _SensorCompensation:
Sensor Compensation
--------------------------

Some Qumada measurements support linear sensor compensation. Currently supported are Generic_2D_buffered_Measurement, Generic_Pulsed_Measurement and Generic_1D_buffered_Measurements.
All other measurements will ignore parameters of type "compensating". In order to use a parameter to compensate for the changes of another parameter you have to alter the gate parameters accordingly.
After defining the measurement as explained in the previous sections, set the "type" of the parameter you want to use for compensation (e.g. the Plunger Gate Voltage of an SET) to "comp" (or "compensating").
Add the keywords

* "compensated_gates" :  [{"terminal1" : "<gate_name>", parameter : "<parameter_name>}", {"terminal2" : "<gate_name>", parameter : "<parameter_name>}" , etc...]
* "leverarms" : [leverarm1, leverarm2, ....]
* "limits": [min_val, max_val] and assign a
* "value" : float

to the parameters dictionary.

The leverarms represent the relative leverarm of the gates, e.g. if you set it to 0.5, 1 V change in the compensated gate will lead to 0.5 V change of the compensating gate.
The limits (list with two floats) work as safety measure to avoid unwanted large voltages, an Exception is erased if the measurement would surpass them.

.. note::

	The safety limits check has to be done inside the measurement.run() as the actual setpoints of the compensating values depend on the type of measurement.
	Make sure to consider this when writing your own measurement scripts.

The value is set at the starting point of the compensated gate's sweep, e.g. if your compensated gate is swept lineariliy from 0 to 1 V, the value of the compensating gate is set to 0.5 V and the leverarm is 0.5, your compensating gate will be swept
from 0.5 to 1.0 V. The formula to calculate the setpoints for the compensating gates is setpoints_comp_gate = value_comp_gate - leverarm \times (setpoints - setpoints[0]).
If one gate compensated multiple gates, it will add the contributions from the different gates, e.g. setpoints_comp_gate = value_comp_gate - leverarm1 x (setpoints1 - setpoints1[0])- leverarm2 x (setpoints2 - setpoints2[0]) - ...

A working example with dummy instruments "buffered_dummy_example_compensation.py" can be found in the qumada examples folder.

Of course, the compensation has to be included in the measurement scripts. Right now, the initialize method of the script will create a list of sweeps for compensation (script.compensating_sweeps) that can be used in the measurement script.run(). Look into the initialize() method for more details.

.. note::
	For non-linear compensation one can use parameter groups, set the compensating parameters to "dynamic" and provide the corresponding setpoint arrays.
	Currently, groups are supported by the basic qumada measurement class and handle in the initialization, but are not used in the generic measurement scripts.

You can find a working example with dummy instruments under src/examples/buffered_dummy_example_compensation.py.
