.. _DeviceObject:

Device Object
===============

The device object is a representation of the device under test and allows fast access to parameters and measurements.
Conceptually it is very similar to the parameters dictionary but offers the advantages of a class.
In analogy to the paramters dictionary, each device has terminals, which again have terminal parameters. Again, terminals represent
functional parts of the real devices such as gates or ohmic contacts and parameters the physical quantities that can be changed or
measured for each of those terminals, such as voltages, currents or temperatures.

To get a quick overview over the device_object's capabilities we recommend to go through the device_object_example.py, which can be found in qumada\src\examples.
It provides a couple of examples and works with dummy instruments.


Creating a Device
-----------------

###################################
Creating from parameters dictionary
###################################

The recommended and probably fastest way to create an instance of the QumadaDevice object class is to generate it automatically from
an existing parameters dictionary. All dictionaries (independently if created manually or loaded from a json or yaml file) that
are compatible with any measurement scripts are valid.

.. code-block:: python

	from qumada.measurement.device_object import QumadaDevice
	parameters = {
		"ohmic": {
			"current": {
				"type": "gettable",
				"break_conditions": ["val > 100e-12"]
			}
		}
		"gate 1": {
			"voltage": {
				"type": "dynamic",
				"setpoints": np.linspace(0, 1, 50),
			}
		}
	}


	device = QumadaDevice.create_from_dict(parameters, station=station, namespace = globals())


This code will create a device with two terminals, "ohmic" and "gate". The "ohmic" has one parameter "current" and
the "gate" one parameter "voltage". As for the parameters defining measurements, the parameters have to match the Qumada conventions
and be in the whitelist for valid parameter names. Additional attributes such as "type", "setpoints" or "value" have no direct influence
when creating the object but are stored and can be accessed later e.g. for running measurements. In particular "values" are NOT directly
set for parameters for safety reason. Creating a device has no direct influence on any instrument settings or applied values.

If the "namespace" argument is not None, all created terminals are added to the provided namespace for easier access.
In this example, all terminals are added to the global namespace, such that it is possible to for example directly access the ohmic's current
by calling "ohmic.current()" instead of "device.ohmic.current()". Be aware, that automatically adding variables to the global namespace is not
always a safe practice, make sure you are familiar with possible issues arising from this before you use the feature. To minimize the risks,
QuMada will not override existing variables and will return an exception if terminals cannot be added to a namespace.

.. note::

	Blanks in terminal names are replaced by underscores, the variable refering to the gate is consequently "gate_1".
	However, the name in the list of terminals (device.terminals) remains "gate 1". As for measurement scripts, the labels
	of mapped QCoDeS parameters are relabled to the terminal name, to give e.g. more meaningful names in plots. An underscores
	would be annoying in this case.

An existing QCoDeS station (cf. QCoDeS documentation and QuMada tutorial on measurements) can be added as optional argument during the creation process
(or later via "device.station = station") to make its components available for the mapping process.

.. note::

	It is possible to create a device object by first creating an instance of the device_object (e.g. "device = QumadaDevice()") and then adding terminals and parameters using
	"device.add_terminal(terminal_name)" and  "device.terminal_name.add_terminal_parameter(parameter_name)". However, this is rather inconvenient and it is strongly recommended to
	use dictionaries.


.. _UpdatingDevice:
###########################
Updating an existing device
###########################

It is easily possible to add or remove terminals and parameters to or from the device.
Terminals can be added by calling the built-in method "add_terminal(terminal_name)" and be removed with "remove_terminal(terminal_name)".
Parameters can be added by calling "terminal_name.add_terminal_parameter(param_name)" and be removed with
"terminal_name.remove_terminal_parameter(param_name)".
An oftenmore convenient method is to simply load an updated parameters dictionary.
If you call "device.load_from_dict(param_dict)" all parameters and terminals from the dictionary that were not already in the device are
added automatically. Note, that it is usually necessary to repeat the mapping process for the new parameters.




Mapping
-------------


As for measurement scripts it is required to map the device object to the available measurement instruments. The QuMada mapping method is
compatible with the device object.

.. code-block:: python

	map_terminals_gui(station.components, device.instrument_parameters)

