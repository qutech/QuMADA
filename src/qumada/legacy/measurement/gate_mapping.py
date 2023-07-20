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


import json  # Used to store mappings until DB is functional
import re

from qumada.utils import browsefiles
from qumada.measurement import get_from_station as gfs
import qumada.utils.load_save_config as lsc


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
            self.get_method(station)
            # self.wrap = mapping(station, **kwargs)

        def get_method(self, station):
            """
            User input to decide whether a mapping should be loaded from file
            or a new one should be created. DB support to be added
            """
            method = input("Do you want to load an existing mapping? (y/n)\n")
            if method.lower() == "y":
                return self.load_mapping(station)
            elif method.lower() == "n":
                return self.create_mapping(station)  # Create new mapping
            else:
                print("Please enter y or n")
                return self.get_method()

        def create_mapping(self, station):
            """
            Create a new GateMapping with user input
            """
            self.wrap = mapping(station)
            try:
                gate_number = int(input("Please enter number of gates:\n"))
            except ValueError:
                print("Please enter an integer number")
                self.create_mapping()
            for i in range(0, gate_number):
                self.wrap.add_gate()

        def load_mapping(self, station):
            """
            Used to load a mapping from file (DB support to be added)
            Loading from json files works now, however, a new station object has
            to be passed as the original one cannot be saved to a json file.
            Should work as long as both station objects contain the same
            instruments.
            ToDo: Check whether old and new station object are compatible
            """
            filename = browsefiles.browsefiles(
                filetypes=(("json", ".json"), ("All files", "*.*")),
                initialdir=lsc.load_from_config("gate_mapping", "save_directory"),
            )
            # Save last directory used in config so you dont have to search for it.
            directory = "/".join(filename.split("/")[0:-1])
            lsc.save_to_config("gate_mapping", "save_directory", directory)
            try:
                with open(filename) as read_file:
                    loaded_mapping = json.load(read_file)
            except OSError:
                # TODO: Handle File error
                print("An OS error occured. Please check, whether you chose a valid file")
            loaded_mapping["station"] = station
            self.wrap = mapping(**loaded_mapping)

    return MapGenerator


@create_or_load_mapping
class GateMapping:
    """
    Mapping of "physical" sample gates to device channels.
    Requires qcodes station object as input
    Requires user input.
    To Do:
        - Version without user input
        - Measurement device types
        - Think about dictionary structure
        - Does not fit to our new concept of "Functionalities"- Probably direct
        interaction with station object does not belong here anymore.
    """

    def __init__(self, station, **kwargs):
        self.station = station
        self.gate_number = kwargs.get("gate_number", 0)
        self.gates = kwargs.get(
            "gates", {}
        )  # Mapping gate name <=> list with device channels: [0]=voltage, [1]=current
        self.gate_types = kwargs.get("gate_types", self._load_gate_types())
        # self.add_gates()

    def _load_gate_types(self, file="./gate_types.dat"):
        """
        Loads list of valid gate types from file.
        Will open gui for choosing file if the entered one is not valid.
        Todo: - Allow for user input/saving
        """
        types = set()
        try:
            f = open(file)
        except OSError:
            print("Could not find file with gate types", file)
            print("Please select file")
            file = browsefiles.browsefiles(filetypes=(("dat", ".dat"), ("txt", ".txt"), ("All files", "*.*")))
            return self._load_gate_types(file=file)

        for line in f:
            if line[0] != "#":
                types.add(line.rstrip("\n"))
        f.close()
        return types

    def remove_gate(self, gate=None):
        """
        Allows user to delete gates.
        ToDo: Show list of available entries
        """
        if gate is None:
            gate = input("Enter name of gate you want to delete:\n")
        try:
            del self.gates[gate]
        except KeyError:
            print("This gate does not exist")

    def add_gate(self):
        """
        Method that should be used for adding gates to the mapping. Requires
        user input.
        """
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
        """
        Add current channel to gate entry
        """
        string = "Please select a channel to apply and measure currents for this gate.\n"
        string += 'You can skip this by typing "exit"'
        current_channel = gfs.select_channel(self.station, information=string)
        return current_channel

    def _add_volt(self):
        """
        Add volt channel to gate entry
        """
        string = "Please select a channel to apply and measure voltages for this gate.\n"
        volt_channel = gfs.select_channel(self.station, information=string)
        return volt_channel

    def _gate_type_validator(self, gate_types, gate_type=None):
        """
        Checks whether chosen gate type is valid. Necessary to rely on gate_type
        variable in the measurement script.
        """
        print("Valid gate types are:\n %s" % gate_types)
        if gate_type in gate_types:
            return gate_type
        elif gate_type is None:
            gate_type = input("Please enter gate type:\n")
            return self._gate_type_validator(gate_types, gate_type)
        else:
            print("Invalid gate type. Known gate types are\n%s" % gate_types)
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
        dictionary["gate_types"] = list(dictionary["gate_types"])
        text = json.dumps(dictionary)
        file = browsefiles.browsesavefile(
            filetypes=(("Json", "*.json*"), ("All files", "*.*")),
            initialdir=lsc.load_from_config("gate_mapping", "save_directory"),
        )
        directory = "/".join(file.strip("/")[0:-1])
        lsc.save_to_config("gate_mapping", "save_directory", directory)
        file.write(text)
        file.close()
