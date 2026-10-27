import tkinter as tk
from tkinter import filedialog, messagebox
from app.core.models import Floorplan
from app.core.feasibility import check_feasibility
from app.algorithms.annealing import SimulatedAnnealer
from app.ui.visualizer import Visualizer
from app.ui.dialogs import ask_chip_size
from app.core.parser import load_floorplan_from_json


def main():
    root = tk.Tk()
    root.withdraw()                                   # hide the main window while asking for the chip size
    chip_w, chip_h = ask_chip_size(root)
    root.deiconify()
    current_floorplan = Floorplan(blocks=[], nets=[], chip_width=chip_w, chip_height=chip_h)

    def on_update(current_plan, current_cost, current_temp, iteration):
        ui.draw_floorplan(current_plan, current_cost, current_temp, iteration)

    def start_optimization():
        if ui.running:
            return
        if not ui.plan.blocks:
            messagebox.showinfo("Nothing to optimize", "Add at least one component first.")
            return
        params = ui.get_optimizer_params()
        if params is None or not ui.apply_chip_size():
            return
        init_temp, cooling, iterations, allow_rotation = params

        # Can these components physically fit on this die?
        feas = check_feasibility(ui.plan.blocks, ui.plan.chip_width, ui.plan.chip_height, allow_rotation)
        if not feas.ok:
            side = feas.suggested_side
            text = (f"The chip dimension is not sufficient to accommodate these components.\n\n{feas.message()}\n\n"
                    f"Expand the die to {side} \u00d7 {side} \u03bcm?")
            if feas.hard_fail:
                if not messagebox.askyesno("Dimension not sufficient", text):
                    return
                expand = True
            else:
                answer = messagebox.askyesnocancel("Dimension may be insufficient",
                                                   text + "\n\nYes = expand   |   No = try anyway   |   Cancel = stop")
                if answer is None:
                    return
                expand = answer
            if expand:
                ui.resize_chip(side, side)

        ui.set_running(True)
        ui.reset_plot()
        try:
            SimulatedAnnealer(initial_temp=init_temp, cooling_rate=cooling, allow_rotation=allow_rotation) \
                .optimize(ui.plan, iterations=iterations, update_callback=on_update)
        except tk.TclError:
            return                                    # window was closed mid-run
        ui.set_running(False)
        ui.refresh()
        ui.show_metrics()

    def load_file():
        if ui.running:
            return
        filepath = filedialog.askopenfilename(title="Select Chip Layout",
                                              filetypes=(("JSON files", "*.json"), ("All files", "*.*")))
        if filepath:
            try:
                ui.set_new_floorplan(load_floorplan_from_json(filepath))
            except (ValueError, OSError) as e:
                messagebox.showerror("Could not load layout", str(e))

    ui = Visualizer(root, current_floorplan, start_cb=start_optimization, load_cb=load_file)
    root.mainloop()


if __name__ == "__main__":
    main()
