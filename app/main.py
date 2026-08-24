import tkinter as tk
from app.core.models import Block, Net, Floorplan
from app.algorithms.annealing import SimulatedAnnealer
from app.ui.visualizer import Visualizer

def main():
    # 1. Setup blocks (scaled up slightly so they are easier to see on screen)
    alu = Block("ALU", width=80, height=60, x=0, y=0)
    reg = Block("REG", width=40, height=40, x=300, y=300)
    cache = Block("CACHE", width=100, height=80, x=100, y=500)
    mux = Block("MUX", width=30, height=20, x=400, y=100)
    ctrl = Block("CTRL", width=40, height=30, x=500, y=300)

    nets = [
        Net("ALU_to_REG", [alu, reg]),
        Net("ALU_to_MUX", [alu, mux]),
        Net("REG_to_CACHE", [reg, cache]),
        Net("MUX_to_CTRL", [mux, ctrl])
    ]

    floorplan = Floorplan(blocks=[alu, reg, cache, mux, ctrl], nets=nets)

    # 2. Setup the UI Window
    root = tk.Tk()
    ui = Visualizer(root, floorplan)

    # 3. Define what happens when the optimizer pings the UI
    def on_update(current_plan, current_cost, current_temp):
        ui.draw_floorplan(current_plan, current_cost, current_temp)

    # 4. Start the optimization!
    optimizer = SimulatedAnnealer(initial_temp=5000.0, cooling_rate=0.999)
    
    # We delay the start by 1 second so you can see the terrible initial placement
    root.after(1000, lambda: optimizer.optimize(floorplan, iterations=15000, update_callback=on_update))
    
    # 5. Keep the window open
    root.mainloop()

if __name__ == "__main__":
    main()