import random
import math
import copy
from app.core.models import Floorplan
from app.core.feasibility import pack
from app.metrics.cost import calculate_total_cost, cost_breakdown


class SimulatedAnnealer:
    def __init__(self, initial_temp: float = 5000.0, cooling_rate: float = 0.999,
                 allow_rotation: bool = True):
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.allow_rotation = allow_rotation

    @staticmethod
    def _clamp(block, chip_w, chip_h):
        """Keep a block inside the die (if it is small enough to fit at all)."""
        if block.width <= chip_w:
            block.x = min(max(block.x, 0.0), chip_w - block.width)
        if block.height <= chip_h:
            block.y = min(max(block.y, 0.0), chip_h - block.height)

    def _seed_legal_layout(self, plan: Floorplan):
        """If the current layout is illegal (e.g. all blocks spawned on top of each
        other), start from a legal shelf-packed layout instead."""
        if cost_breakdown(plan)["legal"]:
            return
        placement = pack(plan.blocks, plan.chip_width, plan.chip_height, self.allow_rotation)
        if placement:
            for b in plan.blocks:
                x, y, w, h = placement[b.name]
                b.x, b.y, b.width, b.height = x, y, w, h

    def optimize(self, floorplan: Floorplan, iterations: int = 1000, update_callback=None) -> Floorplan:
        current_plan = copy.deepcopy(floorplan)
        self._seed_legal_layout(current_plan)
        best_plan = copy.deepcopy(current_plan)

        current_cost = calculate_total_cost(current_plan)
        best_cost = current_cost
        current_temp = self.initial_temp
        W, H = current_plan.chip_width, current_plan.chip_height
        max_step = 0.15 * max(W, H)
        n = len(current_plan.blocks)

        for i in range(iterations):
            if n == 0:
                break
            # Move size shrinks as the temperature falls (big jumps early, fine tuning late)
            frac = max(current_temp / self.initial_temp, 0.02)
            step = max(2.0, max_step * frac)

            move = random.random()
            if n > 1 and move < 0.15:
                # SWAP the positions of two blocks
                a, b = random.sample(range(n), 2)
                A, B = current_plan.blocks[a], current_plan.blocks[b]
                saved = [(A.x, A.y), (B.x, B.y)]
                A.x, A.y, B.x, B.y = B.x, B.y, A.x, A.y
                self._clamp(A, W, H); self._clamp(B, W, H)
                undo = lambda A=A, B=B, s=saved: (setattr(A, "x", s[0][0]), setattr(A, "y", s[0][1]),
                                                  setattr(B, "x", s[1][0]), setattr(B, "y", s[1][1]))
            elif self.allow_rotation and move < 0.25:
                # ROTATE one block by 90 degrees
                A = current_plan.blocks[random.randrange(n)]
                saved = (A.x, A.y)
                A.rotate()
                self._clamp(A, W, H)
                undo = lambda A=A, s=saved: (A.rotate(), setattr(A, "x", s[0]), setattr(A, "y", s[1]))
            else:
                # SHIFT one block
                A = current_plan.blocks[random.randrange(n)]
                saved = (A.x, A.y)
                A.x += random.uniform(-step, step)
                A.y += random.uniform(-step, step)
                self._clamp(A, W, H)
                undo = lambda A=A, s=saved: (setattr(A, "x", s[0]), setattr(A, "y", s[1]))

            new_cost = calculate_total_cost(current_plan)
            cost_diff = new_cost - current_cost

            if cost_diff < 0 or random.random() < math.exp(-cost_diff / max(current_temp, 0.0001)):
                current_cost = new_cost
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_plan = copy.deepcopy(current_plan)
            else:
                undo()

            current_temp *= self.cooling_rate

            if update_callback and i % 50 == 0:
                update_callback(current_plan, current_cost, current_temp, i)

        # Apply the best result (positions AND orientation) to the original object
        for i in range(len(best_plan.blocks)):
            src, dst = best_plan.blocks[i], floorplan.blocks[i]
            dst.x, dst.y, dst.width, dst.height = src.x, src.y, src.width, src.height

        if update_callback:
            update_callback(floorplan, best_cost, current_temp, iterations)

        return best_plan
