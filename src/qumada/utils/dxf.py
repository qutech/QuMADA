import argparse
import copy
import itertools
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
import numpy as np

import shapely.affinity
from matplotlib import pyplot as plt
from shapely.geometry import LineString, MultiLineString, Polygon, box
from shapely.plotting import plot_polygon

from qumada.utils.geometry import Gate, load_from_file, store_to_file

SELECT_ALPHA = 0.3
DEFAULT_X_RNG = (-3.0, 3.0)
DEFAULT_Y_RNG = (-1.5, 1.5)
DEFAULT_LAYER_REGEX = r".*BEAM\_L."
DEFAULT_GRID_SIZE = 1e-3

logger = logging.getLogger(__name__)


def entity_to_geom(e):
    """
    Best-effort conversion of an ezdxf entity to a Shapely geometry.
    Extend this to cover more exotic entities as needed.
    """
    if e.dxftype() == "LINE":
        return LineString([e.dxf.start, e.dxf.end])

    if e.dxftype() == "LWPOLYLINE":
        vertices = [(x, y)
                    for x, y, *_ in e.vertices_in_wcs()]
        closed = bool(e.closed) if hasattr(e, "closed") else vertices[0] == vertices[-1]
        if closed:
            return Polygon(vertices)
        else:
            return LineString(vertices)

    if e.dxftype() == "POLYLINE":
        points = [
            (x, y)
            for x, y, *_ in e.points_in_wcs()
        ]
        closed = bool(e.closed) if hasattr(e, "closed") else points[0] == points[-1]
        if closed:
            return Polygon(points)
        else:
            return LineString(points)

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


def _get_all_entity_bounding_box(doc: ezdxf.document.Drawing) -> tuple[float, float, float, float] | None:
    minx = miny = maxx = maxy = float('nan')

    for model in doc.modelspace():
        for e, _ in iterate_all_entities(model):
            e_minx, e_miny, e_maxx, e_maxy = entity_to_geom(e).bounds
            minx = min(e_minx, minx)
            miny = min(e_miny, miny)
            maxx = max(e_maxx, maxx)
            maxy = max(e_maxy, maxy)

    if math.isnan(minx):
        return None

    return minx, miny, maxx, maxy


def _auto_cropping_box(doc: ezdxf.document.Drawing,
                       keep_layer: dict[str, bool],
                       feature_size: float,
                       max_cropping_box_size: float,
                       grid_size: float,
                       ) -> tuple[float, float, float, float] | None:
    edge_set = []

    for model in doc.modelspace():
        for e, _ in iterate_all_entities(model):
            if not keep_layer[e.dxf.layer]:
                continue

            raw_geom = entity_to_geom(e)
            if raw_geom is None:
                continue
            geom = Polygon(raw_geom).simplify(grid_size)

            points = np.array(geom.boundary.xy).T.tolist()

            if not points:
                continue

            points.append(points[0])
            for (x0, y0), (x1, y1) in itertools.pairwise(points):
                if x0 == x1 and x1 == y1:
                    continue

                if (x0 - x1)**2 + (y0 - y1)**2 <= feature_size**2:
                    edge_set.append(
                        [
                            [x0, y0],
                            [x1, y1]
                        ]
                    )
    if not edge_set:
        return None

    edge_set = np.array(edge_set)

    edge_center = np.mean(edge_set, axis=(0, 1))
    logger.debug("edge_center: %r", edge_center)
    edge_distance = np.min(np.linalg.norm(edge_set - edge_center, axis=2), axis=1)
    edge_mask = edge_distance <= max_cropping_box_size * 5
    included_edges = edge_set[edge_mask]

    minx, miny = np.min(included_edges, axis=(0, 1)).tolist()
    maxx, maxy = np.max(included_edges, axis=(0, 1)).tolist()
    return minx, miny, maxx, maxy


def get_gates_from_cropped_region(
    doc: ezdxf.document.Drawing,
    x_rng: tuple[float, float] = DEFAULT_X_RNG,
    y_rng: tuple[float, float] = DEFAULT_Y_RNG,
    layer_regex: str = DEFAULT_LAYER_REGEX,
    grid_size: float = DEFAULT_GRID_SIZE,
    auto_adjust_cropping: bool = False,
) -> list[Gate]:
    """Selects all polygons (POLYLINE entities) from the selected region that live in a layer matched by the given
    regular expression. The polygons are cropped to the region and returned as :py:`.Gate` objects.

    :py:attr:`.Gate.label_position` is only assigned to gates that touch the boundary.

    In some cases, continuous gates are returned in multiple pieces. Use :py:`.auto_merge` to merge overlapping gates in the same layer.
    """
    regex = re.compile(layer_regex)
    logger.debug("Using regular expression %r for layer selection", layer_regex)

    keep_layer = {layer.dxf.name: bool(regex.search(layer.dxf.name)) for layer in doc.layers}

    xmin, xmax = x_rng
    ymin, ymax = y_rng

    if auto_adjust_cropping:
        feature_size = min(xmax - xmin, ymax - ymin) / 3.
        max_box_size = math.sqrt((xmax - xmin)**2 + (ymax - ymin)**2)
        auto_xmin, auto_ymin, auto_xmax, auto_ymax = _auto_cropping_box(doc,
                                                                        keep_layer=keep_layer,
                                                                        feature_size=feature_size,
                                                                        max_cropping_box_size=max_box_size,
                                                                        grid_size=grid_size,
                                                                        )

        x_center = (auto_xmax + auto_xmin) / 2.0
        y_center = (auto_ymax + auto_ymin) / 2.0
        offset = (x_center, y_center)

        logger.info("Shifting box by %r", offset)

        # shift initial box
        xmin += x_center
        xmax += x_center
        ymin += y_center
        ymax += y_center

    logger.info("Using x cropping range: %r and y cropping range %r", (xmin, xmax), (ymin, ymax))

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
    if not gates:
        return []

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


