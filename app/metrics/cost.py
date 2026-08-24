from app.core.models import Floorplan, Net, Block

def calculate_hpwl(net: Net) -> float:
    if not net.connected_blocks:
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

# NEW: Congestion math
def calculate_congestion(floorplan: Floorplan, grid_size: float = 100.0) -> float:
    """Estimates routing congestion by dividing the chip into a grid."""
    congestion_grid = {}
    
    for net in floorplan.nets:
        if not net.connected_blocks:
            continue
            
        x_coords = [b.x + (b.width / 2) for b in net.connected_blocks]
        y_coords = [b.y + (b.height / 2) for b in net.connected_blocks]
        
        # Bounding box of the wire network
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # Map physical coordinates to grid cell indexes
        start_col, end_col = int(min_x // grid_size), int(max_x // grid_size)
        start_row, end_row = int(min_y // grid_size), int(max_y // grid_size)
        
        # Increment the wire count for every grid cell this wire crosses
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = (row, col)
                congestion_grid[cell] = congestion_grid.get(cell, 0) + 1
                
    # Penalize grid cells that have too many overlapping wires
    penalty = 0.0
    for cell, count in congestion_grid.items():
        if count > 2: # Allow up to 2 wires per grid space safely
            penalty += (count ** 2) # Square the count to severely punish hotspots
            
    return penalty

# UPDATED: Incorporate the congestion penalty
def calculate_total_cost(floorplan: Floorplan, overlap_weight: float = 1000.0, congestion_weight: float = 50.0) -> float:
    total_wirelength = sum(calculate_hpwl(net) for net in floorplan.nets)
    
    total_overlap = 0.0
    blocks = floorplan.blocks
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            total_overlap += calculate_overlap_area(blocks[i], blocks[j])
            
    total_congestion = calculate_congestion(floorplan)
            
    # Final combined objective function
    return total_wirelength + (total_overlap * overlap_weight) + (total_congestion * congestion_weight)