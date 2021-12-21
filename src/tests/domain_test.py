import json

import pytest
import requests
from pytest_httpserver import HTTPServer

import qtools.data.db as db
from qtools.data.device import Wafer


def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj


@pytest.fixture(scope="function", autouse=True)
def setup_db(httpserver: HTTPServer):
    db.api_url = httpserver.url_for("")


@pytest.fixture
def min_wafer() -> Wafer:
    return Wafer(
        "wafer_test", None, None, None, None, None, "wafer test description", "20211221"
    )


@pytest.fixture
def max_wafer() -> Wafer:
    return Wafer(
        name="wafer_test",
        pid="89738c4a-e46b-40de-b2fd-c5aaeea7175c",
        creatorId="DG",
        createDate="20211220",
        lastChangerId="DG",
        lastChangeDate="20211221",
        description="wafer test description",
        productionDate="20211221",
    )


@pytest.fixture
def json_wafer():
    return json.loads("""
        {
            "creatorId": "DG",
            "createDate": "20211220",
            "lastChangerId": "DG",
            "lastChangeDate": "20211221",
            "name": "wafer_test",
            "description": "wafer test description",
            "productionDate": "20211221",
            "pid": "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
        }
        """)


class TestDomain:
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

    def test_Wafer_factory(self, min_wafer: Wafer, max_wafer: Wafer):
        wafer = Wafer.create("wafer_test", "wafer test description", "20211221")
        assert wafer == min_wafer
        wafer = Wafer.create(
            name="wafer_test",
            description="wafer test description",
            productionDate="20211221",
            pid="89738c4a-e46b-40de-b2fd-c5aaeea7175c",
            creatorId="DG",
            createDate="20211220",
            lastChangerId="DG",
            lastChangeDate="20211221",
        )
        assert wafer == max_wafer

    def test_Wafer_from_pid(self, json_wafer, max_wafer: Wafer, httpserver: HTTPServer):
        httpserver.expect_request(
            "/getWaferById",
            query_string="pid=89738c4a-e46b-40de-b2fd-c5aaeea7175c",
            method="GET",
        ).respond_with_json(json_wafer)
        assert Wafer.get_by_id("89738c4a-e46b-40de-b2fd-c5aaeea7175c") == max_wafer

    def test_Wafer_get_all(self, json_wafer, max_wafer: Wafer, httpserver: HTTPServer):
        httpserver.expect_request("/wafers").respond_with_json([json_wafer, json_wafer])
        wafers = Wafer.get_all()
        assert wafers == [max_wafer, max_wafer]

    def test_Wafer_save(self, min_wafer: Wafer, httpserver: HTTPServer):
        # TODO: improve data matching
        data = {
            "name": "wafer_test",
            "description": "wafer test description",
            "productionDate": "20211221",
            "pid": "",
            "creatorId": "",
            "createDate": "",
            "lastChangerId": "",
            "lastChangeDate": "",
        }
        print(data)
        response = {
            "status": True,
            "id": "89738c4a-e46b-40de-b2fd-c5aaeea7175c",
            "errorMessage": None,
        }
        httpserver.expect_request(
            "/saveOrUpdateWafer", method="PUT", json=data
        ).respond_with_json(response)
        assert min_wafer.save() == "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
        assert min_wafer.pid == "89738c4a-e46b-40de-b2fd-c5aaeea7175c"
