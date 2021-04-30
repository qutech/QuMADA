# -*- coding: utf-8 -*-
"""
Created on Thu Dec 17 18:38:47 2020

@author: Huckemann
"""
import json     # Used to store mappings until DB is functional

from qtools.utils import browsefiles
from qtools.measurement import get_from_station as gfs


def create_or_load_mapping(mapping):
    class MapGenerator:
        """
        Decorator used to separate the GateMapping class from the stuff that is
        needed to create/load it. Keep in mind, that it will return the
        MapGenerator object, to access the GateMapping() object,
        usage of .wrap is required (ToDo: Change this)
        """
        def __init__(self, station, **kwargs):
            # Get access to GateMapping methods
            self.wrap = mapping(station, **kwargs)
            self.get_method()

        def get_method(self):
            """
            User input to decide whether a mapping should be loaded from file
            or a new one should be created. DB support to be added
            """
            method = input("Do you want to load an existing mapping? (y/n)\n")
            if method.lower() == "y":
                pass    # add function for loading here
            elif method.lower() == "n":
                return self.create_mapping()    # Create new mapping
            else:
                print("Please enter y or n")
                return self.get_method()

        def create_mapping(self):
            """
            Create a new GateMapping with user input
            """
            try:
                gate_number = int(input("Please enter number of gates: \n"))
            except ValueError:
                print("Please enter an integer number")
                self.create_mapping()
            for i in range(0, gate_number):
                self.wrap.add_gate()

        def load_mapping(self):
            """
            Used to load a mapping from file (DB support to be added)
            Not functional yet, have to find a way to store/restore Qcodes
            objects like Instruments/Stations beforehand
            """
            filename = browsefiles.browsefiles(filetypes=(("json", ".json"),
                                                          ("All files", "*.*")))
            try:
                f = open(filename, "r")
            except OSError:
                # TODO: Handle File error
                pass
            f.close()
            return None

    return MapGenerator


@create_or_load_mapping
class GateMapping():
    '''
    Mapping of "physical" sample gates to device channels.
    Requires qcodes station object as input
    Requires user input.
    To Do:
        - Version without user input
        - Loading/Saving
        - Measurement device types
        - Think about dictionary structure
    '''
    def __init__(self, station, **kwargs):
        self.station = station
        self.gate_number = kwargs.get('gate_number', 0)
        self.gates = {}     # Mapping gate name <=> list with device channels: [0]=voltage, [1]=current
        self.gate_types = self._load_gate_types()
        # self.add_gates()

    def _load_gate_types(self, file="./gate_types.dat"):
        '''
        Loads list of valid gate types from file.
        Will open gui for choosing file if the entered one is not valid.
        Todo: - Allow for user input/saving
        '''
        types = set()
        try:
            f = open(file, 'r')
        except OSError:
            print("Could not find file with gate types", file)
            print("Please select file")
            file = browsefiles.browsefiles(filetypes=(("dat", ".dat"),
                                                      ("txt", ".txt"),
                                                      ("All files", "*.*")))
            return self._load_gate_types(file=file)

        for line in f:
            if line[0] != "#":
                types.add(line.rstrip('\n'))
        f.close()
        return types

    def remove_gate(self, gate=None):
        '''
        Allows user to delete gates.
        ToDo: Show list of available entries
        '''
        if gate is None:
            gate = input("Enter name of gate you want to delete: \n")
        try:
            del self.gates[gate]
        except KeyError:
            print("This gate does not exist")

    def add_gate(self):
        '''
        Method that should be used for adding gates to the mapping. Requires
        user input.
        '''
        key = input("Please enter gate name: ")
        gate_type = self._gate_type_validator(self.gate_types)
        volt_channel = self._add_volt()
        current_channel = self._add_current()
        self.gates[key] = {}
        self.gates[key]["gate_type"] = gate_type
        self.gates[key]["volt"] = volt_channel
        self.gates[key]["current"] = current_channel
        self.gate_number += 1

    def _add_current(self):
        '''
        Add current channel to gate entry
        '''
        string = "Please select a channel to apply and measure currents for this gate.\n"
        string += 'You can skip this by typing "exit"'
        current_channel = gfs.select_channel(self.station, information=string)
        return current_channel

    def _add_volt(self):
        '''
        Add volt channel to gate entry
        '''
        string = "Please select a channel to apply and measure voltages for this gate.\n"
        volt_channel = gfs.select_channel(self.station, information=string)
        return volt_channel

    def _gate_type_validator(self, gate_types, gate_type=None):
        '''
        Checks whether chosen gate type is valid. Necessary to rely on gate_type
        variable in the measurement script.
        '''
        print("Valid gate types are: \n" + str(gate_types))
        if gate_type in gate_types:
            return gate_type
        elif gate_type is None:
            gate_type = input("Please enter gate type: \n")
            return self._gate_type_validator(gate_types, gate_type)
        else:
            print("Invalid gate type. Known gate types are \n" + str(gate_types))
            print("You can use 'other' for unspecified gates. Support for adding new types will be added later")
            return self._gate_type_validator(gate_types)

    def save_to_file(self):
        """
        Used to store mapping in json file
        Not functional yet, have to find a way to store/restore Qcodes
        objects like Instruments/Stations beforehand
        Could be done via YAML config, check qcodes doc
        """
        dictionary = self.__dict__
        dictionary["station"] = None
        text = json.dumps(dictionary)
        file = browsefiles.browsesavefile(filetypes=("Json", ".json"))
        file.write(text)
        file.close()
