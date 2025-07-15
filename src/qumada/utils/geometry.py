import dataclasses
import pathlib
import json

from shapely.geometry import Point, LineString, Polygon
from shapely import wkt

@dataclasses.dataclass
class Gate:
    polygon: Polygon
    path: list[str]
    layer: str
    label: str | None
    label_position: tuple[float, float]

def gate_list_to_string(gates: list[Gate]) -> str:
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
    data = json.loads(txt)
    assert isinstance(data, list)

    gates = []
    for d in data:
        d["polygon"] = wkt.loads(d["polygon"])
        d["label_position"] = tuple(d["label_position"])
        gates.append(Gate(**d))
    return gates


def store_to_file(gates: list[Gate], path: pathlib.Path):
    path = pathlib.Path(path)
    txt = gate_list_to_string(gates)
    path.write_text(txt)


def load_from_file(path: pathlib.Path):
    path = pathlib.Path(path)
    txt = path.read_text()
    return string_to_gate_list(txt)