def load_convert_and_cache(
    path: pathlib.Path | str, expected_number_of_gates: int | range | slice = slice(1, None)
) -> list[Gate]:
    path = pathlib.Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix == ".dxf":
        dxf_path = path
        json_path = path.with_suffix(".json")

        if not json_path.exists():
            try:
                _ = subprocess.run(
                    [sys.executable, "-m", "qumada.utils.dxf", dxf_path], check=True, stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as err:
                err_msg = err.stderr.decode(errors="replace")
                print("File conversion failed:\n", err_msg, file=sys.stderr)
                raise

    elif path.suffix == ".json":
        json_path = path

    else:
        raise ValueError("Only dxf and json are supported", path)

    return load_from_file(json_path)


def get_parser():
    import argparse

    def to_range(s: str):
        try:
            min_s, max_s = s.split(":")
            if not min_s:
                min_s = "-inf"
            if not max_s:
                max_s = "inf"
            return float(min_s), float(max_s)
        except Exception as err:
            raise argparse.ArgumentTypeError(
                "Argument must be a 'min:max' pair of python floats or empty strings separated by a colon."
            ) from err

    def to_slice(s: str):
        try:
            start, stop = s.split(":")
            if start:
                start = int(start)
            else:
                start = None
            if stop:
                stop = int(stop)
            else:
                stop = None
            return slice(start, stop)
        except Exception as err:
            raise argparse.ArgumentTypeError(
                "Argument must be a 'start:stop' pair of python integers or empty strings separated by a colon."
            ) from err

    parser = argparse.ArgumentParser(description="Qumada dxf labeler")
    parser.add_argument("dxf_path", type=pathlib.Path, help="path to dxf file")
    parser.add_argument(
        "--json-path",
        type=pathlib.Path,
        help="path to json file. default is the same as dxf with other ending",
        default=None,
    )
    parser.add_argument(
        "--x-rng",
        help="The gates are cropped to this range in x coordinates",
        type=to_range,
        metavar="[X_MIN={}]:[X_MAX={}]".format(*DEFAULT_X_RNG),
        default=":".join(map(str, DEFAULT_X_RNG)),
    )
    parser.add_argument(
        "--y-rng",
        help="The gates are cropped to this range in y coordinates",
        type=to_range,
        metavar="[Y_MIN={}]:[Y_MAX={}]".format(*DEFAULT_Y_RNG),
        default=":".join(map(str, DEFAULT_Y_RNG)),
    )
    parser.add_argument(
        "--layer-regex",
        help=f"Only gates from layers where the name matches this regex are considered. (Default: \"{DEFAULT_LAYER_REGEX}\")",
        default=DEFAULT_LAYER_REGEX,
    )
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    )
    parser.add_argument(
        "--auto-adjust-cropping",
        help="If true(default), the cropping ranges are adjusted based on some unstable feature detection algorithm.",
        choices=[True, False],
        type=lambda x: x.lower() == "true",
        default=True,
    )

    parser.add_argument(
        "--expected-gate-number",
        help="Expected number of gates in integer slice notation (excluding end). "
        "The default will result in an error if there are no gates extracted",
        metavar="[START]:[STOP]",
        type=to_slice,
        default="1:",
    )

    return parser


def _main(
    dxf_path: str,
    json_path: str,
    layer_regex: str,
    x_rng: tuple[float, float],
    y_rng: tuple[float, float],
    expected_gate_number: slice,
    auto_adjust_cropping: bool,
):
    matplotlib.use("qtagg")
    doc = ezdxf.readfile(dxf_path)
    raw_gates = get_gates_from_cropped_region(
        doc,
        layer_regex=layer_regex,
        x_rng=x_rng,
        y_rng=y_rng,
        auto_adjust_cropping=auto_adjust_cropping
    )
    logger.info(f"{len(raw_gates)} raw gates extracted.")

    merged_gates = auto_merge(raw_gates)
    logger.info(f"{len(merged_gates)} gates left after merging.")

    if expected_gate_number.start is not None and len(merged_gates) < expected_gate_number.start:
        raise ValueError(f"Only {len(merged_gates)} gates extracted but >= {expected_gate_number.start} were expected.")
    if expected_gate_number.stop is not None and len(merged_gates) >= expected_gate_number.stop:
        raise ValueError(f"Only {len(merged_gates)} gates extracted but < {expected_gate_number.stop} were expected.")

    if not merged_gates:
        # this is apparently explicitly allowed by the user cause otherwise the expected_gate_number check should fail
        logger.info("No gates extracted. Storing empty gates in json path")
        store_to_file([], json_path)
        return

    resulting_gates = label_gates(merged_gates)
    plt.show(block=True)
    store_to_file(resulting_gates, json_path)


if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()
    if args.json_path is None:
        args.json_path = args.dxf_path.with_suffix(".json")

    logging.basicConfig()
    logger.setLevel(args.log_level)

    _main(args.dxf_path, args.json_path, args.layer_regex, args.x_rng, args.y_rng,
          args.expected_gate_number, auto_adjust_cropping=args.auto_adjust_cropping)
