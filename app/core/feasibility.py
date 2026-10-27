"""Checks whether a set of blocks can physically fit on a die.

Rectangle packing is NP-hard, so there are two kinds of answer:
  * hard failure  -> mathematically impossible (a block is bigger than the die,
                     or total block area is larger than the die area)
  * soft failure  -> area is fine, but a shelf-packing heuristic could not find
                     a legal arrangement, so it is *probably* too tight
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.core.models import Block

Placement = Dict[str, Tuple[float, float, float, float]]  # name -> (x, y, w, h)


@dataclass
class FeasibilityResult:
    ok: bool
    hard_fail: bool = False
    reasons: List[str] = field(default_factory=list)
    utilization: float = 0.0
    placement: Optional[Placement] = None   # a legal arrangement, if one was found
    suggested_side: Optional[int] = None    # square die side that should work

    def message(self) -> str:
        return "\n".join(self.reasons)


def _shelf_pack(items, width, height) -> Optional[Placement]:
    """Place (name, w, h) items left-to-right in shelves, tallest first."""
    items = sorted(items, key=lambda t: t[2], reverse=True)
    placement: Placement = {}
    x = y = shelf_h = 0.0
    for name, w, h in items:
        if w > width or h > height:
            return None
        if x + w > width:                 # start a new shelf
            y += shelf_h
            x, shelf_h = 0.0, 0.0
        if y + h > height:
            return None
        placement[name] = (x, y, w, h)
        x += w
        shelf_h = max(shelf_h, h)
    return placement


def pack(blocks: List[Block], width: float, height: float, allow_rotation: bool = True) -> Optional[Placement]:
    """Try a few orientation strategies; return the first legal arrangement."""
    strategies = ["as_is"] + (["wide", "tall"] if allow_rotation else [])
    for mode in strategies:
        items = []
        for b in blocks:
            w, h = b.width, b.height
            if mode == "wide" and h > w:
                w, h = h, w
            elif mode == "tall" and w > h:
                w, h = h, w
            items.append((b.name, w, h))
        result = _shelf_pack(items, width, height)
        if result is not None:
            return result
    return None


def suggest_side(blocks: List[Block], allow_rotation: bool = True, headroom: float = 1.2) -> int:
    """Smallest square die (rounded up to 10 um) that packs, plus some headroom."""
    if not blocks:
        return 400
    total = sum(b.area() for b in blocks)
    side = max(math.sqrt(total), max(min(b.width, b.height) for b in blocks))
    side = max(side, max(max(b.width, b.height) for b in blocks) if not allow_rotation else side)
    for _ in range(400):
        if pack(blocks, side, side, allow_rotation) is not None:
            break
        side *= 1.03
    return int(math.ceil(side * headroom / 10.0) * 10)


def check_feasibility(blocks: List[Block], width: float, height: float,
                      allow_rotation: bool = True) -> FeasibilityResult:
    res = FeasibilityResult(ok=True)
    chip_area = width * height
    total = sum(b.area() for b in blocks)
    res.utilization = total / chip_area if chip_area > 0 else float("inf")
    if not blocks:
        return res

    for b in blocks:
        fits = (b.width <= width and b.height <= height)
        if allow_rotation:
            fits = fits or (b.height <= width and b.width <= height)
        if not fits:
            res.ok, res.hard_fail = False, True
            res.reasons.append(
                f"{b.name} ({b.width:g} x {b.height:g}) is larger than the die ({width:g} x {height:g}).")

    if total > chip_area:
        res.ok, res.hard_fail = False, True
        res.reasons.append(
            f"Total component area {total:,.0f} um\u00b2 exceeds the die area {chip_area:,.0f} um\u00b2 "
            f"({res.utilization * 100:.0f}% utilization).")

    if res.ok:
        placement = pack(blocks, width, height, allow_rotation)
        if placement is None:
            res.ok = False
            res.reasons.append(
                f"Area is sufficient ({res.utilization * 100:.0f}% utilization) but no legal arrangement "
                f"could be found. The die is probably too tight.")
        else:
            res.placement = placement

    if not res.ok:
        res.suggested_side = suggest_side(blocks, allow_rotation)
    return res
