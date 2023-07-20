Working with metadata
=====================

.. note::
    This section is Work in Progress.


#################################
Automatically collecting metadata
#################################

When doing measurements, QuMADA automatically collects metadata during setup and run of the measurement.

Here is an overview of collected metadata and where it is collected:

* The measurements datetime and a reference to the measured data is collected after calling :py:meth:`qumada.measurement.measurement.MeasurementScript.run`
  To turn off the collection, use arguments ``add_datetime_to_metadata`` and ``add_data_to_metadata``.
* The instrument mapping is added during :py:func:`qumada.instrument.mapping.base.map_gates_to_instruments`.
* Script and settings are added during :py:meth:`qumada.measurement.measurement.MeasurementScript.setup`.
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

Metadata or any domain object can be saved by :py:meth:`qumada.metadata.Savable.save` or updated by :py:meth:`qumada.metadata.Savable.update`. This only works for metadata implementations, that are savable.
