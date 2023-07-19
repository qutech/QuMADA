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


from typing import Mapping

from tabulate import tabulate

_FLAG_FIRST = object()


def flatten_dict(d, join=lambda a, b: [a, b], lift=lambda x: x):
    '''
    Flattens nested dictionary
    '''
    results = []

    def visit(subdict, results, partial_key):
        for k, v in subdict.items():
            new_key = lift(k) if partial_key == _FLAG_FIRST else join(partial_key, lift(k))
            if isinstance(v, Mapping):
                visit(v, results, new_key)
            else:
                results.append(new_key)
    visit(d, results, _FLAG_FIRST)
    return results


def _find_instr_channel(key, station, last_entry=None, **kwargs):
    '''

    '''
    if last_entry is None:
        last_entry = []
    dictionary = kwargs.get('dictionary', station.__dict__)
    results = kwargs.get('results', [])
    f_d = flatten_dict(dictionary, join=lambda a, b: [a, b])
    for entry in f_d:
        # Some entries are lists rather than nested dicts. Treat both cases
        # separately
        if isinstance(entry, list):
            for item in entry:
                if str(item).find(key) >= 0:
                    results.append([*last_entry, *entry])
                try:
                    # Test if we have got an object with a .__dict__ function
                    # Need try/except as most entries won't have a .__dict__
                    if _find_instr_channel(dictionary=get_channel(station, entry).__dict__,
                                           key=key,
                                           station=station) != []:
                        # If true, we continue search inside entry.__dict__
                        entry.append('__dict__')
                        # Do not pass **kwargs here as we don't want to double
                        # our results list. We still stay inside the main func.
                        results.append(
                            _find_instr_channel(dictionary=get_channel(station, entry),
                                                key=key,
                                                station=station,
                                                last_entry=[*last_entry, *entry]))
                except Exception:
                    pass
        # Now search the nested dicts
        elif isinstance(entry, dict):
            if str(entry).find(key) >= 0:
                # print('Found something2: ' + str([*last_entry, *entry]))
                results.append([*last_entry, *entry])
    return results


def find_instr_channels(station, key, submodules=True, **kwargs):
    '''
    Creates list with all entries to the station that contain the key and does
    not stop at the first level, where the key is found (e.g. if you look for
    for some module named "key" all submodules of key will be listed as well)
    '''
    if not submodules:
        return flatten_list(_find_instr_channel(key=key, station=station, **kwargs), [])
    else:
        results = flatten_list(_find_instr_channel(dictionary=station.__dict__,
                                                   key=key,
                                                   station=station), [])
        # Now append all the results including subparams
        for entry in results:
            try:
                helper = _find_instr_channel(dictionary=get_channel(station, entry).__dict__,
                                             station=station,
                                             key="")
            except Exception:
                continue
            for result in helper:
                if [*entry, '__dict__', *result] not in results:    # necessary to avoid doubled entries
                    results.append([*entry, '__dict__', *result])
        return results


def flatten_list(mylist, result=None):
    '''
    Flattens nested lists.
    Necessary to flatten output of find_instr_channel to make it
    compatible with get_channel. Note that the result will still be a list of
    lists!
    '''
    if result is None:
        result = []
    for elem in mylist:
        if not isinstance(elem, list):
            if mylist not in result:
                result.append(mylist)
            break
        else:
            flatten_list(elem, result)
    return result


def search_list(ls, key=""):
    '''
    Creates list with only entries containing the key  from a larger list.
    Intended to work with flattened results from find_instr_channels
    '''
    results = []
    keys = key.split(" ")

    def flatten(ls):
        # Flatten list recursively if necessary
        mylist = ""
        for elem in ls:
            if isinstance(elem, str):
                mylist += elem
            else:
                return flatten(elem)
        return mylist
    for elem in ls:
        valid = True
        try:
            for string in keys:
                if flatten(elem).find(string) < 0:
                    valid = False
                    break
            if valid:
                results.append(elem)
        except Exception:
            print("Skipped " + str(elem))
            continue
    return results


def choose_result(results, **kwargs):
    '''
    User can choose result from list, function will return the choice
    '''
    info_text = kwargs.get('info_text', 'Please select index or enter "exit" to abort: ')
    print('There are multiple results in the list:')
    print(tabulate(results, tablefmt="psql", showindex=True))
    valid = False
    while not valid:
        try:
            choice = input(info_text)
            choice = int(choice)
            if choice >= 0 and choice < len(results):
                valid = True
            else:
                print('Please enter an index that corresponds to an entry')
        except Exception:
            if choice.lower() == 'exit':
                return None
            elif choice.lower() == 'again':
                return 'again'
            else:
                print('Please enter a number.')
    return results[choice]


def select_channel(station, **kwargs):
    '''
    Used to search and select a certain channel/parameter from station object.
    Just puts all the other methods in the right order and adds some comments.
    Necessary to start new search with different key.
    '''
    information = kwargs.get('information', "")
    silent = kwargs.get('silent', False)
    if not silent:
        print(information)
    info_text = 'Please select index to proceed, enter "again" to start a new search or "exit" to abort. '
    key = kwargs.get('key', input('Please enter key to seach for or exit to skip:
'))
    if key.lower() == "exit":
        return None
    results = find_instr_channels(station=station, key=key, **kwargs)
    while len(results) >= 50:
        print("More than 50 results.")
        key2 = input('Please enter one or more keywords (separated by blanks) for further specification'
                     ' or "all" to show all entries: ')
        if key2.lower() == "all":
            break
        results = search_list(results, key2)
    result = choose_result(results, info_text=info_text, **kwargs)
    if result == 'again':
        return select_channel(station, **kwargs)
    else:
        return result


def get_channel(station, path):
    '''
    Will return object/component of a qcodes station based on the "path
    provided. The path has to be a list of the keys of station.__dict__ leading
    to the wanted object. As some instruments may have submodules that are a
    subclass/function of the instruments main class (e.g. dac channels), the
    list may contain "__dict__" entries. In this case, the function will try to
    get the channel/object from the .__dict__ of the object specified so far.
    '''
    def level(last_level, item):
        '''
        Subroutine to allow (pseudo-recursion) to go to arbitrary deep levels
        of nested structures.
        '''
        return last_level[item]

    # Define starting point
    last_level = station.__dict__
    # Iterate over all list entries in the path
    for i in range(0, len(path)):
        # Go into __dict__ of the current object if necessary
        if path[i] == '__dict__':
            try:
                last_level = last_level.__dict__
            except Exception:
                print("Error: Could not find "
                      + str(last_level) + ".__dict__.")
        else:
            # Go to next nested level and continue
            last_level = level(last_level, path[i])
    return last_level


def get_by_type(mapping, gate_type):
    '''
    '''
    results = []
    for key in mapping.gates:
        if mapping.gates[key]['gate_type'] == gate_type:
            results.append(key)
    return results
