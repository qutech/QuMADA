from __future__ import annotations

from typing import Iterable

from qtools.data.db import _api_get, _api_put
from qtools.data.domain import DomainObject


def _process_class_get_by_id(cls, fn_name: str, id_name: str):
    # Try to guess function name if not provided
    if fn_name is None:
        fn_name = f"get{cls.__name__}ById"

    # TODO: change this to exec-construction, that dataclasses uses for better introspection

    def get_by_id(cls, pid: str):
        data = _api_get(fn_name, {id_name: pid})
        return cls(**data)

    setattr(cls, "get_by_id", classmethod(get_by_id))
    return cls


def get_by_id(cls=None, /, *, fn_name: str | None = None, id_name: str | None = "pid"):
    """
    Decorator construction to add an API call to get an object by pid.

    This decorator adds a class method get_by_id to the class, that takes a pid and returns
    the corresponding object from the database.

    Args:
        fn_name: Name of the API call. If None, f"get{cls.__name__}ById" is used.
        id_name: Name of the ID datafield of the API call. Defaults to "pid".
    """

    def wrap(cls):
        return _process_class_get_by_id(cls, fn_name, id_name)

    if cls is None:
        return wrap
    return wrap(cls)


def _process_class_get_all(cls, fn_name: str):
    # Try to guess function name if not provided
    if fn_name is None:
        fn_name = f"{cls.__name__.lower()}s"

    # TODO: change this to exec-construction, that dataclasses uses for better introspection

    def get_all(cls):
        return [cls(**data) for data in _api_get(fn_name)]

    setattr(cls, "get_all", classmethod(get_all))
    return cls


def get_all(cls=None, /, *, fn_name: str | None = None):
    """
    Decorator construction to add an API call to get all objects from the database.

    This decorator adds a class method get_all to the class, that returns all corresponding objects from the database.

    Args:
        fn_name: Name of the API call. If None, f"{cls.__name__.lower()}s" is used.
    """

    def wrap(cls):
        return _process_class_get_all(cls, fn_name)

    if cls is None:
        return wrap
    return wrap(cls)


def _process_class_save(cls, fn_name: str, field_names: list[str]):
    # Try to guess function name if not provided
    if fn_name is None:
        fn_name = f"put{cls.__name__}"
    if field_names is None:
        field_names = list(getattr(cls, "__dataclass_fields__").keys())

    # TODO: change this to exec-construction, that dataclasses uses for better introspection

    def save(self):
        # data = {field_name: getattr(self, field_name) for field_name in field_names}
        data = {}
        for field_name in field_names:
            # TODO: match-clause with Python 3.10
            attr = getattr(self, field_name)
            if isinstance(attr, DomainObject):
                # Take pid for DomainObjects by default
                attr = attr.pid
                field_name = f"{field_name}Id"
            elif isinstance(attr, Iterable) and not isinstance(attr, str):
                # Take pid from all DomainObjects
                attr = [a.pid if isinstance(a, DomainObject) else a for a in attr]
                # Join Iterables by comma
                attr = ",".join(attr)
                field_name = f"{field_name.removesuffix('s')}Ids"
            elif not isinstance(attr, str):
                # Turn everything else into str (except None, which turns into an empty string instead of "None")
                attr = str(attr or "")
            data[field_name] = attr
        resp = _api_put(fn_name, data)
        self._handle_db_response(resp)
        return self.pid

    setattr(cls, "save", save)
    return cls


def save(
    cls=None, /, *, fn_name: str | None = None, field_names: list[str] | None = None
):
    """
    Decorator construction to add an API call to put an object into the database.

    This decorator adds a class method save to the class, that creates or updates the object entry on the database.

    Args:
        fn_name: Name of the API call. If None, f"put{cls.__name__}" is used.
        field_names: List of all fields names, the api call gets.
                     If None, every field of the class is used.
    """

    def wrap(cls):
        return _process_class_save(cls, fn_name, field_names)

    if cls is None:
        return wrap
    return wrap(cls)
