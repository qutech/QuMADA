Device Object
===============

The device object is a representation of the device under test and allows fast access to parameters and measurements.
Conceptually it is very similar to the parameters dictionary but offers the advantages of a class.
In analogy to the paramters dictionary, each device has terminals, which again have terminal parameters. Again, terminals represent
functional parts of the real devices such as gates or ohmic contacts and parameters the physical quantities that can be changed or
measured for each of those terminals, such as voltages, currents or temperatures.


Creating a Device
-----------------

######################
Creating manually
######################

TODO



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


	device = QumadaDevice.create_from_dict(parameters, station=station, make_terminals_global = True, namespace = globals())


This code will create a device with two terminals, "ohmic" and "gate". The "ohmic" has one parameter "current" and
the "gate" one parameter "voltage". As for the parameters defining measurements, the parameters have to match the Qumada conventions
and be in the whitelist for valid parameter names. Additional attributes such as "type", "setpoints" or "value" have no direct influence
when creating the object but are stored and can be accessed later e.g. for running measurements. In particular "values" are NOT directly
set for parameters for safety reason. Creating a device has no direct influence on any instrument settings or applied values.

The argument "make_terminals_global" adds all created terminals to the namespace provided in the "namespace" argument for easier access.
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

###################################
Parameters and simple measurements
####################################

With the mapping done it is now possible to use the device, its terminals and parameters.
"device.terminal_name.parameter_name()" calls the get command of the mapped instrument parameter, "device.terminal_name.parameter_name(value)" sets
it to the value. If the terminals were added to global namespace, they can be called without the device. As QuMada is tailored for experiments with
gated quantum dots where the most accessed parameters are gate voltages, the voltage parameter can be directly accessed by just calling its terminal,
e.g. "gate_1()" will return "gate_1.voltage()" and "gate_1(1)" will set the voltage of gate 1 to 1 V. For all other parameters (even if there is only
one parameter for a certain terminal) it is required to access the parameters explicitely. Also, this works only for calling the terminal.
If you try to access other attributes or methods of the voltage parameter you still have to call it explicitely. E.g. "gate_1.setpoints" will not return
return the setpoints of the voltage!

It is possible to print all voltages of the device by calling "device.voltages" for a quick overview.

"gate_1.voltage.ramp(target, ramp_speed)" can be used to ramp to a certain value, "gate_1.voltage.measured_ramp(target)" will automatically
start a new measurement (in the currently active QCoDeS database and for the currently active experiment container) ramping from the current value
to the target. This offers a very quick and intuitive way to record measurements based on the current device working point.
Note that there are a couple of optional arguments for the measured_ramp method to specify the starting point, the number of points, if the measurement
should be buffered and its name. For details look into TBD.

To quickly benchmark a devices stability it is possible to record a timetrace with device.timetrace(duration), 2D scans centered at the current working point
can be recorded with device.sweep_2D(slow_param, fast_param, slow_param_range, fast_param_range). Again, both feature multiple additional arguments and can
be buffered.

In all cases mentioned so far the working point of the device is defined by getting the current values of all mapped parameters.
Values and setpoints defined in the parameter dictionary are not used for measurements started with built-in methods to avoid confusion. However, only parameters of
type "gettable" are recorded in those measurements. All other parameters are temporarily set to "static" except for the parameters that are to be ramped
in the 1D or 2D sweeps, those are temporarily set to dynamic. To record a value that was not specified to be "gettable" when the device was created can simply
be set to "gettable" by changing its type:
"device.terminal.parameter.type = 'gettable'". If you do not want to record a parameter set it to "".
Values from the parameters dictionary are stored in device.terminal.parameter._stored_value to distinguish them from device.terminal.parameter.value which is
the current value of the parameter. However, in case you want to use the values and setpoints from the parameter dictionary instead of the one specified
in the function call of measurement scripts, you can set the argument priorize_stored_values to True.

Another important feature is the possibility to save and load device working points. To store a certain configuration as your default working point,
use device.save_defaults. This stores all parameter values (of parameters that can be set). With device.set_defaults() you can reset it to the stored
configuration. Alternatively you can use "device.save_state(name)" and "device.set_state(name)" to store and set multiple working points with
custom names. They can also be accessed via "device.states" in case you forgot the name. Be aware that the set commands currently set the
parameters instead of ramping to them, which can endanger your device if it is sensitive to voltage jumps.


###############
Safety features
###############

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
