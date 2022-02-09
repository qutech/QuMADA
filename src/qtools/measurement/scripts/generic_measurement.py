import time
from copy import deepcopy

import qcodes as qc
from qcodes.dataset.experiment_container import load_or_create_experiment
from qcodes.instrument import Parameter
from qcodes.utils.dataset.doNd import LinSweep, do1d, do2d, dond
from qtools.measurement.doNd_enhanced.doNd_enhanced import _interpret_breaks, do1d_parallel

from qtools.measurement.measurement import MeasurementScript


class Generic_1D_Sweep(MeasurementScript):
    def run(self) -> list:
        """
        Perform 1D sweeps for all dynamic parameters
        """
        # self.setup(parameters, metadata)
        self.initialize()
        data = list()
        time.sleep(5)
        i=0
        for sweep in self.dynamic_sweeps:  
            sweep._param.set(sweep.get_setpoints()[0])
            time.sleep(5)
            data.append(
                dond(sweep,
                     *tuple(self.gettable_channels),
                     measurement_name=self.metadata.measurement.name or "measurement",
                     #measurement_name=self.metadata.get('measurement_name', "measurement") +self.dynamic_parameters[i]["gate"],
                     break_condition = _interpret_breaks(self.break_conditions)
                     )
                )
            self.reset()
            i+=1
        return data


class Generic_nD_Sweep(MeasurementScript):
    """
    Perform n-Dimensional sweep with n dynamic parameters.
    """

    def run(self):

        self.initialize()
        for sweep in self.dynamic_sweeps:
            sweep._param.set(sweep.get_setpoints()[0])
        time.sleep(5)
        data = dond(*tuple(self.dynamic_sweeps),
                    *tuple(self.gettable_channels),
                    measurement_name=self.metadata.measurement.name or "measurement",
                    break_condition=_interpret_breaks(self.break_conditions)
                     )
        self.reset()
        return data
    
class Generic_1D_parallel_Sweep(MeasurementScript):
    
    def run(self):
        self.initialize()
        dynamic_params = list()
        for sweep in self.dynamic_sweeps:
            sweep._param.set(sweep.get_setpoints()[0])
            dynamic_params.append(sweep.param)
        time.sleep(5)
            
        
        data = do1d_parallel(*tuple(self.gettable_channels),
                            param_set=dynamic_params,
                            setpoints = self.dynamic_sweeps[0].get_setpoints(),
                            delay = self.dynamic_sweeps[0]._delay,
                            measurement_name=self.metadata.measurement.name or "measurement",
                            break_condition = _interpret_breaks(self.break_conditions)
                            )
        
        return data

