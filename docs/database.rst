Metadata database
=================

The `qtools-db <https://git-ce.rwth-aachen.de/qutech/lab_software/qtools_db>`__ metadata database has the following structure:

.. image:: diagrams/ERD/ERD.svg

See below for a detailed description of each entity and its data fields.

Fabrication
-----------

.. image:: diagrams/ERD_fab/ERD_fab.svg

Wafer
^^^^^

.. py:data:: name
:type: str

Wafer name

.. py:data:: production_date
:type: date

Date of finished production

.. py:data:: description
:type: str

Description of wafer

.. py:data:: heterostructure
:type: link

Design of the heterostructure

.. py:data:: recipe
:type: link

Recipe followed, if all samples fabricated from wafer share the same recipe.
Includes notes on fabrication done.


.. py:data:: layout
:type: str

Layout, if all samples fabricated from wafer share the same layout



Factory
^^^^^^^

.. py:data:: name
:type: str

Factory name


Sample
^^^^^^

.. py:data:: name
:type: str

Sample name

.. py:data:: description
:type: str

Description of the sample

.. py:data:: fabrication_date
:type: date

Date of the finished fabrication

.. py:data:: creator
:type: str

Name of creator of the recipe

.. py:data:: recipe
:type: link

Recipe followed, includes notes on fabrication done

.. py:data:: fabricator
:type: str

Name of person responsible for fabrication



SampleLayout
^^^^^^^^^^^^

.. py:data:: name
:type: str

Layout name

.. py:data:: description
:type: str

Description of the layout


Device
^^^^^^

.. py:data:: name
:type: str

Device name

.. py:data:: description
:type: str

Description of the device

.. py:data:: comment
:type: str

Comment on the state of the device

.. py:data:: layout_parameters
:type: str

Relevant parameters of the device layout

.. py:data:: status
:type: str

State of the device
*This should probably be limited to a few choices*

.. py:data:: microscope
:type: str

Results of microscope investigation
*This should probably be limited to a few choices*

.. py:data:: annealing
:type: str

Annealing parameters
*Is this still necessary?*

.. py:data:: responsible_person
:type: str

Person responsible for the device at the current time

.. py:data:: deliver_date
:type: date

Date when the device was delivered to the responsible person

.. py:data:: current_location
:type: str

Current location of the device



DeviceLayout
^^^^^^^^^^^^

.. py:data:: name
:type: str

Device layout name

.. py:data:: description
:type: str

Description of the device layout

.. py:data:: image
:type: bytea

Image of the DeviceLayout
*Is this necessary?*

.. py:data:: creator
:type: str

Name of creator of the layout

.. py:data:: layout_file
:type: link

Link to layout design file

.. py:data:: layout_cell
:type: str

Cell referencing the location of the specific device layout
*Should default to "Top"*



Terminal
^^^^^^^^

.. py:data:: name
:type: str

Terminal layout name

.. py:data:: function
:type: str

Function of the terminal in the device

.. py:data:: number
:type: int

Assigned terminal number


.. Measurement
.. -----------

.. .. image:: diagrams/ERD_measurement/ERD_measurement.svg

.. Measurement
.. ^^^^^^^^^^^

.. MeasurementType
.. ^^^^^^^^^^^^^^^

.. MeasurementSettings
.. ^^^^^^^^^^^^^^^^^^^

.. MeasurementMapping
.. ^^^^^^^^^^^^^^^^^^

.. MeasurementScript
.. ^^^^^^^^^^^^^^^^^

.. MeasurementSeries
.. ^^^^^^^^^^^^^^^^^

.. MeasurementData
.. ^^^^^^^^^^^^^^^

.. ExperimentSetup
.. ^^^^^^^^^^^^^^^

.. Analysis
.. --------

.. Analysis
.. ^^^^^^^^

.. AnalysisResult
.. ^^^^^^^^^^^^^^
