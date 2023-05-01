Mapping GUI
===========

This GUI helps you to map the QuMADA Terminals (shown on left side) to the respective instrument parameters (shown on right side).

You can drag a terminal or one of its parameters (children in tree) to an instrument/channel/parameter. You can also select a terminal/terminal parameter and press the enter key to start a mapping process. The selection switches to the instrument tree where you can select a respective instrument/channel/parameter. Press enter again to map the respective terminal/terminal parameter to the instrument/channel/parameter.

Trying to map a terminal (containing multiple terminal parameters) to an instrument or channel (containing multiple parameters) will result in mapping of all unique pairs (the instrument parameters have an associated terminal parameter in a respective mapping file, which has to be loaded first with the add_mapping_to_instrument function).

If multiple terminal parameters are mapped to the same instrument paramter the involved terminal parameters are marked in pink.

Monitoring is a feature, which repeatedly calls the **get** command (or optionally the cached value) for the mapped parameters.

The **Reset mapping** button resets all mappings. The **Unfold** button folds all terminals in the tree representation (toggling if pressed repeatedly).

The **Map automatically** button applies a heuristic for mapping the available terminals.
The algorithm used is (almost) equivalent to selecting the first terminal and repeatedly pressing the enter key until the last terminal (in the tree) is mapped.
This works best if the terminals are in the same order as the instruments that they should be mapped to.
Additionally the terminals mapping to channels of an instrument should be ordered the same as the channels (up to the driver but usually something like 0,1,2,...)


.. image:: images/mapping_gui.png
