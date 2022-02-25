"""
Created on Mon May 31 17:33:53 2021

@author: till3
"""

import configparser



def load_from_config(section, key, config_file = "../config.cfg"):
    """
    Helps you to load settings from the config file.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    if section in config:
        if key in config[section]:
            return config[section][key]
    print("No such entry in config:\n %s \n %s" %(section,key))
    return None

def save_to_config(section, key, value, config_file = "../config.cfg"):
    """
    Stores settings in config file for you
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    if not section in config:
        config[section] = {}
    config[section][key] = value
    with open(config_file, "w") as configfile:
        config.write(configfile)
    return None
