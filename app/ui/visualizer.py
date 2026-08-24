import tkinter as tk
from tkinter import messagebox
import json
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.core.models import Floorplan
from app.metrics.cost import calculate_total_cost

class Visualizer:
    def __init__(self, master_window, initial_plan: Floorplan, start_cb=None, load_cb=None):
        self.master = master_window
        self.master.title("SiliconMap - Live Optimization")
        self.plan = initial_plan
        
        self.main_frame = tk.Frame(master_window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        if load_cb:
            self.btn_load = tk.Button(self.left_frame, text="Load JSON File", command=load_cb, font=("Arial", 14))
            self.btn_load.pack(pady=5)
            
        # NEW: Settings Panel
        self.settings_frame = tk.LabelFrame(self.left_frame, text="Algorithm Parameters", font=("Arial", 12))
        self.settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(self.settings_frame, text="Initial Temp:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.temp_var = tk.StringVar(value="5000.0")
        tk.Entry(self.settings_frame, textvariable=self.temp_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(self.settings_frame, text="Cooling Rate:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.cooling_var = tk.StringVar(value="0.999")
        tk.Entry(self.settings_frame, textvariable=self.cooling_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        if start_cb:
            self.btn_opt = tk.Button(self.left_frame, text="Run Optimizer", command=start_cb, font=("Arial", 14))
            self.btn_opt.pack(pady=5)
            
        self.btn_export = tk.Button(self.left_frame, text="Save Results", command=self.export_results, font=("Arial", 14))
        self.btn_export.pack(pady=5)

        self.canvas = tk.Canvas(self.left_frame, width=600, height=600, bg="white")
        self.canvas.pack()

        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Cost vs Iterations")
        self.ax.set_xlabel("Iterations")
        self.ax.set_ylabel("Cost")
        
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.plot_canvas.get_tk_widget().pack()
        
        self.iterations_data = []
        self.cost_data = []

        self.selected_block = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.draw_floorplan(self.plan, calculate_total_cost(self.plan))

    # NEW: Helper methods to safely read the UI inputs (add these right below __init__)
    def get_initial_temp(self) -> float:
        try:
            return float(self.temp_var.get())
        except ValueError:
            return 5000.0  # Fallback if the user types letters by accident

    def get_cooling_rate(self) -> float:
        try:
            return float(self.cooling_var.get())
        except ValueError:
            return 0.999   # Fallback
        
    def set_new_floorplan(self, new_plan: Floorplan):
        self.plan = new_plan
        self.reset_plot()
        self.draw_floorplan(self.plan, calculate_total_cost(self.plan))

    def reset_plot(self):
        self.iterations_data.clear()
        self.cost_data.clear()
        self.ax.clear()
        self.ax.set_title("Cost vs Iterations")
        self.ax.set_xlabel("Iterations")
        self.ax.set_ylabel("Cost")
        self.plot_canvas.draw()

    # NEW: Export Logic
    def export_results(self):
        try:
            # Save Coordinates to JSON
            export_data = {
                "blocks": [
                    {
                        "name": b.name, 
                        "x": round(b.x, 2), 
                        "y": round(b.y, 2), 
                        "width": b.width, 
                        "height": b.height
                    } for b in self.plan.blocks
                ]
            }
            with open("optimized_layout.json", "w") as f:
                json.dump(export_data, f, indent=4)
                
            # Save Graph to PNG
            self.fig.savefig("cost_graph.png")
            
            messagebox.showinfo("Export Successful", "Saved 'optimized_layout.json' and 'cost_graph.png' to your SiliconMap folder!")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save files: {str(e)}")

    def on_mouse_down(self, event):
        offset_x, offset_y = 100, 100
        for block in reversed(self.plan.blocks):
            x1, y1 = block.x + offset_x, block.y + offset_y
            if x1 <= event.x <= x1 + block.width and y1 <= event.y <= y1 + block.height:
                self.selected_block = block
                self.drag_start_x, self.drag_start_y = event.x, event.y
                break

    def on_mouse_drag(self, event):
        if self.selected_block:
            self.selected_block.x += event.x - self.drag_start_x
            self.selected_block.y += event.y - self.drag_start_y
            self.drag_start_x, self.drag_start_y = event.x, event.y
            self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))

    def on_mouse_up(self, event):
        self.selected_block = None

    def draw_floorplan(self, floorplan: Floorplan, cost: float = 0.0, temp: float = 0.0, iteration: int = 0):
        self.plan = floorplan
        self.canvas.delete("all")
        offset_x, offset_y = 100, 100
        
        # Wires
        for net in floorplan.nets:
            if len(net.connected_blocks) >= 2:
                for i in range(len(net.connected_blocks) - 1):
                    b1, b2 = net.connected_blocks[i], net.connected_blocks[i+1]
                    self.canvas.create_line(
                        b1.x + offset_x + b1.width/2, b1.y + offset_y + b1.height/2,
                        b2.x + offset_x + b2.width/2, b2.y + offset_y + b2.height/2,
                        fill="gray", dash=(4, 4)
                    )
        
        # Blocks
        for block in floorplan.blocks:
            x1, y1 = block.x + offset_x, block.y + offset_y
            outline = "red" if block == self.selected_block else "blue"
            width = 3 if block == self.selected_block else 2
            self.canvas.create_rectangle(x1, y1, x1 + block.width, y1 + block.height, fill="#ADD8E6", outline=outline, width=width)
            self.canvas.create_text(x1 + block.width/2, y1 + block.height/2, text=block.name)
            
        self.canvas.create_text(300, 30, text=f"Cost: {cost:.2f}  |  Temp: {temp:.2f}", font=("Arial", 16))
        
        if iteration > 0:
            self.iterations_data.append(iteration)
            self.cost_data.append(cost)
            self.ax.plot(self.iterations_data, self.cost_data, color="blue")
            self.plot_canvas.draw()
            
        self.master.update()