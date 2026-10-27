import json
from app.core.models import Block, Net, Floorplan
from app.core.library import kind_of, default_power


def load_floorplan_from_json(filepath: str) -> Floorplan:
    """Load a floorplan. Raises ValueError with a readable message on bad input."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Not a valid JSON file: {e}")

    blocks_dict = {}
    for b_data in data.get("blocks", []):
        try:
            name = str(b_data["name"])
            width, height = float(b_data["width"]), float(b_data["height"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Every block needs a 'name', 'width' and 'height'.")
        if width <= 0 or height <= 0:
            raise ValueError(f"Block {name} has a non-positive size.")
        if name in blocks_dict:
            raise ValueError(f"Duplicate block name: {name}")
        blocks_dict[name] = Block(
            name=name, width=width, height=height,
            x=float(b_data.get("x", 0.0)), y=float(b_data.get("y", 0.0)),
            power_watts=float(b_data.get("power_watts", default_power(name))),
            kind=b_data.get("kind", kind_of(name)),
        )

    nets = []
    for n_data in data.get("nets", []):
        connected = [blocks_dict[n] for n in n_data.get("blocks", []) if n in blocks_dict]
        nets.append(Net(name=n_data["name"], connected_blocks=connected))

    chip_w = float(data.get("chip_width", 400.0))
    chip_h = float(data.get("chip_height", 400.0))
    if chip_w <= 0 or chip_h <= 0:
        raise ValueError("Chip dimensions must be positive.")
    return Floorplan(blocks=list(blocks_dict.values()), nets=nets, chip_width=chip_w, chip_height=chip_h)
