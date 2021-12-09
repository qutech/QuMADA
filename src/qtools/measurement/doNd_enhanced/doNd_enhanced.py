"""
Created on Mon Nov 29 12:57:40 2021

@author: lab
"""
from __future__ import annotations

import operator
from functools import partial
from typing import Any, Callable


def _interpret_breaks(break_conditions: list, **kwargs) -> Callable[[], bool] | None:
    """
    Translates break conditions and returns callable to check them.

    Parameters
    ----------
    break_conditions : List of dictionaries containing:
            "channel": Gettable parameter to check
            "break_condition": String specifying the break condition.
                    Syntax:
                        Parameter to check: only "val" supported so far.
                        Comparator: "<",">" or "=="
                        Value: float
                    The parts have to be separated by blanks.

    **kwargs : TYPE
        DESCRIPTION.

    Returns
    -------
    Callable
        Function, that returns a boolean, True if break conditions are fulfilled.

    """

    def eval_binary_expr(op1: Any, oper: str, op2: Any) -> bool:
        # evaluates the string "op1 [operator] op2
        # supports <, > and == as operators
        ops = {
        '>' : operator.gt,
        '<' : operator.lt,
        '==' : operator.eq,
        }
        # Why convert explicitly to float?
        # op1, op2 = float(op1), float(op2)
        return ops[oper](op1, op2)

    def check_conditions(conditions: list[Callable[[], bool]]):
        for cond in conditions:
            if cond():
                return True
        return False

    conditions = []
    # Create break condition callables
    for cond in break_conditions:
        ops = cond["break_condition"].split(" ")
        if ops[0] != "val":
            raise NotImplementedError(
                'Only parameter values can be used for breaks in this version. Use "val" for the break condition.'
            )
        f = lambda: eval_binary_expr(cond["channel"].get(), ops[1], float(ops[2]))
        conditions.append(f)
    return partial(check_conditions, conditions) if conditions else None
