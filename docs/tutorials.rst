Tutorials
=========

First steps: Example Measurements (WIP)
---------------------------------

QTools is a QCoDeS based measurement framework that helps you performing measurements easily as well as dumping all required metadata in a database.
Before you start with this basic tutorial make sure to get familiar with QCoDeS, we recommend to work through the 15-Minute-To-QCoDeS tutorial to learn about setting up
a database for the measurement data, Experiment containers, the measurement context manager and the station object.
In this tutorial we assume that you already set up a QCoDeS database and created an experiment.

This tutorial will show you how to setup basic sweeps in QTools. In most cases you will start your measurements by using the main.ipy found in Qtools/src.
It contains a couple of blocks for the steps you have to do in order to set up the measurement and run it. We start by importing required submodules:

.. code-block:: python

	#Required to load parameter json or yaml
	import json
	import yaml

	#Drivers for the measurement instruments
	from qcodes.station import Station
	from qcodes.instrument_drivers.Harvard.Decadac import Decadac
	from qcodes.instrument_drivers.stanford_research.SR830 import SR830
	from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400
	from qcodes.instrument_drivers.QDevil.QDevil_QDAC import QDac

	#You need this to set up the QCoDeS database and experiment
	from qcodes.dataset import (
		Measurement,
		experiments,
		initialise_or_create_database_at,
		load_by_run_spec,
		load_or_create_experiment,
	)

	#QTools imports
	import qtools_metadata.db as db
	from qtools_metadata.metadata import Metadata
	from qtools.instrument.mapping import (
		add_mapping_to_instrument,
		DECADAC_MAPPING,
		SR830_MAPPING,
		KEITHLEY_2400_MAPPING,
		QDAC_MAPPING)
	from qtools.instrument.mapping.base import map_gates_to_instruments
	from qtools.measurement.scripts import (
		Generic_1D_Sweep,
		Generic_nD_Sweep,
		Generic_1D_parallel_Sweep,
		Timetrace)
	#Some methods helping you to do things faster
	from qtools.utils.load_from_sqlite_db import load_db
	from qtools.utils.generate_sweeps import generate_sweep, replace_parameter_settings
	from qtools.utils.ramp_parameter import *

#################
Station and Instruments
#################


After importing everything necessary we can start with setting up the QCoDeS station object and the measurement instruments.
In difference to QCoDeS measurements, QTools measurements scripts are largely independend from the instruments used. Nonetheless, it is still required to create a QCoDeS station
object and specify the instruments used, which is done by providing name and the address of the instrument using the corresponding QCoDeS methods.
In addition to this, we want to add an instrument mapping to each instrument. As QCoDeS drivers are supplied by many different people, the parameters of instruments are named
inconsistently. The voltage parameter of a Keithley 2400 DMM is addressed via Keithley.volt, the parameter of a Keithley 2450 via Keithley.source.voltage and the
voltage of a QDevil QDac channel via QDac.Ch01.v. When using QCoDeS, it is necessary to alter the measurement script accordingly whenever a different instrument is used. QTools deals with this issue
by introducing an additional abstraction layer, the gate_mapping. QTools uses predefined names for similar parameters making sure you can reuse your measurement scripts and do not have to browse through instrument
drivers in order to look up the right command.

.. note::

	Right now these names are specified in the measurement_scipt class. It will be moved to a separate file later on.
	When using an instrument not yet implemented into QTools you might have to specify new names for the parameters there.
	For more information look into the section about creating gate_mappings for new instruments

Adding the mapping is easily done by using the "add_mapping_to_instrument" command:

.. py:function:: add_mapping_to_instrument(instrument, mapping)

	Applies the mapping specified to the instrument

   :instrument: Instrument
   :mapping: Mapping, has to be imported from qtools.instrument.mapping and be listed in the corresponding __init__ file
   :return: None

.. code-block:: python

	# Setup qcodes station
	station = Station()

	# Setup instruments
	# Call add_mapping_to_instrument(instrument, mapping) to map the instrument's parameters to qtools-specific names.
	dac = Decadac(
		"dac",
		"ASRL3::INSTR",
		min_val=-10,
		max_val=10,
		terminator="\n")
	add_mapping_to_instrument(dac, DECADAC_MAPPING)
	station.add_component(dac)

	lockin = SR830("lockin", "GPIB1::12::INSTR")
	add_mapping_to_instrument(lockin, SR830_MAPPING)
	station.add_component(lockin)

	qdac = QDac("qdac", "ASRL5::INSTR")
	add_mapping_to_instrument(qdac, QDAC_MAPPING)
	station.add_component(qdac)

	keithley = Keithley_2400("keithley", "GPIB1::27::INSTR")
	add_mapping_to_instrument(keithley, KEITHLEY_2400_MAPPING)
	station.add_component(keithley)

In this sample we just add a couple of real instruments. Of course you can add QCoDeS dummy instruments as well and provide mappings for them.

.. note::

	There is a known bug that requires the instrument's name to be the same as the name found in the corresponding mapping file.
	This is especcially relevant when you want to use two instruments of the same type. We are working on a fix for this issue.
	As a workaround, you can create a second mapping file for the second instrument and alter the instrument name on the left side of
	the mapping file to the name of the second instrument.

