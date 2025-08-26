import argparse
import copy
import logging
import math
import operator
import pathlib
import re
import subprocess
import sys
import warnings
from copy import deepcopy
from typing import Tuple

import ezdxf.document
import matplotlib.widgets
import shapely
from matplotlib import pyplot as plt
from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.plotting import plot_polygon

from qumada.utils.geometry import Gate, load_from_file, store_to_file

SELECT_ALPHA = 0.3

logger = logging.getLogger(__name__)


def entity_to_geom(e):
    """
    Best-effort conversion of an ezdxf entity to a Shapely geometry.
    Extend this to cover more exotic entities as needed.
    """
    if e.dxftype() == "LINE":
        return LineString([e.dxf.start, e.dxf.end])

    if e.dxftype() in {"LWPOLYLINE", "POLYLINE"}:
        if hasattr(e, "get_points"):
            points = e.get_points()
        else:
            points = e.points_in_wcs()
        pts = [tuple(p)[:2] for p in points]  # ignore bulge for now
        closed = bool(e.closed) if hasattr(e, "closed") else pts[0] == pts[-1]
        return Polygon(pts) if closed else LineString(pts)

    raise NotImplementedError(e.dxftype())


def iterate_all_entities(e, path=None):
    if path is None:
        path = []
    if e.dxftype() == "INSERT":
        path.append(e.dxf.name)
        for sub in e.virtual_entities():
            yield from iterate_all_entities(sub, path)
        path.pop()
    else:
        yield e, list(path)


def get_gates_from_cropped_region(
    doc: ezdxf.document.Drawing,
    x_rng: tuple[float, float] = (-3.0, 3.0),
    y_rng: tuple[float, float] = (-1.5, 1.5),
    layer_regex: str = r".*BEAM\_L.",
    grid_size: float = 1e-3,
) -> list[Gate]:
    """Selects all polygons (POLYLINE entities) from the selected region that live in a layer matched by the given
    regular expression. The polygons are cropped to the region and returned as :py:`.Gate` objects.

    :py:attr:`.Gate.label_position` is only assigned to gates that touch the boundary.

    In some cases, continuous gates are returned in multiple pieces. Use :py:`.auto_merge` to merge overlapping gates in the same layer.
    """
    regex = re.compile(layer_regex)

    keep_layer = {layer.dxf.name: bool(regex.search(layer.dxf.name)) for layer in doc.layers}

    xmin, xmax = x_rng
    ymin, ymax = y_rng
    roi_poly = Polygon(box(xmin, ymin, xmax, ymax))

    chosen = []
    for model in doc.modelspace():
        for e, path in iterate_all_entities(model):
            layer = e.dxf.layer
            if not keep_layer[layer]:
                continue

            raw_geom = entity_to_geom(e)
            if raw_geom is None:
                continue

            geom = Polygon(raw_geom).simplify(grid_size)
            geom_roi = geom.intersection(roi_poly)
            if geom_roi == roi_poly:
                continue

            if geom_roi.is_empty:
                continue

            geom_roi = shapely.set_precision(geom_roi, grid_size=grid_size)

            boundary = geom.intersection(roi_poly.boundary)

            if not boundary.is_empty and isinstance(boundary, (LineString, MultiLineString)):
                label_position_point = boundary.line_interpolate_point(0.5, normalized=True)
                label_position = label_position_point.x, label_position_point.y
            else:
                label_position = None

            label = f"G{len(chosen)}"
            if label == "G36":
                pass

            gate = Gate(
                polygon=geom_roi,
                label_position=label_position,
                label=label,
                path=path,
                layer=layer,
            )
            chosen.append(gate)

    return chosen


def _connect_all_touching(gates: list[Gate], grid_size: float) -> list[Gate]:
    """Iteratively connects all touching gates "or"-ing their label positions."""
    assert len({gate.layer for gate in gates}) == 1

    result = []
    not_intersecting = []
    intersecting = []
    for gate in gates:
        not_intersecting.clear()
        intersecting.clear()
        for other in result:
            # boundary = gate.polygon.intersection(other.polygon, grid_size=grid_size)
            if gate.polygon.intersects(other.polygon):
                intersecting.append(other)
            else:
                not_intersecting.append(other)
        result.clear()

        if intersecting:
            intersecting.append(gate)
            label_position = None
            for g in intersecting:
                label_position = label_position or g.label_position
            new_poly = shapely.union_all([g.polygon for g in intersecting], grid_size=grid_size)
            to_append = intersecting[0]
            to_append.polygon = new_poly
            to_append.label_position = label_position

            result.append(to_append)
        else:
            result.append(copy.copy(gate))

        result.extend(not_intersecting)
    return result


def auto_merge(gates: list[Gate], grid_size: float = 1e-3):
    """Merges touching gates in the same layer"""

    by_layer = {}
    for gate in gates:
        by_layer.setdefault(gate.layer, []).append(gate)

    for layer, layer_gates in by_layer.items():
        connected = _connect_all_touching(layer_gates, grid_size)
        by_layer[layer] = connected

    result = sum(by_layer.values(), start=[])
    return result


