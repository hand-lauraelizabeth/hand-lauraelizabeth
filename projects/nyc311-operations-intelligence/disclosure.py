"""Disclosure gate for NYC 311 aggregate views; standard library only.

Do not publish source marginals alongside suppressed cells: exact row/column
marginals can reconstruct otherwise hidden counts.
"""

def publish_cells(cells, *, minimum=10):
    """Return safe detailed cells without exact marginal totals.

    All breakdowns must be built from the same permitted result, not the source.
    """
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 2:
        raise ValueError("minimum must be an integer >= 2")
    seen = set()
    output = []
    for cell in cells:
        group = tuple(cell[k] for k in ("month", "borough", "agency", "problem"))
        if group in seen:
            raise ValueError("duplicate aggregate grain")
        seen.add(group)
        n = cell["requests"]
        closed = cell.get("closed_with_valid_interval")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise ValueError("invalid request count")
        if closed is not None and (not isinstance(closed, int) or closed < 0 or closed > n):
            raise ValueError("invalid closed count")
        if n < minimum:
            continue
        safe = {k: cell[k] for k in ("month", "borough", "agency", "problem")}
        safe["requests"] = n
        if closed is not None and closed >= minimum and n - closed >= minimum:
            safe["closed_with_valid_interval"] = closed
        output.append(safe)
    return {"minimum": minimum, "marginals_available": False,
            "cells": output, "note": "Suppressed cells omitted; exact source totals and derived marginals intentionally withheld."}
