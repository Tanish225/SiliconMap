# defines the actual physical objects on the chip

from dataclasses import dataclass, field
from typing import List

@dataclass
class Block:
    name: str
    width: float
    height: float
    x: float = 0.0
    y: float = 0.0

    def area(self) -> float:
        return self.width * self.height

@dataclass
class Net:
    """A wire connecting multiple blocks."""
    name: str
    connected_blocks: List[Block] = field(default_factory=list)

@dataclass
class Floorplan:
    """The overall chip containing all blocks and nets."""
    blocks: List[Block]
    nets: List[Net]
    
    def get_block(self, name: str) -> Block:
        for b in self.blocks:
            if b.name == name:
                return b
        raise ValueError(f"Block {name} not found")