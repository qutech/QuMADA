"""
General Object class for the domain.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import Field, dataclass, fields, is_dataclass
from typing import Iterable, Sequence, TypeVar, get_type_hints

from qtools.data.db import _api_get, _api_put

T = TypeVar("T", bound="DomainObject")


@dataclass
class DomainObject:
    """Represents a database entry. Consists of the data fields, every db entry has."""
    name: str
    pid: str
    creatorId: str          # pylint: disable=invalid-name
    createDate: str         # pylint: disable=invalid-name
    lastChangerId: str      # pylint: disable=invalid-name
    lastChangeDate: str     # pylint: disable=invalid-name

    @classmethod
    def _create(cls: type[T], name: str, **kwargs) -> T:
        """
        This factory function creates a DomainObject while ensuring, that the internal DB fields are all set to None.
        This function is usually not called directly, but by the factory function of a child class.

        Args:
            name (str): Name of the DomainObject

        Returns:
            [cls]: Created object
        """
        # Set default values for internal fields
        kwargs["name"] = name
        kwargs.setdefault("pid", None)
        kwargs.setdefault("creatorId", None)
        kwargs.setdefault("createDate", None)
        kwargs.setdefault("lastChangerId", None)
        kwargs.setdefault("lastChangeDate", None)
        return cls(**kwargs)

    @classmethod
    def get_by_id(cls: type[T], pid: str) -> T:
        """get a domain object by pid from the database."""
        return cls._get_by_id(pid)

    @classmethod
    def _get_by_id(
        cls: type[T], pid: str, fn_name: str | None = None, id_name: str = "pid"
    ) -> T:
        # Try to guess function name if not provided
        if fn_name is None:
            fn_name = f"get{cls.__name__}ById"
        data = _api_get(fn_name, {id_name: pid})
        return cls(**data)

    @classmethod
    def get_all(cls: type[T]) -> list[T]:
        """get all domain objects of the specific type from the database."""
        return cls._get_all()

    @classmethod
    def _get_all(cls: type[T], fn_name: str | None = None) -> list[T]:
        # Try to guess function name if not provided
        if fn_name is None:
            fn_name = f"{cls.__name__.lower()}s"
        return [cls(**data) for data in _api_get(fn_name)]

    def save(self):
        """saves the domain object to the database."""
        return self._save()

    def _save(
        self: DomainObject,
        fn_name: str | None = None,
        field_names: list[str] | None = None,
    ) -> str:
        # Try to guess function name if not provided
        if fn_name is None:
            fn_name = f"put{type(self).__name__}"
        if field_names is None:
            field_names = [f.name for f in fields(self)]
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
                attr = str(attr) if attr is not None else ""
            data[field_name] = attr
        resp = _api_put(fn_name, data)
        self._handle_db_response(resp)
        return self.pid

    def to_json(self) -> str:
        """Return a JSON representation of the domain object."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def __post_init__(self) -> None:
        # Select all variables, that should be a dataclass, but are a dict (or dics in lists) and
        # turn them into the respective objects.
        # The field's type is evaluated using get_type_hints, because dataclasses are incompatible
        # with the string type hints, which are introduced with PEP 563 and "from __future__ import annotations"
        # This behavior may change in the future, if PEP 649 is implemented
        def _load_field(field: Field):
            name = field.name
            obj = self.__dict__[name]
            cls = types[name]
            if is_dataclass(cls) and isinstance(obj, Mapping):
                return cls(**obj)
            elif isinstance(obj, Sequence) and not isinstance(obj, str):
                # list of dicts?
                # A sequence type hint has only one entry
                cls = cls.__args__[0]
                if is_dataclass(cls):
                    return list(
                        map(lambda d: cls(**d) if isinstance(d, Mapping) else d, obj)
                    )
            return None

        types = get_type_hints(type(self))
        objects = {}
        for field in fields(self):
            obj = _load_field(field)
            if obj:
                objects[field.name] = obj
        self.__dict__.update(objects)

    def __eq__(self, other) -> bool:
        return self.__dict__ == other.__dict__

    def _handle_db_response(self, response) -> None:
        if not response["status"]:
            raise Exception(response["errorMessage"])
        # save pid
        self.pid = response["id"]
