import pytest

import json
from qtools.data.device import Wafer


def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


@pytest.fixture
def json_wafer():
    return json.loads("""
        {
            "creatorId": null,
            "createDate": null,
            "lastChangerId": null,
            "lastChangeDate": null,
            "name": "test",
            "description": "Test Descr",
            "productionDate": null,
            "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
        }
        """)


class TestWafer:
    def test_Wafer_from_json(self, json_wafer):
        wafer = Wafer(**json_wafer)
        assert ordered(json_wafer) == ordered(wafer.__dict__)
        wafer.name = "not_test"
        assert not ordered(json_wafer) == ordered(wafer.__dict__)

    def test_Wafer_to_json(self, json_wafer):
        wafer = Wafer(**json_wafer)
        assert ordered(json_wafer) == ordered(json.loads(wafer.to_json()))
        wafer.name = "not_test"
        assert not ordered(json_wafer) == ordered(json.loads(wafer.to_json()))
