# Copyright (c) 2023 JARA Institute for Quantum Information
#
# This file is part of QuMADA.
#
# QuMADA is free software: you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# QuMADA is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with QuMADA. If not, see <https://www.gnu.org/licenses/>.
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
from copy import deepcopy

LOG = logging.getLogger(__name__)

def has_ramp_method(parameter):
    try:
        parameter.root_instrument._qumada_ramp
        return True
    except AttributeError:
        return False

def has_pulse_method(parameter):
    try:
        parameter.root_instrument._qumada_pulse
        return True
    except AttributeError:
        return False
    
def has_force_trigger_method(parameter):
    try:
        parameter.root_instrument._qumada_mapping.force_trigger
        return True
    except AttributeError:
        return False

class Unsweepable_parameter(Exception):
    pass

class Unsettable_parameter(Exception):
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
        raise Unsettable_parameter()
    current_value = parameter.get()
    LOG.debug(f"parameter: {parameter}")
    LOG.debug(f"current value: {current_value}")
    LOG.debug(f"ramp rate: {ramp_rate}")
    LOG.debug(f"ramp time: {ramp_time}")

    if isinstance(current_value, float|int) and not isinstance(current_value, bool):
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

        num_points = int(abs(current_value - float(target)) / (setpoint_intervall)) + 2
        if ramp_time is not None and ramp_time < abs(current_value - float(target)) / ramp_rate:
            LOG.info(
                f"Ramp rate of {parameter} is to low to reach target value in specified"
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
            time.sleep(ramp_time/num_points)
        return True
    else:
        raise Unsweepable_parameter("Parameter has non-float values")
    return False


def ramp_or_set_parameter(
    parameter,
    target,
    ramp_rate: float | None = 0.3,
    ramp_time: float | None = 5,
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
    except Unsettable_parameter:
        pass
        
def ramp_or_set_parameters(
        parameters: list,
        targets: list[float],
        ramp_rate: float | list[float] = 0.3,
        ramp_time: float | list[float] = 5,
        setpoint_interval: float |list[float] = 0.1,
        tolerance: float = 1e-5,
        trigger_start = None,
        trigger_type = "software",
        trigger_reset = None,
        sync_trigger = None):
    instruments = {param.root_instrument for param in parameters}
    instruments_dict = {} #Will contain instruments as keys and their params with targets as vals.
    #Check requirements for parallel ramps.
    if trigger_type is not None:
        for instr in instruments:
            if has_ramp_method(instr) and has_force_trigger_method(instr) and hasattr(instr._qumada_mapping, "max_ramp_channels"):
                instruments_dict[instr] = [] #Only instruments supporting ramps are added!
    # Loop groups params according to their instruments for later execution of ramps.
    for param, target in zip(parameters, targets):
        if param._settable is False:
            LOG.warning(f"{param} is not _settable and cannot be ramped!")
            continue
        
        current_value = param.get() 
        #TODO: Possibly further improvements with cached val or known start.
        # Check if parameter should be ramped or set.
        if isinstance(current_value, float|int) and not isinstance(current_value, bool):
            LOG.debug(f"current value: {current_value}, target: {target}")
            if isclose(current_value, target, rel_tol=tolerance):
                LOG.debug("Target value is sufficiently close to current_value, no need to ramp")
                continue
        if param.root_instrument in instruments_dict.keys():  #Only instruments supporting ramps
                instruments_dict[param.root_instrument].append((param,target))
        else: #Everything that cannot be ramped with instrument ramp is ramped/set here
            ramp_or_set_parameter(param, target, ramp_rate, ramp_time, setpoint_interval)
    # Now go through all instruments supporting ramps and start the ramps
    for instr, values in instruments_dict.items():
        counter = 1
        param_helper = []
        target_helper = []
        #Params and targets are added until the max number of simultaneously rampable
        #channels is reached. Then ramp is started and new params are added.
        for param, target in values:
            param_helper.append(param)
            target_helper.append(target)
            #TODO: Triggering logic won't work if sync trigger is used to trigger another
            # DAC (e.g. QDac in combination with Decadac)
            if counter%instr._qumada_mapping.max_ramp_channels == 0 or counter == len(values):
                LOG.debug(f"Ramping {param_helper} to {target_helper}")            
                if sync_trigger is not None:
                    LOG.exception("You are using a sync trigger for ramps outside measurements. \
                                  If the sync trigger is required to start an another DACs/AWGs ramp \
                                  this will not work. (E.g. QDac and Decadac). If you only need it to \
                                  start data acquisitions you're fine.")
                instr._qumada_ramp(
                    param_helper,
                    end_values = target_helper,
                    ramp_time = min(ramp_time, 1/ramp_rate), #TODO: Is that fine/Safe enough?
                    sync_trigger=None
                    )
                instr._qumada_mapping.force_trigger()
                #TODO: Force trigger for AWGs/DACs?
                time.sleep(ramp_time)
                try:
                    trigger_reset()
                except TypeError:
                    LOG.info("No method to reset the trigger defined.")
                param_helper = []
                target_helper = []
            counter +=1

                    
                    
                
        
    
    