def label_gates(gates: list[Gate]) -> list[Gate]:
    gates = [copy.deepcopy(gate) for gate in gates]

    gates = sorted(gates, key=lambda gate: 0.0 if gate.label_position is None else math.atan2(*gate.label_position))

    axd = plt.figure(layout="constrained").subplot_mosaic(
        """
        AAAA
        BCDE
        """,
        height_ratios=[1, 0.1],
    )
    ax = axd["A"]
    fig = ax.get_figure()
    prv = matplotlib.widgets.Button(ax=axd["B"], label="Previous")
    txt = matplotlib.widgets.TextBox(ax=axd["C"], label="Name")
    apply = matplotlib.widgets.Button(ax=axd["D"], label="Apply")
    nxt = matplotlib.widgets.Button(ax=axd["E"], label="Next")

    layers = {gate.layer for gate in gates}
    color_iter = iter(plt.rcParams["axes.prop_cycle"].by_key()["color"])
    layer_colors = dict(zip(layers, color_iter))

    plots = []
    for idx, gate in enumerate(gates):
        color = layer_colors[gate.layer]
        poly_patch = plot_polygon(gate.polygon, facecolor="none", color=color, add_points=False, ax=ax)

        poly_patch.gate_index = idx
        poly_patch.set_picker(True)

        label_plot = ax.annotate(
            str(gate.label), gate.label_position, bbox=dict(boxstyle="round", fc="0.8"), ha="center", va="center"
        )
        plots.append((poly_patch, label_plot))

    def deselect_gate(idx):
        poly_plot, label_plot = plots[idx]
        poly_plot.set_facecolor("none")
        txt.set_val("")
        plt.draw()

    def select_gate(idx):
        poly_plot, label_plot = plots[idx]
        gate = gates[idx]
        color = layer_colors[gate.layer]
        poly_plot.set_facecolor((color, SELECT_ALPHA))
        if str(gate.label) != str(None):
            txt.set_val(str(gate.label))
        plt.draw()

    current_gate = 0
    select_gate(current_gate)

    def apply_action(*_):
        gate = gates[current_gate]
        _, label_plot = plots[current_gate]
        gate.label = txt.text
        label_plot.set_text(txt.text)
        plt.draw()

    def prev_action(*_):
        nonlocal current_gate
        deselect_gate(current_gate)
        if current_gate == 0:
            current_gate += len(gates)
        current_gate -= 1
        select_gate(current_gate)

    def next_action(*_):
        nonlocal current_gate
        deselect_gate(current_gate)
        current_gate += 1
        if current_gate == len(gates):
            current_gate -= len(gates)
        select_gate(current_gate)

    def pick_handler(event):
        nonlocal current_gate
        artist = event.artist
        if hasattr(artist, "gate_index"):
            gate_index = artist.gate_index
            if gate_index != current_gate:
                deselect_gate(current_gate)
                current_gate = gate_index
                select_gate(current_gate)
        else:
            raise NotImplementedError(event)

    prv.on_clicked(prev_action)
    apply.on_clicked(apply_action)
    nxt.on_clicked(next_action)
    fig.canvas.mpl_connect("pick_event", pick_handler)

    widgets = [prv, apply, nxt, txt]
    fig.widgets = widgets

    return gates


def load_convert_and_cache(path: pathlib.Path | str) -> list[Gate]:
    path = pathlib.Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix == ".dxf":
        dxf_path = path
        json_path = path.with_suffix(".json")

        if not json_path.exists():
            try:
                _ = subprocess.run([sys.executable, "-m", "qumada.utils.dxf", dxf_path], check=True, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as err:
                err_msg = err.stderr.decode(errors='replace')
                print("File conversion failed:\n", err_msg, file=sys.stderr)
                raise

    elif path.suffix == ".json":
        json_path = path

    else:
        raise ValueError("Only dxf and json are supported", path)

    return load_from_file(json_path)


def get_parser():
    import argparse

    parser = argparse.ArgumentParser(description="Qumada dxf labeler")
    parser.add_argument("dxf_path", type=pathlib.Path, help="path to dxf file")
    parser.add_argument(
        "--json-path",
        type=pathlib.Path,
        help="path to json file. default is the same as dxf with other ending",
        default=None,
    )
    return parser


if __name__ == "__main__":
    matplotlib.use("Qt5Agg")
    parser = get_parser()
    args = parser.parse_args()
    if args.json_path is None:
        args.json_path = args.dxf_path.with_suffix(".json")

    doc = ezdxf.readfile(args.dxf_path)
    raw_gates = get_gates_from_cropped_region(doc)
    merged_gates = auto_merge(raw_gates)
    resulting_gates = label_gates(merged_gates)
    plt.show(block=True)
    store_to_file(resulting_gates, args.json_path)
