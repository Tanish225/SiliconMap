import tkinter as tk
from app.core.models import Block, Net, Floorplan
from app.algorithms.annealing import SimulatedAnnealer
from app.ui.visualizer import Visualizer

def main():
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

    root = tk.Tk()
    
    # Callback for the UI to redraw during optimization
    def on_update(current_plan, current_cost, current_temp):
        ui.draw_floorplan(current_plan, current_cost, current_temp)

    # What happens when you click the new button
    def start_optimization():
        ui.btn_opt.config(state=tk.DISABLED, text="Optimizing...")
        optimizer = SimulatedAnnealer(initial_temp=5000.0, cooling_rate=0.999)
        optimizer.optimize(floorplan, iterations=15000, update_callback=on_update)
        ui.btn_opt.config(state=tk.NORMAL, text="Run Optimizer")

    # Pass the button command into the Visualizer
    ui = Visualizer(root, floorplan, start_cb=start_optimization)

    root.mainloop()

if __name__ == "__main__":
    main()