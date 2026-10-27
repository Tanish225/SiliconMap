import math
from app.core.models import Floorplan, Net, Block

OVERLAP_WEIGHT = 2000.0
CONGESTION_WEIGHT = 50.0
BOUNDS_WEIGHT = 3000.0
THERMAL_WEIGHT = 10.0


def calculate_hpwl(net: Net) -> float:
    """Half-perimeter wirelength of one net (block-centre approximation)."""
    if len(net.connected_blocks) < 2:
        return 0.0
    x_coords = [b.x + (b.width / 2) for b in net.connected_blocks]
    y_coords = [b.y + (b.height / 2) for b in net.connected_blocks]
    return (max(x_coords) - min(x_coords)) + (max(y_coords) - min(y_coords))


def calculate_overlap_area(b1: Block, b2: Block) -> float:
    dx = min(b1.x + b1.width, b2.x + b2.width) - max(b1.x, b2.x)
    dy = min(b1.y + b1.height, b2.y + b2.height) - max(b1.y, b2.y)
    if dx > 0 and dy > 0:
        return dx * dy
    return 0.0


def calculate_total_overlap(floorplan: Floorplan) -> float:
    blocks = floorplan.blocks
    return sum(calculate_overlap_area(blocks[i], blocks[j])
               for i in range(len(blocks)) for j in range(i + 1, len(blocks)))


def count_overlaps(floorplan: Floorplan, tolerance: float = 0.01) -> int:
    blocks = floorplan.blocks
    return sum(1 for i in range(len(blocks)) for j in range(i + 1, len(blocks))
               if calculate_overlap_area(blocks[i], blocks[j]) > tolerance)


def calculate_congestion(floorplan: Floorplan, grid_size: float = None) -> float:
    # Grid is a quarter of the die so the metric scales with chip size (100 um for a 400 um die).
    if grid_size is None:
        grid_size = max(floorplan.chip_width, floorplan.chip_height) / 4.0
    grid_size = max(grid_size, 1.0)
    congestion_grid = {}
    for net in floorplan.nets:
        if len(net.connected_blocks) < 2:
            continue
        x_coords = [b.x + (b.width / 2) for b in net.connected_blocks]
        y_coords = [b.y + (b.height / 2) for b in net.connected_blocks]
        start_col, end_col = int(min(x_coords) // grid_size), int(max(x_coords) // grid_size)
        start_row, end_row = int(min(y_coords) // grid_size), int(max(y_coords) // grid_size)
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = (row, col)
                congestion_grid[cell] = congestion_grid.get(cell, 0) + 1
    penalty = 0.0
    for count in congestion_grid.values():
        if count > 2:
            penalty += count ** 2
    return penalty


def calculate_out_of_bounds_penalty(floorplan: Floorplan) -> float:
    """Total distance (um) by which blocks stick out of the die on any side."""
    penalty = 0.0
    for b in floorplan.blocks:
        penalty += max(0.0, -b.x) + max(0.0, b.x + b.width - floorplan.chip_width)
        penalty += max(0.0, -b.y) + max(0.0, b.y + b.height - floorplan.chip_height)
    return penalty


def calculate_thermal_penalty(floorplan: Floorplan) -> float:
    """Penalizes high-power components being placed too close together."""
    penalty = 0.0
    blocks = floorplan.blocks
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            b1, b2 = blocks[i], blocks[j]
            dx = (b1.x + b1.width / 2) - (b2.x + b2.width / 2)
            dy = (b1.y + b1.height / 2) - (b2.y + b2.height / 2)
            dist = math.hypot(dx, dy)
            penalty += (b1.power_watts * b2.power_watts) / max(dist, 1.0)
    return penalty


def cost_breakdown(floorplan: Floorplan) -> dict:
    """Every cost term separately, plus legality information for the UI."""
    wl = sum(calculate_hpwl(n) for n in floorplan.nets)
    ov = calculate_total_overlap(floorplan)
    cg = calculate_congestion(floorplan)
    oob = calculate_out_of_bounds_penalty(floorplan)
    heat = calculate_thermal_penalty(floorplan)
    total = (wl + ov * OVERLAP_WEIGHT + cg * CONGESTION_WEIGHT
             + oob * BOUNDS_WEIGHT + heat * THERMAL_WEIGHT)
    return {
        "total": total, "wirelength": wl, "overlap_area": ov, "congestion": cg,
        "out_of_bounds": oob, "thermal": heat,
        "overlap_count": count_overlaps(floorplan),
        "legal": count_overlaps(floorplan) == 0 and oob < 0.01,
    }


def calculate_total_cost(floorplan: Floorplan, overlap_weight: float = OVERLAP_WEIGHT,
                         congestion_weight: float = CONGESTION_WEIGHT) -> float:
    wl = sum(calculate_hpwl(n) for n in floorplan.nets)
    return (wl + calculate_total_overlap(floorplan) * overlap_weight
            + calculate_congestion(floorplan) * congestion_weight
            + calculate_out_of_bounds_penalty(floorplan) * BOUNDS_WEIGHT
            + calculate_thermal_penalty(floorplan) * THERMAL_WEIGHT)
