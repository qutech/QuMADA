#%%
import numpy as np
from qupulse.pulses import AbstractPT, FunctionPT, AtomicMultiChannelPT, PointPT
from qupulse.pulses.plotting import plot, render


test = FunctionPT('exp(-t/tau)*sin(phi*t)+offset', "duration")
#%%
def get_pulse_setpoints(pulse, parameters, sampling_rate= 10):
    channels = pulse.defined_channels
    program = pulse.create_program(parameters=parameters,
                                    channel_mapping={ch: ch for ch in channels},
                                    measurement_mapping={w: w for w in pulse.measurement_names})
    times, voltages, measurements = render(program,
                                               sampling_rate,
                                               render_measurements=False,
                                               )
    return times, voltages["default"]
# %%
