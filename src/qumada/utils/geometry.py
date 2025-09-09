import dataclasses
import json
import pathlib

from shapely import wkt
from shapely.geometry import LineString, Point, Polygon


@dataclasses.dataclass
class Gate:
    """Representation of a gate electrode with the geometric properties and annotation information."""

    polygon: Polygon
    path: list[str]
    layer: str
    label: str | None
    label_position: tuple[float, float]


def gate_list_to_string(gates: list[Gate]) -> str:
    """Serialize a list of gates to a JSON string.

    The geometric information is stored in WKT format (well known text)."""

    def to_json(o):
        if isinstance(o, Gate):
            return dataclasses.asdict(o)
        elif isinstance(o, Polygon):
            return o.wkt
        else:
            return o

    txt = json.dumps(gates, indent=2, default=to_json)
    return txt


def string_to_gate_list(txt: str) -> list[Gate]:
    """Deserialize a JSON string produced by :py:`.gate_list_to_string` to a list of gates."""

    data = json.loads(txt)
    assert isinstance(data, list)

    gates = []
    for d in data:
        d["polygon"] = wkt.loads(d["polygon"])
        d["label_position"] = tuple(d["label_position"])
        gates.append(Gate(**d))
    return gates


def store_to_file(gates: list[Gate], path: pathlib.Path):
    """Store a list of gates in a file in json format."""
    path = pathlib.Path(path)
    txt = gate_list_to_string(gates)
    path.write_text(txt)


def load_from_file(path: pathlib.Path):
    """Load a list of gates from a JSON file produced with :py:`.store_to_file`."""
    path = pathlib.Path(path)
    txt = path.read_text()
    return string_to_gate_list(txt)
