import random
import math
import copy
from app.core.models import Floorplan
from app.metrics.cost import calculate_total_cost

class SimulatedAnnealer:
    def __init__(self, initial_temp: float = 5000.0, cooling_rate: float = 0.999):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate

    def optimize(self, floorplan: Floorplan, iterations: int = 1000, update_callback=None) -> Floorplan:
        current_plan = copy.deepcopy(floorplan)
        best_plan = copy.deepcopy(floorplan)
        
        current_cost = calculate_total_cost(current_plan)
        best_cost = current_cost
        current_temp = self.initial_temp
        
        for i in range(iterations):
            if not current_plan.blocks:
                break
                
            block_idx = random.randint(0, len(current_plan.blocks) - 1)
            old_x = current_plan.blocks[block_idx].x
            old_y = current_plan.blocks[block_idx].y
            
            # Perturb
            current_plan.blocks[block_idx].x += random.uniform(-30, 30)
            current_plan.blocks[block_idx].y += random.uniform(-30, 30)
            
            new_cost = calculate_total_cost(current_plan)
            cost_diff = new_cost - current_cost
            
            if cost_diff < 0 or random.random() < math.exp(-cost_diff / max(current_temp, 0.0001)):
                current_cost = new_cost
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_plan = copy.deepcopy(current_plan)
            else:
                current_plan.blocks[block_idx].x = old_x
                current_plan.blocks[block_idx].y = old_y
                
            current_temp *= self.cooling_rate
            
            if update_callback and i % 50 == 0:
                update_callback(current_plan, current_cost, current_temp, i)
        
        # Apply the best results to the original object
        for i in range(len(best_plan.blocks)):
            floorplan.blocks[i].x = best_plan.blocks[i].x
            floorplan.blocks[i].y = best_plan.blocks[i].y
            
        if update_callback:
            update_callback(floorplan, best_cost, current_temp, iterations)
            
        return best_plan