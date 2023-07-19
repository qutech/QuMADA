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


import configparser


def load_from_config(section, key, config_file="../config.cfg"):
    """
    Helps you to load settings from the config file.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    if section in config and key in config[section]:
        return config[section][key]
    print(f"No such entry in config: {section} {key}")
    return None


def save_to_config(section, key, value, config_file="../config.cfg"):
    """
    Stores settings in config file for you
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    if section not in config:
        config[section] = {}
    config[section][key] = value
    with open(config_file, "w") as configfile:
        config.write(configfile)
    return None
