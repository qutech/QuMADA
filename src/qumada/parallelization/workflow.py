import copy
import threading
from dataclasses import dataclass
from collections.abc import Iterable, Mapping, MutableMapping
from time import sleep

from qcodes.station import Station
from qumada.measurement.measurement import  MeasurementScript


@dataclass 
class Device:
    #can eliminate this class and directly use index if no further information is needed
    index: list # multmiindex of the device. Must be compatible with the deviceMapping of the WorkflowConfiguration to be used.

@dataclass
class Workflow:
    """Container class representing a single workflow. A workflow is 
    a measurement or series of measurements to be executed on a device."""
    measurement: MeasurementScript # could be more general (function with args, which need to contain mapping)
    #args: tuple
    #kwargs: dict
    #device: Device = None# only set once configured. Derive new class?
    # dict instead of class enough for now    
    device_index: list = None #generalize to iterable?


class WorkflowConfiguration: # turn into dataclass?
    """Class to define and execute a set of workflows."""
    workflows: list # configured workflows
    device_mapping: Mapping #nested mapping of the chip. Morge general type, e.g. iterable, MutableMapping? Must be indexable.
    #The lowest level contains the chip pad indices, which must serve as top level index of the stup mapping
    setup_mapping: dict #Mapping of the setup (same for all workflows). List of indexable maps to be applied consecutively. 
    #The entries of the (n)th map must serve as index to the (n+1)th.
    station: Station # QCoDeS station
  
    def __init__(self, station, setup_mapping:dict = None, device_mapping:dict = None):
        self.station = station
        self.device_mapping = device_mapping
        self.setup_mapping = setup_mapping  
        self.workflows = []   
    # It is likely useful to allow for flow configurations without some of these being defined, 
    # e.g. to be setup agnostic
    # Metadata to be added (waver, batch etc.)
  
    def add_single_workflow(self, wf:Workflow, device):
        """ add a single workflow wf. Device is an index list 
        identifying the device via the previously configured deviceMapping. """
        wf = copy.copy(wf)
        wf.device_index = device 
        self.workflows.append(wf)

    def add_identical_workflows(self, base_workflow:Workflow, devices:list):
        """ Configure the same workflow to be executed for several different devices.
        Each element of devices will generate one workflow for the indicated device. """
        # entries of devices must fully specify a device. It should correspond to the metadata at least 
        # by convention and allow for resolution of the device map.
    
    
        # can likely generalize type of devices.
        for dev in devices:
            wf = copy.copy(base_workflow) # shallow copy should be sufficient as only device will be changed and     
            wf.device_index = dev
            self.workflows.append(wf) 
     
    
    def run(self):
        """Execute configured workflows"""    
        # TODO: set common global parameters (such as magnetic field, temperature)
        # Per convention (?), any parameter is either global or local to at most one workflow.
    
        # execute all configured workflows in a separate thread  
        threads = []
        for wf in self.workflows:
            # Resolve indices to create a complete mapping that can be passed to measurement function.
            # This involves flattening the mapping to the qumada mapping format 
            # of dictionary with one or no nesting level.
            #   - substitute device indices.
            #   - Evaluate concatenated setup Map.
            
            # Apply nested device map to obtain map from device terminals as 
            # refered to in measurement to chip pins.
            terminal_map = self.device_mapping
            for index in wf.device_index:
                terminal_map = terminal_map[index]
            
            mapping = {} # mapping dict to map device terminals to hardware channels.
            # generated from terminalMap and setupMapping in the following 
       
            # Adapted from instruments/mapping/base.py, load_mapped_terminal_parameters
            # Assertions present in load_mapped_gate_parameters dropped in the following.
            for terminal_name, terminal_or_parameter in terminal_map.items():
                if not isinstance(terminal_or_parameter, MutableMapping):
                    # Single parameter, get component by full name
                    index = terminal_or_parameter #should equal terminalMap[terminalName]
                    # iterate on terminalsOrParameter directly?
                    
                    # Concatenate setupMaps
                    for map in self.setup_mapping:
                        index = map[index]
                    
                    #mapping[terminalName] = index # add entry do dict
                    # last map is expected to point to valid parameter names contained in the station.
                    # Translate from multi index such as instrument, channel?                        

                    #try:
                    mapping[terminal_name] = self.station.get_component(index)
                    #except KeyError: # see mapping/base.py for logger setup.
                    #    logger.warning("Parameter could not be loaded: QCoDeS station does not contain parameter %s", index)
                
                else: # terminalOrParameter is a terminal with potentially several associated parameters
                    resolved_terminal_map = {} # map from terminal parameters to chip indices.
                    for parameter_name, parameter in terminal_or_parameter.items():
                        index = parameter
                        for map in self.setupMapping:
                            index = map[index]
                        resolved_terminal_map[parameter_name] = self.station.get_component(index)
                    mapping[terminal_name] = resolved_terminal_map
                        
            #wf.Measurement.gate_parameters = mapping  # does not match quamada convention
            # Complete mapping, assuming gates are mappted to components and the parameter 
            # name is the same, given in gate_parameters of the MeasurementScript.
            # Likely useful extension: Provide explicit translation. May depend on component.  
            for (gate, parameters) in wf.measurement.gate_parameters.items():
                for parameter_name in parameters.keys():
                    wf.measurement.gate_parameters[gate][parameter_name] = \
                        self.station.get_component(mapping[gate].full_name + "_" + parameter_name)
            
            threads.append(threading.Thread(target = wf.measurement.run)) #, args = wf.args, kwargs = wf.kwargs))
            # No need to make threads daemonic as they should all finish first (or use this to kill threads? Only if safe.)             

        for thread in threads:
            thread.start()
            sleep(.2)
            #thread.join() # test        
        # Wait for threads to finish. 
        for thread in threads:
            thread.join() 
        
        # Note on progress indicator: dond functions use tqdm, which needs to be integrated in a loop.
        # Other quamada scripts (not based on dond and relatives) don't use tqdm. 
        # Several simultaneous outputs work (see examples/progress_bar_playground.py).
        # tqmd can take a position argument and description. Position seems relative to current position.  
        # These would need modification of the acquisition function(s) and providing some name.
        
        # Is data storage thread safe? How are measurements distinguished?
        # Termination signal would be desirable. Event? Would need to be polled by worker functions. 

    #TODO: various convenience functions for inspecting and changing workflows.

