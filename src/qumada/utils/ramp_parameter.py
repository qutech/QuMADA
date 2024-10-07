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
# - Sionludi Lab
# - Till Huckeman
# - Tobias Hangleiter


from __future__ import annotations

import logging
import time
from math import isclose

from qumada.utils.generate_sweeps import generate_sweep

LOG = logging.getLogger(__name__)


class Unsweepable_parameter(Exception):
    pass


def ramp_parameter(
    parameter,
    target,
    ramp_rate: float | None = None,
    ramp_time: float | None = None,
    setpoint_intervall: float = 0.1,
    valid_units: str = "all",
    tolerance: float = 1e-5,
    **kwargs,
):
    """
    Used for ramping float-valued parameters. Allows to specify ramp_rate and/or
    ramp_time. The ramp_time provides an upper limit to the time the sweep may
    take if specified.

    Parameters
    ----------
    parameter : QCoDeS parameter
        Parameter you want to sweep
    target : float
        Target value.
    ramp_rate : float | None, optional
        Specify ramp rate for the sweep. Is only relevant when ramp_time is None
        or ramping is finished before ramp_time has passed. If ramp is to slow,
        ramp_time will be used to define the ramp_speed.The default is None.
    ramp_time : float | None, optional
        Maximum time the ramping may take. If ramp_rate is None, the sweep will
        be performed in ramp_time. Else, it provides an upper limit to the ramp
        time.
    setpoint_intervall : float, optional
        Stepsize of the sweep. The smaller, the smoother the sweep will be
        Very small steps can increase the sweeptime significantly.
        The default is 0.1.
    valid_units : str, optional
        Not used yet. The default is "all".
    tolerance: float, optional
        If abs(current_value- target_value) < tolerance*max(current_value, target_value)
        no ramp is done. Default 1e-5.
    **kwargs : TYPE
        DESCRIPTION.

    Raises
    ------
    Unsweepable_parameter
        Raised when the parameter has non-float values and cannot be swepted.

    Returns
    -------
    BOOL
        True if sweep was completed, False if it failed.

    """
    if parameter._settable is False:
        LOG.warning(f"{parameter} is not _settable and cannot be ramped!")
        return False
    current_value = parameter.get()
    LOG.debug(f"parameter: {parameter}")
    LOG.debug(f"current value: {current_value}")
    LOG.debug(f"ramp rate: {ramp_rate}")
    LOG.debug(f"ramp time: {ramp_time}")

    if isinstance(current_value, float):
        LOG.debug(f"target: {target}")
        if isclose(current_value, target, rel_tol=tolerance):
            LOG.debug("Target value is sufficiently close to current_value, no need to ramp")
            return True

        if not ramp_rate:
            if not ramp_time:
                print("Please specify either ramp_time or ramp_speed")
                return False
            else:
                ramp_rate = abs(current_value - float(target)) / ramp_time

        num_points = int(abs(current_value - float(target)) / (ramp_rate * setpoint_intervall)) + 2
        if ramp_time is not None and ramp_time < abs(current_value - float(target)) / ramp_rate:
            print(
                f"Ramp rate of {param} is to low to reach target value in specified"
                "max ramp time. Adapting ramp rate to match ramp time"
            )
            return ramp_parameter(
                parameter=parameter,
                target=target,
                ramp_rate=None,
                ramp_time=ramp_time,
                setpoint_intervall=setpoint_intervall,
                valid_units=valid_units,
                **kwargs,
            )
        sweep = generate_sweep(parameter.get(), target, num_points)
        LOG.debug(f"sweep: {sweep}")
        for value in sweep:
            parameter.set(value)
            time.sleep(setpoint_intervall)
        return True
    else:
        raise Unsweepable_parameter("Parameter has non-float values")
    return False


def ramp_or_set_parameter(
    parameter,
    target,
    ramp_rate: float | None = 0.1,
    ramp_time: float | None = 10,
    setpoint_intervall: float = 0.1,
    **kwargs,
):
    """
    Trys to ramp parameter to specified value, if the parameter values are not
    float, they are just set.
    """
    try:
        ramp_parameter(parameter, target, ramp_rate, ramp_time, setpoint_intervall)
    except Unsweepable_parameter:
        parameter.set(target)