Opens the mapping GUI. The mapping is stored in device.instrument_parameters and it is possible to pass an existing mapping to
map_terminals_gui to reuse an existing mapping. As for measurement scripts mappings can be saved to files and be loaded again.
It is recommended to pass the QCoDeS station to the device (cf. "Creating from parameters dictionary"). In this case the mapping
can simply be done via "device.mapping()", which opens up the mapping GUI without asking for additional arguments.


Using the device
----------------------

####################################
Setting and Getting Parameters
####################################

With the mapping done it is now possible to use the device, its terminals and parameters.
"device.terminal_name.parameter_name()" calls the get command of the mapped instrument parameter, "device.terminal_name.parameter_name(value)" sets
it to the value. If the terminals were added to global namespace, they can be called without "device". As QuMada is tailored for experiments with
gated quantum dots where the most accessed parameters are gate voltages, the voltage parameter can be directly accessed by just calling its terminal,
e.g. "gate_1()" will return "gate_1.voltage()" and "gate_1(1)" will set the voltage of gate 1 to 1 V. For all other parameters (even if there is only
one parameter for a certain terminal) it is required to access the parameters explicitely. Also, this works only for calling the terminal.
If you try to access other attributes or methods of the voltage parameter you still have to call it explicitely. E.g. "gate_1.setpoints" will not return
return the setpoints of the voltage!

In case you want to set a parameter with a numeric value (such as a voltage), e.g gate1.voltage(1), it is ramped to the provided value and not instantly set.
This behaviour can be changed globally by setting "device.ramp = False" (default is true) or for each parameter individually by setting "device.parameter.rampable" to True or False.
The ramp rate of each parameter can be adjusted via "device.parameter.ramp_rate". By default, the maximum time a ramp can take is limited to 5 sec, if the ramp_rate is to low it will
be changed to ensure a smooth ramp to the target value within this time. The ramp_time parameter can be set via the "ramp_time" argument of ramp-method of parameters.
Independently of the settings, you can always use "terminal.parameter.ramp(target, ramp_speed)" to ramp to a certain value.

It is possible to print all voltages of the device by calling "device.voltages()" for a quick overview.

#################################
Ramping and Simple Measurements
#################################

The device object can be used to run any kind of measurement without the need to work with parameter dictionaries.
Most measurements can be started on the device level, furthermore it is possible to start 1D sweeps of individual parameters by calling gate.parameter.measured_ramp().
"gate_1.voltage.measured_ramp(target)" will automatically start a new measurement (in the currently active QCoDeS database and for the currently active experiment container) ramping from the current value
to the target. This offers a very quick and intuitive way to record measurements based on the current device working point.

Note that there are a couple of optional arguments for the measured_ramp method to specify the starting point, the number of points, if the measurement
should be buffered and its name.

To quickly benchmark a devices stability it is possible to record a timetrace with device.timetrace(duration), 2D scans centered at the current working point
can be recorded with device.sweep_2D(slow_param, fast_param, slow_param_range, fast_param_range). Again, both feature multiple additional arguments and can
be buffered. "device.run_measurement()" is capable of running any QuMada measurements script (including self-written ones) on device level. Thus, it is possible to use
the full functionality of QuMada without working with parameter dictionaries!

For more details on the individual available measurement types and their arguments check the measurements/device_object section of :ref:`API_DOC`.

In all cases mentioned so far the working point of the device is defined by getting the current values of all mapped parameters.
Values and setpoints defined in the parameter dictionary are not used for measurements started with built-in methods to avoid confusion. However, only parameters of
type "gettable" are recorded in those measurements. All other parameters are temporarily set to "static" except for the parameters that are to be ramped
in the 1D or 2D sweeps, those are temporarily set to dynamic. To record a value that was not specified to be "gettable" when the device was created can simply
be set to "gettable" by changing its type:
"device.terminal.parameter.type = 'gettable'". If you do not want to record nor explicitely set a parameter set it to "".
Values from the parameters dictionary are stored in device.terminal.parameter._stored_value to distinguish them from device.terminal.parameter.value which is
the current value of the parameter. However, in case you want to use the values and setpoints from the parameter dictionary instead of the one specified
in the function call of measurement scripts, you can set the argument priorize_stored_values to True.

################################
Storing and Loading Setpoints
################################