#############
Metadata
#############


In the next step, we want to create a metadata object. The object contains all the metadata to store in the metadatabase and is furthermore used to supply
the metadata for the measurement script and the QCoDeS-database. Thus, you have to provide sample name and measurement name even if you do not intend to use
the metadatabase.

The easiest way to create the metadata-object is by entering the data into the metadata.yaml found in the QTools directory and create the object from this file.

.. code-block:: python

	# Set Metadata-DB URL
	db.api_url = "http://134.61.7.48:9124"
	# Load metadata.yaml
	with open("metadata.yaml", "r") as file:
		metadata = Metadata.from_yaml(file)

.. note::

	The metadata acquisition process is currently overhauled. For more details look into the Metadata section of this documentation.

The connection to the metadabase is required for loading information of already existing samples and measurements (so you do not have to enter them again) and
- of course - for storing the data. Right now, we are only interested in creating the metadata object for usage in our measurements.

In case you have not already initialized a QCoDeS database you can easily do so by using the load_db(path_to_db [optional) method, which either takes the path to the database you want to use or, when no argument is supplied,
opens an open-file prompt allowing you to simply pick the database you want to use (be aware that the prompt might pop up behind other windows).

At this point we have taken care of all preliminary steps required before defining the measurement.
Except for changing the measurement name in the metadata object, you will have to do those steps only when exchanging the sample or altering the setup.

From now on, we will go through a typical workflow for characterizing a gate-defined Single Electron Transistor (SET) in a semiconductor heterostructure such as Si/SiGe or Si MOS.
Measurements in QTools are mainly defined by two things: The gate_parameters and the measurement script used.


###############################
Gate parameters
###############################

The gate_parameters are part of each measurement script and contain a list of all physical terminals of the device under test (DUT) such as gates or ohmic contacts and information about what to do with them during the measurement.
The gate_parameters can be loaded from a yaml-file (or json-file if you prefer to double-check brackets all the time...):

.. code-block:: python

	# Load parameters
	with open("parameters.yaml", "r") as file:
		parameters = yaml.safe_load(file)

A typical parameters.yaml could look like this:

.. code-block:: yaml

	source drain:
	  amplitude:
		type: dynamic
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
		num_points: 200
		delay: 0.025
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
		type: dynamic
		start: 0
		stop: 2
		num_points: 200
		delay: 0.025

In our example the SET consists source and drain contact, a global accumulation gate, two barriers and a plunger gate for finetuning the dot potential.
In a first step we want to ramp all the gates in parallel to check whether we can accumulate charges and open a current path through the quantum well.
Furthermore, we want to apply a bias voltage between the source and drain contact and measure the current flowing through them using a lockin amplifier.
Each terminal or gate in QTools can have one or more parameters corresponding to physical properties such as voltage or current. In some cases it is still
necessary to think about instrument properties (in this case the lockin has an "output_enabled" parameter) and settings that have to be set. You can either change them
manually before the measurement or include them into the parameters. In the latter case they will be set automatically before the measurement start.

.. note::

	It is planned to move those mere "settings" which are only changed on rare occasions into some default setup files; the corresponding settings are then applied automatically before the
	measurement starts. Only when the required settings deviate from those defaults they have to be specified explicitely in the parameters.

Each of those parameters has a specific type: "dynamic", "static" and/or "gettable".

Dynamic parameters are ramped during the measurement, they require an array of setpoints or - as in our - case a start, stop and num_points value specifying a linear sweep as well as delay representing the delay
inbetween two measurement points. Dynamic parameters are automatically recorded during the measurement.

Static parametes are kept constant during the measurement, they only require a "value" to be set to. Float-valued parameters are ramped to their corresponding starting point at the beginning of a measurement, other parameters are simple set.
Static paramters usually correspond to settings or static gates.

Gettable parameters do not require any additional settings, their value is recorded at each setpoint during the measurement. Nonetheless, you can add "break_conditions" to gettable parameters, which are checked at each setpoint and
will raise an exception and (in most cases) stop the measurement when fulfilled. At the moment only break conditions checking whether the value of a parameters is larger or smaller than the value specified are supported. Break conditions are added
as a list of strings (you can have multiple break conditions) consisting of the "val" keyword (to indicate you are interested in the value of the parameters, more to come), a comparator ("<", ">", "=") and a value. The parts of the strings have to
be separated by blanks.

.. note::

	Note that parameters can be both, gettable and static ("type": "static gettable"). This might be counter intuitive at first as you always know the value of static parameters. However, static parameters are not recorded
	in the QCoDeS database but only stored in the metadata (and the station snapshot) and it might be handy to have the corresponding values together with the measurement data instead of having to search for it elswhere.

In our case we added a maximum current as we want to stop the measurement when the current becomes to large.

###################
Measurement Scripts
###################

Obviously, the measurement is not yet completely defined. We still have to a create measurement script or -more precisely- a measurement_script object.
In QTools all information relevant for the measurement are stored in this object, including the gate_parameters and their mapping to the used instruments,
the details about how the measurement has to be performed and some metadata such as sample and measurement name.

.. code-block:: python

	script = Generic_1D_parallel_Sweep()
	script.setup(parameters, metadata, ramp_rate = 0.3, back_after_break = True)

For our first measurement we use the Generic_1D_parallel_Sweep method, which ramps all dynamic parameter in parallel.

.. note::

	This measurement script uses the setpoints of the first gate_parameter to define the sweeps, the other parameter's setpoints are ignored at the current state.
	It is not trivial to merge arbitrary setpoint arrays with different delays into one sweep, we might improve the script in the future.


Note that we do not directly pass the arguments when creating the object but use the built-in "setup" method. It is required to pass the parameters and a metadata object.
All measurement_script objects have an initialize and a reset method, which take care of ramping/setting all parameters to the correct values and furthermore create a couple of attributes,
like lists of all sweeps, different parameters and so on. Furthermore, they will automatically relabel the parameters in the QCoDeS datasets to match the gate names you specified.
When using the predefined measurement scripts that come with QTools those steps are automatically performed whenever you run the measurement. In case you define your own measurement scripts, you are free to use those built-in methods as you need them.
Furthermore, measurement scripts can have keyword arguments specifying details of how the measurement is performed. In this case we set the ramp_rate, which is again built-in into all measurement script objects and defines the ramp_speed used to ramp all parameters
to their starting value as well as the back_after_break parameter, which automatically adds a backsweep to the measurement once a break condition is fulfilled. This is particulary handy for accumulation curves including hysteresis investigations.

At this point we have a well defined measurement script that has a list of gates or terminals and knows what to do with them. The last step is now to assign the terminals to their corresponding instrument channels.


##################################
Mapping terminals to instruments
##################################

Assigning the terminals to their correspoing instruments channels can be either done manually or by passing an already existing gate mapping object. The gate mapping is stored inside the measurement script and can be accessed via measurement_scipt.gate_parameter.
The method we use to perform the gate mapping is:

.. py:function:: map_gates_to_instruments(components, mapping, existing_mapping [optional])

In our case we can simply pass station.components containing all the measurement instruments and their parameters and script.gate_parameters. If we already had a mapping from a previous measurement, we could simply pass it as third argument. Map_gates_to_instruments is also
capable of handling existing mappings with different parameters than the current measurement script, you only have to add the changed parameters manually then.

.. code-block:: python

	map_gates_to_instruments(station.components, measurement_script.gate_parameter)

You are now asked for each registered gate/terminal to specify an instrument (or instrument channel) to map to. All available instruments are listed, you simply have to type in the number corresponding to the correct instrument.
As Qtools' :ref:`gate mapping<Station and Instruments>` has well defined parameter names the parameters are mapped automatically once the correct measurement instrument is specified.

.. note::

	Right now there are some issues with multichannel instruments such as the DecaDac. The different channels are all part of the same instrument, whenever you assign a parameter to the instrument the first unassigned channel will be mapped.
	In general this means that the channels are assigned in the order of their numbers (first parameter mapped to Channel 1, second parameter mapped to Channel 2, etc.) Make sure to add the parameters to the gate_parameters.yaml in the corresponding order.


Finally you can use

.. py:function:: measurement_script.run()

to start the measurement.

#####################################################
Accessing Measurent Data and Plotting the Measurement
#####################################################

Qtools does not have separate live-plotting tool so far, instead you have to use the plottr-inspectr as described in the `QCoDeS documentation <https://qcodes.github.io/Qcodes/examples/plotting/How-to-use-Plottr-with-QCoDeS-for-live-plotting.html>`_.
However, the "utils section" has a couple of tools that make working with the QCoDeS database, in which the data is stored, easier.




Adding the Qtools Buffer Class to Instruments
-----------------------------------------------

Using Qtools for doing buffered measurements requires the measurement instruments to have a Qtools "Buffered" Class.
In analogy to the gate mapping it will map the instrument's buffer's properties and functions to a common Qtools interface.

In this tutorial we will go through the most important steps for writing such a class using a Dummy DMM.
The Dummy DMMs Driver can be found in qtools/instrument/custom_drivers/Dummies/dummy_dmm.py.

Our custom buffer inherits from

.. py:class:: Buffer(ABC)

Buffer() contains list of allowed setting names, trigger modes, triggers, etc. required to validate the input parameters.
Furthermore, a couple of required properties and (abstract)methods are defined. This is required to ensure compatibility of custom buffer classes
with QTools measurements.

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

We have to tell the Qtools Buffer as well as the instruments which parameters shall be measured. Therefore, we need a subscribe method.
It requires a list of parameters to add. The subscribe method has to make sure that the chosen parameters are valid (part of the instrument and
usable in combination with the buffer and each other), tell the measurement instrument to write the parameters' measurement values into its buffer and
add the parameters to the _subscribed_parameters property of the buffer class.

.. code-block:: python

    def subscribe(self, parameters: list[Parameter]) -> None:
        assert type(parameters) == list
        for parameter in parameters:
            self._device.buffer.subscribe(parameter)
            self._subscribed_parameters.add(parameter)
