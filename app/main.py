from app.core.models import Block, Net, Floorplan
from app.metrics.cost import calculate_total_cost
from app.algorithms.annealing import SimulatedAnnealer

def main():
    # 1. Create dummy blocks spread far apart (terrible initial placement)
    alu = Block("ALU", width=40, height=30, x=0, y=0)
    reg = Block("REG", width=20, height=20, x=200, y=200)
    cache = Block("CACHE", width=50, height=40, x=100, y=500)
    mux = Block("MUX", width=15, height=10, x=400, y=100)
    ctrl = Block("CTRL", width=20, height=15, x=500, y=300)

    # 2. Define the wires connecting them
    nets = [
        Net("ALU_to_REG", [alu, reg]),
        Net("ALU_to_MUX", [alu, mux]),
        Net("REG_to_CACHE", [reg, cache]),
        Net("MUX_to_CTRL", [mux, ctrl])
    ]

    # 3. Assemble the chip floorplan
    floorplan = Floorplan(blocks=[alu, reg, cache, mux, ctrl], nets=nets)

    print("--- SILICONMAP: VLSI PLACEMENT OPTIMIZER ---")
    
    # 4. Check the initial cost
    initial_cost = calculate_total_cost(floorplan)
    print(f"Initial Wirelength Cost: {initial_cost:.2f} µm")

    # 5. Run the Simulated Annealing optimizer
    print("\nOptimizing...")
    optimizer = SimulatedAnnealer(initial_temp=1000.0, cooling_rate=0.99)
    
    # Running 10,000 iterations takes a fraction of a second without a UI
    optimized_plan = optimizer.optimize(floorplan, iterations=10000)

    # 6. Check the final cost
    final_cost = calculate_total_cost(optimized_plan)
    print(f"Final Wirelength Cost: {final_cost:.2f} µm")
    
    if initial_cost > 0:
        improvement = ((initial_cost - final_cost) / initial_cost) * 100
        print(f"Improvement: {improvement:.1f}%\n")

    # 7. Print final coordinates to see where they ended up
    print("Final Block Positions:")
    for b in optimized_plan.blocks:
        print(f"  {b.name}: (x: {b.x:.1f}, y: {b.y:.1f})")

if __name__ == "__main__":
    main()