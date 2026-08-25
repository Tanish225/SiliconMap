import tkinter as tk
import math
from tkinter import filedialog, messagebox
from app.core.models import Floorplan
from app.algorithms.annealing import SimulatedAnnealer
from app.ui.visualizer import Visualizer
from app.core.parser import load_floorplan_from_json

def main():
    root = tk.Tk()
    current_floorplan = Floorplan(blocks=[], nets=[], chip_width=400.0, chip_height=400.0)
    
    def on_update(current_plan, current_cost, current_temp, iteration):
        ui.draw_floorplan(current_plan, current_cost, current_temp, iteration)

    def start_optimization():
        ui.sync_chip_dimensions()
        
        # Smart Capacity Check (Calculate packing density)
        total_block_area = sum(b.area() for b in ui.plan.blocks)
        chip_area = ui.plan.chip_width * ui.plan.chip_height
        
        # If blocks take up more than 60% of the space, packing is extremely difficult
        if total_block_area > chip_area * 0.6:
            if messagebox.askyesno("Capacity Warning", "The components are too large for this chip size.\n\nExpand the chip automatically for efficient thermal packing?"):
                # Resize to target a safe 40% density for routing and cooling
                new_side = math.sqrt(total_block_area / 0.4)
                ui.plan.chip_width = round(new_side)
                ui.plan.chip_height = round(new_side)
                ui.chip_w_var.set(str(ui.plan.chip_width))
                ui.chip_h_var.set(str(ui.plan.chip_height))
                ui.center_view()

        ui.btn_opt.config(state=tk.DISABLED, text="Optimizing...")
        ui.reset_plot()
        
        init_temp = ui.get_initial_temp()
        cooling = ui.get_cooling_rate()
        
        optimizer = SimulatedAnnealer(initial_temp=init_temp, cooling_rate=cooling)
        optimizer.optimize(ui.plan, iterations=15000, update_callback=on_update)
        
        ui.btn_opt.config(state=tk.NORMAL, text="▶ Run Optimizer")

    def load_file():
        filepath = filedialog.askopenfilename(
            title="Select Chip Layout",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )
        if filepath:
            loaded_plan = load_floorplan_from_json(filepath)
            ui.set_new_floorplan(loaded_plan)

    ui = Visualizer(root, current_floorplan, start_cb=start_optimization, load_cb=load_file)
    root.mainloop()

if __name__ == "__main__":
    main()