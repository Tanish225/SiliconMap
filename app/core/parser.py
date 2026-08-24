import json
from app.core.models import Block, Net, Floorplan

def load_floorplan_from_json(filepath: str) -> Floorplan:
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    blocks_dict = {}
    
    # 1. Parse all blocks
    for b_data in data.get("blocks", []):
        block = Block(
            name=b_data["name"],
            width=b_data["width"],
            height=b_data["height"],
            x=b_data.get("x", 0.0),
            y=b_data.get("y", 0.0)
        )
        blocks_dict[block.name] = block
        
    # 2. Parse all nets and link them to the blocks
    nets = []
    for n_data in data.get("nets", []):
        connected_blocks = []
        for b_name in n_data.get("blocks", []):
            if b_name in blocks_dict:
                connected_blocks.append(blocks_dict[b_name])
        nets.append(Net(name=n_data["name"], connected_blocks=connected_blocks))
        
    return Floorplan(blocks=list(blocks_dict.values()), nets=nets)