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


def get_station_instr(station):
    """
    Lists all instruments listed in a qcodes station config yaml.
    Can be used to create instances of instruments after loading the station.
    """
    return [elem.strip("load_") for elem in station.__dict__["_added_methods"]]


def instance_instr(station):
    """
    Creates instances of all instruments listed in qcodes stations qconfig yaml
    and puts them into a list. Not the most elegant way but might be handy for
    automation...
    """
    return [station.load_instrument(elem) for elem in get_station_instr(station)]
