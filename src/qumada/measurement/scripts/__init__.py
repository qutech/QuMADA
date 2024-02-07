# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# QuMADA. If not, see <https://www.gnu.org/licenses/>.
#
# Contributors:
# - Daniel Grothe
# - Till Huckeman

from .generic_measurement import (
    Generic_1D_Hysteresis_buffered,
    Generic_1D_parallel_asymm_Sweep,
    Generic_1D_parallel_Sweep,
    Generic_1D_Sweep,
    Generic_1D_Sweep_buffered,
    Generic_2D_Sweep_buffered,
    Generic_nD_Sweep,
    Timetrace,
    Timetrace_buffered,
    Timetrace_with_sweeps,
    Timetrace_with_Sweeps_buffered,
)

try:
    from .spectrometer import Measure_Spectrum
except ModuleNotFoundError:
    # Only relevant if you want to use spectrometer.
    # Requires access to Bluhm Group GitLab
    pass
except ImportError:
    pass

__all__ = [
    "Generic_1D_Sweep",
    "Generic_1D_Sweep_buffered",
    "Generic_nD_Sweep",
    "Generic_1D_parallel_Sweep",
    "Generic_1D_Hysteresis_buffered",
    "Generic_1D_parallel_asymm_Sweep",
    "Generic_2D_Sweep_buffered",
    "Timetrace",
    "Timetrace_with_sweeps",
    "Timetrace_buffered",
    "Timetrace_with_Sweeps_buffered",
    "Measure_Spectrum",
]
