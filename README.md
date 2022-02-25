# qtools
Interfaces and measurement scripts for usage with QCoDeS.

## Installation

First, clone the current version of qtools from gitlab

```
git clone git@git-ce.rwth-aachen.de:qutech/lab_software/qtools.git qtools
cd qtools
```

### Setup virtual environment

Installation of qtools should be done in a virtual environment.
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

Install qtools through pip

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

### Build documentation

Run

```
cd docs
make html
```

The built documentation can be found at `_build/html/index.html`.
