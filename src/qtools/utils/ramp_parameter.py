# -*- coding: utf-8 -*-
"""
Created on Fri Jan 28 14:42:03 2022

@author: lab
"""

from qtools.utils.generate_sweeps import generate_sweep
import time
import logging

LOG = logging.getLogger(__name__)


class Unsweepable_parameter(Exception):
    pass

def ramp_parameter(
        parameter,
        target,
        ramp_rate : float = 0.1,
        setpoint_intervall: float = 0.1
        ):
    """
    Ramping paramters for instruments without buildin ramp function.
    ramp_speed sets the ramping speed in [value]/s, setpoint intervalls defines
    the delay between to consecutive set_commands (the ramp_speed is independent)
    """
    time.sleep(0.1)
    LOG.debug(f"parameter: {parameter}")
    current_value = parameter.get()
    LOG.debug(f"current value: {current_value}")
    if type(current_value) == float:
        LOG.debug(f"target: {target}")
        num_points = int(abs(current_value-float(target))/(ramp_rate*setpoint_intervall))+2
        sweep = generate_sweep(parameter.get(), target, num_points)
        LOG.debug(f"sweep: {sweep}")
        for value in sweep:
            parameter.set(value)
            time.sleep(setpoint_intervall)
        return True
    else:
        raise Unsweepable_parameter("Parameter has non-float values")



def ramp_or_set_parameter(parameter,
                          target,
                          ramp_rate : float = 0.1,
                          setpoint_intervall: float = 0.1):
    """
    Trys to ramp parameter to specified value, if the parameter values are not
    float, they are just set.
    """
    try:
        ramp_parameter(parameter,
                       target,
                       ramp_rate,
                       setpoint_intervall)
    except Unsweepable_parameter:
        parameter.set(target)
