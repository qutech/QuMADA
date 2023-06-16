# QuMADA
Interfaces and measurement scripts for usage with QCoDeS.

## Installation

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

### Install QuMADA

Install QuMADA directly from PyPI:

```
python -m pip install qumada
```

Alternatively, install the latest development version of QuMADA from github:

```
git clone https://github.com/qutech/qumada.git qumada
cd qumada
python -m pip install -e .
```

You can also install optional dependencies, like *Spyder* or QCoDeS' *plottr-inspectr*:

```
python -m pip install -e .[spyder,gui]
```

### Setup for development

For development, first clone the latest development version of QuMADA from github:

```
git clone https://github.com/qutech/qumada.git qumada
cd qumada
```

The requirements are stored in *dev_requirements.txt*.

```
python -m pip install -r dev_requirements.txt
```

Set up pre-commit hooks

```
python -m pre-commit install
```

### Documentation

To build the documentation, run:

```
cd docs
make html
```

The built documentation can be found at `_build/html/index.html`.
