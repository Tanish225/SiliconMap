# half-perimeter wirelength (HPWL) algorithm
from app.core.models import Floorplan, Net

def calculate_hpwl(net: Net) -> float:
    """Calculates the bounding box perimeter for all blocks in a net."""
    if not net.connected_blocks:
        return 0.0
        
    # Find the center coordinates of each connected block
    x_coords = [b.x + (b.width / 2) for b in net.connected_blocks]
    y_coords = [b.y + (b.height / 2) for b in net.connected_blocks]
    
    min_x, max_x = min(x_coords), max(x_coords)
    min_y, max_y = min(y_coords), max(y_coords)
    
    # Half-perimeter
    return (max_x - min_x) + (max_y - min_y)

def calculate_total_cost(floorplan: Floorplan) -> float:
    """Calculates the total wirelength cost of the current floorplan."""
    total_wirelength = sum(calculate_hpwl(net) for net in floorplan.nets)
    
    # You can add area overlap penalties or congestion metrics here later
    return total_wirelength