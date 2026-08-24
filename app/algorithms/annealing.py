# It will randomly shift blocks around, check the new cost, and decide whether to keep the move based on the "temperature".
import math
import random
import copy
from app.core.models import Floorplan
from app.metrics.cost import calculate_total_cost

class SimulatedAnnealer:
    def __init__(self, initial_temp: float = 1000.0, cooling_rate: float = 0.95):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate

    def optimize(self, floorplan: Floorplan, iterations: int = 1000) -> Floorplan:
        current_temp = self.initial_temp
        
        # Deep copy to avoid modifying the original until we are sure
        best_plan = copy.deepcopy(floorplan)
        current_plan = copy.deepcopy(floorplan)
        
        best_cost = calculate_total_cost(best_plan)
        current_cost = best_cost
        
        for i in range(iterations):
            # 1. Pick a random block and perturb it
            block_to_move = random.choice(current_plan.blocks)
            old_x, old_y = block_to_move.x, block_to_move.y
            
            # Move randomly within a small radius
            block_to_move.x += random.uniform(-10, 10)
            block_to_move.y += random.uniform(-10, 10)
            
            # 2. Calculate new cost
            new_cost = calculate_total_cost(current_plan)
            delta_cost = new_cost - current_cost
            
            # 3. Decide whether to accept the move
            if delta_cost < 0:
                # Better cost: always accept
                current_cost = new_cost
                if new_cost < best_cost:
                    best_cost = new_cost
                    best_plan = copy.deepcopy(current_plan)
            else:
                # Worse cost: maybe accept based on temperature
                probability = math.exp(-delta_cost / current_temp)
                if random.random() < probability:
                    current_cost = new_cost # Accepted!
                else:
                    # Rejected: revert the move
                    block_to_move.x, block_to_move.y = old_x, old_y
            
            # 4. Cool down
            current_temp *= self.cooling_rate
            
        return best_plan