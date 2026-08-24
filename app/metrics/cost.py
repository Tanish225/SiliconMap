from app.core.models import Floorplan, Net, Block

def calculate_hpwl(net: Net) -> float:
    """Calculates the bounding box perimeter for all blocks in a net."""
    if not net.connected_blocks:
        return 0.0
        
    x_coords = [b.x + (b.width / 2) for b in net.connected_blocks]
    y_coords = [b.y + (b.height / 2) for b in net.connected_blocks]
    
    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)
    
    return (max_x - min_x) + (max_y - min_y)

def calculate_overlap_area(b1: Block, b2: Block) -> float:
    """Calculates the overlapping area between two blocks."""
    # Find the intersecting rectangle dimensions
    dx = min(b1.x + b1.width, b2.x + b2.width) - max(b1.x, b2.x)
    dy = min(b1.y + b1.height, b2.y + b2.height) - max(b1.y, b2.y)
    
    # If both dx and dy are positive, the blocks overlap
    if dx > 0 and dy > 0:
        return dx * dy
    return 0.0

def calculate_total_cost(floorplan: Floorplan, overlap_weight: float = 1000.0) -> float:
    """Calculates total cost including wirelength and overlap penalty."""
    # 1. Wirelength Cost
    total_wirelength = sum(calculate_hpwl(net) for net in floorplan.nets)
    
    # 2. Overlap Penalty
    total_overlap = 0.0
    blocks = floorplan.blocks
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            total_overlap += calculate_overlap_area(blocks[i], blocks[j])
            
    # The penalty forces the optimizer to prioritize moving blocks apart
    return total_wirelength + (total_overlap * overlap_weight)