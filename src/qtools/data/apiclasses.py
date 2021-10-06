from __future__ import annotations

from dataclasses import MISSING
from dataclasses import Field as DataclassField
from typing import Literal


class NotADataclassError(Exception):
    pass


class Field(DataclassField):
    __slots__ = ("put", "get", "get_all")

    def __init__(
        self,
        default,
        default_factory,
        init,
        repr,
        hash,
        compare,
        metadata,
        put,
        get,
        get_all,
    ):
        super().__init__(default, default_factory, init, repr, hash, compare, metadata)
        self.put = put
        self.get = get
        self.get_all = get_all

    def __repr__(self):
        ...


# This function is used instead of exposing Field creation directly,
# so that a type checker can be told (via overloads) that this is a
# function whose type depends on its parameters.
def field(
    *,
    default=MISSING,
    default_factory=MISSING,
    init=True,
    repr=True,
    hash=None,
    compare=True,
    metadata=None,
    put=True,
    get=True,
    get_all=True,
):
    """Return an object to identify apiclass fields."""

    if default is not MISSING and default_factory is not MISSING:
        raise ValueError("cannot specify both default and default_factory")
    return Field(
        default, default_factory, init, repr, hash, compare, metadata, put, get, get_all
    )


def _process_class(
    cls,
    api: Literal["rest"],
    get_by_id: str | None,
    get_all: str | None,
    save_or_update: str | None,
):
    # Throw Error if cls is no dataclass
    fields = getattr(cls, "__dataclass_fields__", None)
    if not fields:
        raise NotADataclassError(
            "Decorated class is not a dataclass. Add @dataclass decorator after @apiclass decorator."
        )

    if get_by_id:
        ...

    if get_all:
        ...

    if save_or_update:
        ...


def apiclass(
    cls=None,
    /,
    *,
    api: Literal["rest"] = "rest",
    get_by_id: str | None = None,
    get_all: str | None = None,
    save_or_update: str | None = None,
):
    """
    Returns the same class as was passed in, with dunder methods
    added based on the fields defined in the class.

    Examines PEP 526 __annotations__ to determine fields.

    Args:
        api (Literal["rest"], optional): Determines the type of API.
                                         Currently, only REST is available.
                                         Defaults to "rest".
    """

    def wrap(cls):
        return _process_class(cls, api, get_by_id, get_all, save_or_update)

    # See if we're being called as @dataclass or @dataclass().
    if cls is None:
        # We're called with parens.
        return wrap

    # We're called as @dataclass without parens.
    return wrap(cls)