Another important feature is the possibility to save and load device working points. To store a certain configuration as your default working point,
use device.save_defaults. This stores all parameter values (of parameters that can be set). With device.set_defaults() you can reset it to the stored
configuration. Alternatively you can use "device.save_state(name)" and "device.set_state(name)" to store and set multiple working points with
custom names. They can also be accessed via "device.states" in case you forgot the name.
For all of those methods the parameters are ramped to the final state by default (with the default QuMada ramp rate).


############################
Buffered Measurements
############################

You can use the device_object to run buffered measurements in an even more comfortable way then with the measurement_script based approach.
It is possible to store all relevant buffer settings in the device_object. The measurements will then use the stored settings by default unless you explicetly specify
different ones.

The settings are identical to the ones discussed in :ref:`BufferedMeasurements`.
Create the buffer_settings dictionary and simply set

.. code:: python

	device.buffer_settings = buffer_settings

The arguments usually passed to the measurement script, which define the way the buffered measurement is started (e.g. trigger_start, trigger_type, sync_trigger and trigger_reset),
can be put into a second dictionary named " buffer_script_setup", for example:

.. code-block:: python

	buffer_script_settings = {
  	  	"trigger_type": "hardware",
   	 	"trigger_start": trigger.set,
  	 	"trigger_reset": trigger.clear,
	}
	device.buffer_script_setup = buffer_script_settings

.. note::
	The distintion between those parameters might appear arbitrary at the first glance. Buffer_settings specify how the buffers and trigger of the instruments are setup,
	whereas the buffer_script_setup tells the script how to start and handle buffered measurements. We are considering to combine the two in the future.

The trigger mapping can be done as usual by running:

.. code:: python

	map_triggers(station.components)

To run a buffered measurement, simply set the "buffered" kwarg to True when running the measurement, e.g.

.. code:: python

	device.timetrace(duration = 200, buffered = True)

For most scripts that can be started from the device level,
QuMada automatically uses the buffered version of the script if you set "buffered" to True.
If you use the arbitrary "device.run_measurement()" you obviously have to specify a buffered script yourself. Keep in mind that not all measurement scripts support buffered measurements.
It is always possible to override the settings stored in the device object by explicitely passing the buffer_settings and buffer_script_setup dictioniaries as corresponding arguments
when runing a measurement.
As it is quite common to frequently adjust the number of points recorded during a measurement, the number of points specified in the buffer_settings is overridden in case a number of points
or a setpoint array is specified when running a measurement. QuMada will provide a warning if this happens.
For example:

.. code-block:: python

	buffer_settings = {
    		"trigger_threshold": 0.005,
    		"trigger_mode": "digital",
    		"sampling_rate": 20,
   		"num_points": 100,
    		"delay": 0,
	}
	device.buffer_settings = buffer_settings

	device.gate1.voltage.measured_ramp(0.5,  buffered = True, num_points = 200)

will record a measurement with 200 datapoints. This works only if "num_points" and either "duration" or "sampling_rate" are specified in the buffer settings.
If you provide "duration" and "sampling_rate" you have to ensure that the number of points matches duration x sampling_rate or an exception will occur.
In this case, the buffer settings are overdefined and QuMada has no way of guessing your intend.
Thus, it is recommend to specify "sampling_rate" and "num_points" in the buffer settings.

###################
Sensor Compensation
###################

Sensor compensation with the device_object works in the same way as explained in :ref:`SensorCompensation'.
Simply set the type of the compensating gates to "compensating" (or "comp") and specify the required attributes.
This can be done either by directly addressing them via "device.terminal.parameter.attribute_name" (recommended) or by altering the parameter dictionary and updating the device object
as described in :ref:`UpdatingDevice`. Again, sensor compensation works only for a few measurement types.

##################
Safety features (WIP)
##################

Maximum parameter ranges can be defined via

.. code:: python

	device.terminal.parameter.limits = [min_val, max_val]

Those limits are then added to the validators of the underlying QCoDeS parameters.

.. note::
	Those limits are not checked in buffered measurements! Use them only as additional safety feature and do not rely on them!

It is also possible to directly add a "limits" keyword to the parameter dictionary, limits are automatically applied if the dictionary
is used to create a device object.
With

.. code-block:: python

	device.terminal.parameter.locked = True

you can look parameters. They cannot be changed (on the device object level) until unlocked again.
