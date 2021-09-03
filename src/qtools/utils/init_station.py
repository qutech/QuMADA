"""
Created on Tue Feb 23 21:34:38 2021

@author: till3
"""


def get_station_instr(station):
    """
    Lists all instruments listed in a qcodes station config yaml.
    Can be used to create instances of instruments after loading the station.
    """
    result = []
    for elem in station.__dict__['_added_methods']:
        result.append(elem.strip('load_'))
    return result


def instance_instr(station):
    """
    Creates instances of all instruments listed in qcodes stations qconfig yaml
    and puts them into a list. Not the most elegant way but might be handy for
    automation...
    """
    instruments = []
    for elem in get_station_instr(station):
        instruments.append(station.load_instrument(elem))
    return instruments
