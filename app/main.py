import tkinter as tk
from tkinter import filedialog
from app.core.models import Floorplan
from app.algorithms.annealing import SimulatedAnnealer
from app.ui.visualizer import Visualizer
from app.core.parser import load_floorplan_from_json

def main():
    root = tk.Tk()
    
    # Start with an empty floorplan
    current_floorplan = Floorplan(blocks=[], nets=[])
    
    def on_update(current_plan, current_cost, current_temp, iteration):
        ui.draw_floorplan(current_plan, current_cost, current_temp, iteration)

    def start_optimization():
        ui.btn_opt.config(state=tk.DISABLED, text="Optimizing...")
        ui.reset_plot()
        optimizer = SimulatedAnnealer(initial_temp=5000.0, cooling_rate=0.999)
        optimizer.optimize(current_floorplan, iterations=15000, update_callback=on_update)
        ui.btn_opt.config(state=tk.NORMAL, text="Run Optimizer")

    def load_file():
        nonlocal current_floorplan
        filepath = filedialog.askopenfilename(
            title="Select Chip Layout",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )
        if filepath:
            current_floorplan = load_floorplan_from_json(filepath)
            ui.set_new_floorplan(current_floorplan)

    # Pass both callbacks to the Visualizer
    ui = Visualizer(root, current_floorplan, start_cb=start_optimization, load_cb=load_file)

    root.mainloop()

if __name__ == "__main__":
    main()