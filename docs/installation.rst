Installation
============

First, clone the current version of QuMADA from gitlab

.. code-block:: console

    git clone git@git-ce.rwth-aachen.de:qutech/lab_software/qumada.git qumada
    cd qumada

Setup virtual environment
-------------------------

Installation of QuMADA should be done in a virtual environment.
There are several methods of creating a virtual environment, python's native being *venv*:

On *windows*, run

.. code-block:: console

    python -m venv .venv
    .venv\Scripts\activate.bat

On *linux*, run

.. code-block:: console

    python -m venv .venv
    source .venv/bin/activate

Setup for general use
---------------------

Install QuMADA through pip

.. code-block:: console

    pip install -e .

You can also install optional dependencies, like *Spyder* or the *ZurichInstruments MFLI instrument driver*:

.. code-block:: console

    pip install -e .[spyder,mfli]

Setup for development
---------------------

For development, the requirements are stored in *dev_requirements.txt*.

.. code-block:: console

    pip install -r dev_requirements.txt

Set up pre-commit hooks

.. code-block:: console

    pre-commit install

Build documentation
-------------------

Run

.. code-block:: console

    tox -e docs

or

.. code-block:: console

    cd docs
    make html

The built documentation can be found at :file:`_build/html/index.html`.
