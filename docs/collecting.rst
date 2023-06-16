Working with metadata
=====================

#################
Creating metadata
#################

Metadata is represented in a :py:class:`qtools_metadata.metadata.Metadata` object.
There are manual and guided ways to build up the metadata:

1. Create/Load metadata manually
2. Create/Load metadata using guided input functions
3. Load metadata from a local .yaml file

Create/Load metadata manually
-----------------------------

Each metadata object can be created using their respective factory method.

.. py:method:: DomainObject.create(name: str, **kwargs)
    :classmethod:

    This factory function creates a DomainObject while ensuring, that the internal DB fields are all set to None.
    This function is usually not called directly, but by the factory function of a child class.

    :param str name: Name of the DomainObject
    :rtype: DomainObject

For example, a Factory and Wafer metadata object would be created by

.. code-block:: python

    from datetime import date
    from qtools_metadata.device import Factory, Wafer

    prod_date = date(2022, 12, 12)
    factory = Factory.create(name="my_factory")
    wafer = Wafer.create(
        name="my_wafer",
        productionDate=prod_date,
        factory=factory,
        description="This is a wafer."
    )

To load metadata from the database, use one of their getter functions.

.. automethod:: qtools_metadata.domain.DomainObject.get_all

.. automethod:: qtools_metadata.domain.DomainObject.get_by_id

Depending on the object, there may be filtered get functions.

For example, to load a wafer and all samples from that wafer,
one would use :py:meth:`qtools_metadata.device.Wafer.get_by_id` and :py:meth:`qtools_metadata.device.Sample.get_by_wafer_id`.

.. code-block:: python

    from qtools_metadata.device import Wafer, Sample

    wafer: Wafer = Wafer.get_by_id("8c7576d8-ca5d-4b62-8bda-1f46f75d3266")
    samples: list[Sample] = Sample.get_by_wafer_id(wafer.id)

Create/Load metadata using guided input functions
-------------------------------------------------

Use one of various guided input functions, to create or load metadata or single metadata objects.
For measurement metadata, use :py:func:`qtools_metadata.metadata.create_metadata`,
for specific metadata objects, use :py:func:`qtools_metadata.metadata.create_metadata_object`:

Example:

.. code-block:: python

    from qtools_metadata.metadata import Metadata, create_metadata, create_metadata_object
    from qtools_metadata.device import Device
    from qtools_metadata.measurement import MeasurementScript

    # Create metadata for a measurement
    metadata: Metadata = create_metadata()

    # Create specific metadata objects
    device: Device = create_metadata_object(Device)
    script: MeasurementScript = create_metadata_object(MeasurementScript)


Load metadata from a local .yaml file
-------------------------------------

You can load a yaml representation of the metadata using :py:meth:`qtools_metadata.metadata.Metadata.from_yaml`

.. code-block:: python

    from qtools_metadata.metadata import Metadata

    with open("metadata.yaml", "r") as file:
        metadata = Metadata.from_yaml(file)


#################################
Automatically collecting metadata
#################################

When doing measurements, QuMADA automatically collects metadata during setup and run of the measurement.

Here is an overview of collected metadata and where it is collected:

.. autoattribute:: qtools_metadata.measurement.Measurement.datetime

.. autoattribute:: qtools_metadata.measurement.Measurement.data

The measurements datetime and a reference to the measured data is collected after calling :py:meth:`qumada.measurement.measurement.MeasurementScript.run`.
To turn off the collection, use arguments ``add_datetime_to_metadata`` and ``add_data_to_metadata``.

.. autoattribute:: qtools_metadata.measurement.Measurement.mapping

.. autoattribute:: qtools_metadata.measurement.Measurement.settings

.. autoattribute:: qtools_metadata.measurement.Measurement.script

The instrument mapping is added during :py:func:`qumada.instrument.mapping.base.map_gates_to_instruments`.
Script and settings are added during :py:meth:`qumada.measurement.measurement.MeasurementScript.setup`.
Use arguments ``add_script_to_metadata`` and ``add_parameters_to_metadata`` respectively to turn this off.

.. code-block:: python

    # ...

    # Don't add script or parameters to metadata automatically
    script.setup(
        parameters,
        metadata,
        add_script_to_metadata=False,
        add_parameters_to_metadata=False,
    )

    # Don't add datetime or data metadata automatically
    script.run(add_datetime_to_metadata=False, add_data_to_metadata=False)


################
Save to database
################

Before measurement, the created metadata is automatically saved to the database, if the measurement was setup with it.
This happens after calling :py:meth:`qumada.measurement.measurement.MeasurementScript.run`.
To deactivate this feature, use the argument ``insert_metadata_into_db``.

.. code-block:: python

    script: MeasurementScript = ...

    # Automatically save metadata to the database
    script.run()                              # default
    script.run(insert_metadata_into_db=True)  # explicit

    # Don't save metadata to the database
    script.run(insert_metadata_into_db=False)

Metadata or any domain object can be saved to the database manually by :py:meth:`qtools_metadata.metadata.Metadata.save_to_db` or :py:meth:`qtools_metadata.domain.DomainObject.save`.

.. code-block:: python

    from qtools_metadata.metadata import Metadata, create_metadata, create_metadata_object
    from qtools_metadata.measurement import Measurement

    # Save metadata recursively
    metadata: Metadata = create_metadata()
    metadata.save_to_db()

    # Save specific domain object
    measurement: Measurement = create_metadata_object(Measurement)
    measurement.save()


Override and copy behavior
--------------------------

During a save, qtools_metadata checks the local domain object differs from the DB.
If so, the user is asked if the entry should be overwritten or if a new copy should be created.

This behavior is not desirable, when measurements are performed without user interaction.
To set a standard behavior, one can set the flag :py:attr:`qtools_metadata.domain.db_overwrite_default`:

.. code-block:: python

    import qtools_metadata.domain

    # Set to "ask" (default), "overwrite" or "copy"
    qtools_metadata.domain.db_overwrite_default = "copy"
