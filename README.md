# QuMADA
Interfaces and measurement scripts for usage with QCoDeS.

## Installation

First, clone the current version of QuMADA from gitlab

```
git clone git@git-ce.rwth-aachen.de:qutech/lab_software/qumada.git qumada
cd qumada
```

### Setup virtual environment

Installation of QuMADA should be done in a virtual environment.
There are several methods of creating a virtual environment, python's native being *venv*:

On *windows*, run

```
python -m venv .venv
.venv\Scripts\activate.bat
```

On *linux*, run

```
python -m venv .venv
source .venv/bin/activate
```

### Setup for general use

Install QuMADA through pip

```
pip install -e .
```

You can also install optional dependencies, like *Spyder* or the *ZurichInstruments MFLI instrument driver*:

```
pip install -e .[spyder,mfli]
```

### Setup for development

For development, the requirements are stored in *dev_requirements.txt*.

```
pip install -r dev_requirements.txt
```

Set up pre-commit hooks

```
pre-commit install
```

### Documentation

You can access the current documentation [here](https://qutech.pages.git-ce.rwth-aachen.de/lab_software/qtools/qumada)
or build your own:

Run

```
cd docs
make html
```

The built documentation can be found at `_build/html/index.html`.
