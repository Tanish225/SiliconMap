import math
from app.core.models import Floorplan, Net, Block

def calculate_hpwl(net: Net) -> float:
    if not net.connected_blocks: return 0.0
    x_coords = [b.x + (b.width / 2) for b in net.connected_blocks]
    y_coords = [b.y + (b.height / 2) for b in net.connected_blocks]
    return (max(x_coords) - min(x_coords)) + (max(y_coords) - min(y_coords))

def calculate_overlap_area(b1: Block, b2: Block) -> float:
    dx = min(b1.x + b1.width, b2.x + b2.width) - max(b1.x, b2.x)
    dy = min(b1.y + b1.height, b2.y + b2.height) - max(b1.y, b2.y)
    if dx > 0 and dy > 0: return dx * dy
    return 0.0

def calculate_congestion(floorplan: Floorplan, grid_size: float = 100.0) -> float:
    congestion_grid = {}
    for net in floorplan.nets:
        if not net.connected_blocks: continue
        x_coords = [b.x + (b.width / 2) for b in net.connected_blocks]
        y_coords = [b.y + (b.height / 2) for b in net.connected_blocks]
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        start_col, end_col = int(min_x // grid_size), int(max_x // grid_size)
        start_row, end_row = int(min_y // grid_size), int(max_y // grid_size)
        
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = (row, col)
                congestion_grid[cell] = congestion_grid.get(cell, 0) + 1
                
    penalty = 0.0
    for count in congestion_grid.values():
        if count > 2: penalty += (count ** 2) 
    return penalty

def calculate_out_of_bounds_penalty(floorplan: Floorplan) -> float:
    penalty = 0.0
    for b in floorplan.blocks:
        if b.x < 0: penalty += abs(b.x)
        elif b.x + b.width > floorplan.chip_width: penalty += (b.x + b.width - floorplan.chip_width)
        if b.y < 0: penalty += abs(b.y)
        elif b.y + b.height > floorplan.chip_height: penalty += (b.y + b.height - floorplan.chip_height)
    return penalty

def calculate_thermal_penalty(floorplan: Floorplan) -> float:
    """Penalizes high-power components being placed too close together."""
    penalty = 0.0
    blocks = floorplan.blocks
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            b1, b2 = blocks[i], blocks[j]
            # Center-to-center Euclidean distance
            dx = (b1.x + b1.width/2) - (b2.x + b2.width/2)
            dy = (b1.y + b1.height/2) - (b2.y + b2.height/2)
            dist = math.hypot(dx, dy)
            
            # If distance is small, heat penalty skyrockets
            penalty += (b1.power_watts * b2.power_watts) / max(dist, 1.0)
    return penalty

def calculate_total_cost(floorplan: Floorplan, overlap_weight: float = 2000.0, congestion_weight: float = 50.0) -> float:
    total_wirelength = sum(calculate_hpwl(net) for net in floorplan.nets)
    total_overlap = sum(calculate_overlap_area(floorplan.blocks[i], floorplan.blocks[j]) 
                        for i in range(len(floorplan.blocks)) for j in range(i + 1, len(floorplan.blocks)))
    total_congestion = calculate_congestion(floorplan)
    total_out_of_bounds = calculate_out_of_bounds_penalty(floorplan)
    total_heat = calculate_thermal_penalty(floorplan)
            
    return total_wirelength + (total_overlap * overlap_weight) + (total_congestion * congestion_weight) + (total_out_of_bounds * 3000.0) + (total_heat * 10.0)