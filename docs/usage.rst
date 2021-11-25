Usage
=====

Qtools is used through a shell-like command line.
Once executed, there are several commands to setup the experiment, write or load metadata to/from the database and run the measurements.

An overview of the available commands is shown below:

Metadata
--------

metadata load
    Loads a metadata object from a YAML-file.

metadata new
    Create an empty metadata object.

metadata print
    Print the metadata.

Instrument
----------

instrument list
    List all initialized instruments.

instrument add visa
    Add VISA instrument to station.

instrument add dummy
    Add Dummy instrument to station.

instrument delete
    Remove instrument from station.

instrument load_station
    Load a station file with previously initialized instruments.

instrument save_station
    Save a station to file.

instrument generate_mapping
    Generate a mapping stub from an initialized instrument.

Measurement
-----------

measurement script load
    Loads a measurement script.

measurement setup
    Setup the measurement.

measurement run
    Run the measurement.

measurement map_gates
    Map gates to instruments.
