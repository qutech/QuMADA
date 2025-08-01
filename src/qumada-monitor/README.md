# QuMADA Device Monitor

This is a dash app that is intended to monitor a qumada device. To use it you need to install the `monitor` dependencies for example via 
`pip install qumada[monitor]` or with a local editable install `pip install -e .[monitor]`.

The feature that separates it from the qcodes monitor is the ability to display a proper layout.

```python
from qumada.utils.device_server import start_monitor_socket

device: 'QumadaDevice' = ...
my_dxf_file = ...

start_monitor_socket(device, my_dxf_file)
```

This does the following steps under the hood:

1. Create a list of `qumada.utils.geometry.Gate` objects with the correct labels
    - Load a dxf file with `doc = ezdxf.readfile('my_layout.dxf')`
    - Crop it to the desired region with `raw_gates = qumada.utils.dxf.get_gates_from_cropped_region`
    - Merge gates from the same layer that overlap (necessary for some reason) with `merged_gates = qumada.utils.dxf.auto_merge`
    - Give the gates the proper labels with a helper GUI: `gates = qumada.utils.dxf.label_gates(merged_gates)`
    - Save the gate list to json with `qumada.utils.geometry.store_to_file(gates, 'my_gates.json')`
2. Start the device monitor server and set its gate_geometry

To view the monitor you need to start the webserver by running `python -m qumada-monitor` in a shell

The webserver will try to match parameters to gates based on the gate labels being present in the parameter labels.
Un-matched gates are nan.
