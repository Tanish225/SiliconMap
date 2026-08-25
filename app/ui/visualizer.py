import tkinter as tk
from tkinter import messagebox
import json
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.core.models import Floorplan, Block, Net
from app.metrics.cost import calculate_total_cost

class Visualizer:
    def __init__(self, master_window, initial_plan: Floorplan, start_cb=None, load_cb=None):
        self.master = master_window
        self.master.title("SiliconMap - Advanced CAD Interface")
        self.master.geometry("1300x800") 
        self.plan = initial_plan
        
        self.zoom_factor = 1.0
        self.pan_x = 100.0
        self.pan_y = 100.0
        self.show_grid = tk.BooleanVar(value=True)
        self.is_panning = False
        
        self.main_frame = tk.Frame(master_window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.left_frame = tk.Frame(self.main_frame, width=200)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.center_frame = tk.Frame(self.main_frame)
        self.center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.right_frame = tk.Frame(self.main_frame, width=350)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        self.settings_frame = tk.LabelFrame(self.left_frame, text="Parameters & Dimensions", font=("Arial", 10, "bold"))
        self.settings_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(self.settings_frame, text="Initial Temp:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.temp_var = tk.StringVar(value="5000.0")
        tk.Entry(self.settings_frame, textvariable=self.temp_var, width=8).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(self.settings_frame, text="Cooling Rate:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.cooling_var = tk.StringVar(value="0.999")
        tk.Entry(self.settings_frame, textvariable=self.cooling_var, width=8).grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(self.settings_frame, text="Chip W (μm):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.chip_w_var = tk.StringVar(value=str(self.plan.chip_width))
        tk.Entry(self.settings_frame, textvariable=self.chip_w_var, width=8).grid(row=2, column=1, padx=5, pady=5)
        
        tk.Label(self.settings_frame, text="Chip H (μm):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.chip_h_var = tk.StringVar(value=str(self.plan.chip_height))
        tk.Entry(self.settings_frame, textvariable=self.chip_h_var, width=8).grid(row=3, column=1, padx=5, pady=5)
        
        self.toolbar_frame = tk.LabelFrame(self.left_frame, text="Add Components", font=("Arial", 10, "bold"))
        self.toolbar_frame.pack(fill=tk.X, pady=5)
        
        # STANDARD LIBRARY: (Name, Width, Height, Power/Heat)
        components = [
            ("ALU", 120, 100, 80.0),   
            ("REG", 60, 60, 10.0),     
            ("CACHE", 160, 120, 40.0), 
            ("MUX", 40, 40, 5.0),      
            ("CTRL", 80, 60, 30.0)     
        ]
        
        for name, w, h, pwr in components:
            tk.Button(self.toolbar_frame, text=f"+ {name}", 
                      command=lambda n=name, width=w, height=h, p=pwr: self.spawn_block(n, width, height, p)).pack(fill=tk.X, padx=5, pady=2)

        self.edit_frame = tk.LabelFrame(self.left_frame, text="Modify Selected", font=("Arial", 10, "bold"))
        self.edit_frame.pack(fill=tk.X, pady=5)
        tk.Button(self.edit_frame, text="🔗 Connect To...", command=self.open_connect_dialog).pack(fill=tk.X, padx=5, pady=2)
        tk.Button(self.edit_frame, text="🗑 Delete (Del)", command=self.delete_selected).pack(fill=tk.X, padx=5, pady=2)

        self.action_frame = tk.LabelFrame(self.left_frame, text="Actions", font=("Arial", 10, "bold"))
        self.action_frame.pack(fill=tk.X, pady=5)
        if load_cb: tk.Button(self.action_frame, text="📂 Load JSON", command=load_cb).pack(fill=tk.X, padx=5, pady=2)
        if start_cb:
            self.btn_opt = tk.Button(self.action_frame, text="▶ Run Optimizer", command=start_cb)
            self.btn_opt.pack(fill=tk.X, padx=5, pady=2)
        tk.Button(self.action_frame, text="💾 Save Results", command=self.export_results).pack(fill=tk.X, padx=5, pady=2)

        self.view_controls = tk.Frame(self.center_frame)
        self.view_controls.pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(self.view_controls, text="➕ Zoom In", command=lambda: self.apply_zoom(1.2)).pack(side=tk.LEFT, padx=2)
        tk.Button(self.view_controls, text="➖ Zoom Out", command=lambda: self.apply_zoom(0.8)).pack(side=tk.LEFT, padx=2)
        tk.Button(self.view_controls, text="🎯 Center View", command=self.center_view).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(self.view_controls, text="Show Grid", variable=self.show_grid, 
                       command=lambda: self.draw_floorplan(self.plan)).pack(side=tk.LEFT, padx=10)

        self.canvas = tk.Canvas(self.center_frame, bg="#fafafa", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.graph_frame = tk.LabelFrame(self.right_frame, text="Real-Time Analytics", font=("Arial", 10, "bold"))
        self.graph_frame.pack(fill=tk.BOTH, expand=True)
        self.algo_label = tk.Label(self.right_frame, text="Algorithm: Simulated Annealing", font=("Arial", 10, "italic"), fg="gray")
        self.algo_label.pack(side=tk.BOTTOM, pady=10, anchor="e")

        self.fig = Figure(figsize=(4, 6), dpi=100)
        self.ax_cost = self.fig.add_subplot(211)
        self.ax_cost.set_title("Cost vs Iterations", fontsize=10)
        self.ax_cost.set_ylabel("Cost")
        self.ax_temp = self.fig.add_subplot(212)
        self.ax_temp.set_title("Temperature vs Iterations", fontsize=10)
        self.ax_temp.set_xlabel("Iterations")
        self.ax_temp.set_ylabel("Temperature")
        self.fig.tight_layout(pad=2.0)

        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.iterations_data, self.cost_data, self.temp_data = [], [], []
        self.selected_block = None
        self.drag_start_x = self.drag_start_y = 0
        
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Configure>", lambda e: self.draw_floorplan(self.plan))
        self.master.bind("<Delete>", self.delete_selected)
        self.master.bind("<BackSpace>", self.delete_selected)

        self.draw_floorplan(self.plan, calculate_total_cost(self.plan))

    def delete_selected(self, event=None):
        if self.selected_block:
            self.plan.blocks.remove(self.selected_block)
            for net in self.plan.nets:
                if self.selected_block in net.connected_blocks:
                    net.connected_blocks.remove(self.selected_block)
            self.plan.nets = [n for n in self.plan.nets if len(n.connected_blocks) > 1]
            self.selected_block = None
            self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))

    def open_connect_dialog(self):
        if not self.selected_block:
            messagebox.showwarning("Warning", "Please click a block to select it first!")
            return
            
        top = tk.Toplevel(self.master)
        top.title("Connect Blocks")
        top.geometry("250x150")
        tk.Label(top, text=f"Connect {self.selected_block.name} to:").pack(pady=10)
        
        options = [b.name for b in self.plan.blocks if b != self.selected_block]
        if not options: return
            
        selected_target = tk.StringVar(value=options[0])
        tk.OptionMenu(top, selected_target, *options).pack(pady=5)
        
        def make_connection():
            target_name = selected_target.get()
            target_block = next((b for b in self.plan.blocks if b.name == target_name), None)
            if target_block:
                self.plan.nets.append(Net(name=f"{self.selected_block.name}_to_{target_block.name}", connected_blocks=[self.selected_block, target_block]))
                self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))
            top.destroy()
            
        tk.Button(top, text="Create Wire", command=make_connection).pack(pady=10)

    def apply_zoom(self, factor):
        self.zoom_factor *= factor
        self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))

    def center_view(self):
        if not self.plan.blocks:
            self.pan_x, self.pan_y = 100.0, 100.0
            self.zoom_factor = 1.0
        else:
            min_x = min(b.x for b in self.plan.blocks)
            max_x = max(b.x + b.width for b in self.plan.blocks)
            min_y = min(b.y for b in self.plan.blocks)
            max_y = max(b.y + b.height for b in self.plan.blocks)
            center_x, center_y = (min_x + max_x) / 2, (min_y + max_y) / 2
            
            self.zoom_factor = 1.0
            canvas_w = self.canvas.winfo_width() if self.canvas.winfo_width() > 10 else 600
            canvas_h = self.canvas.winfo_height() if self.canvas.winfo_height() > 10 else 600
            
            self.pan_x = (canvas_w / 2) - center_x
            self.pan_y = (canvas_h / 2) - center_y
        self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))

    def get_initial_temp(self) -> float:
        try: return float(self.temp_var.get())
        except ValueError: return 5000.0

    def get_cooling_rate(self) -> float:
        try: return float(self.cooling_var.get())
        except ValueError: return 0.999
        
    def sync_chip_dimensions(self):
        try:
            self.plan.chip_width = float(self.chip_w_var.get())
            self.plan.chip_height = float(self.chip_h_var.get())
        except ValueError:
            self.plan.chip_width = 400.0
            self.plan.chip_height = 400.0

    def set_new_floorplan(self, new_plan: Floorplan):
        self.plan = new_plan
        self.chip_w_var.set(str(self.plan.chip_width))
        self.chip_h_var.set(str(self.plan.chip_height))
        self.reset_plot()
        self.center_view()

    def reset_plot(self):
        self.iterations_data.clear()
        self.cost_data.clear()
        self.temp_data.clear()
        self.ax_cost.clear()
        self.ax_cost.set_title("Cost vs Iterations", fontsize=10)
        self.ax_cost.set_ylabel("Cost")
        self.ax_temp.clear()
        self.ax_temp.set_title("Temperature vs Iterations", fontsize=10)
        self.ax_temp.set_xlabel("Iterations")
        self.ax_temp.set_ylabel("Temperature")
        self.plot_canvas.draw()

    def spawn_block(self, base_name: str, width: float, height: float, power_watts: float):
        count = sum(1 for b in self.plan.blocks if b.name.startswith(base_name))
        new_name = f"{base_name}_{count + 1}" if count > 0 else base_name
        
        spawn_world_x = ((self.canvas.winfo_width() / 2) - self.pan_x) / self.zoom_factor
        spawn_world_y = ((self.canvas.winfo_height() / 2) - self.pan_y) / self.zoom_factor
        
        new_block = Block(name=new_name, width=width, height=height, x=spawn_world_x, y=spawn_world_y, power_watts=power_watts)
        self.plan.blocks.append(new_block)
        
        self.selected_block = new_block
        self.draw_floorplan(self.plan, calculate_total_cost(self.plan))

    def export_results(self):
        try:
            export_data = {
                "chip_width": self.plan.chip_width,
                "chip_height": self.plan.chip_height,
                "blocks": [{"name": b.name, "x": round(b.x, 2), "y": round(b.y, 2), "width": b.width, "height": b.height} for b in self.plan.blocks],
                "nets": [{"name": n.name, "blocks": [b.name for b in n.connected_blocks]} for n in self.plan.nets]
            }
            with open("optimized_layout.json", "w") as f:
                json.dump(export_data, f, indent=4)
            self.fig.savefig("cost_graph.png")
            messagebox.showinfo("Success", "Saved 'optimized_layout.json' and 'cost_graph.png'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save files: {str(e)}")

    def on_mouse_down(self, event):
        self.drag_start_x, self.drag_start_y = event.x, event.y
        self.selected_block = None
        self.is_panning = False
        
        world_x = (event.x - self.pan_x) / self.zoom_factor
        world_y = (event.y - self.pan_y) / self.zoom_factor
        
        for block in reversed(self.plan.blocks):
            if block.x <= world_x <= block.x + block.width and block.y <= world_y <= block.y + block.height:
                self.selected_block = block
                self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))
                return
                
        self.is_panning = True
        self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))

    def on_mouse_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        if self.selected_block:
            self.selected_block.x += dx / self.zoom_factor
            self.selected_block.y += dy / self.zoom_factor
            self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))
        elif self.is_panning:
            self.pan_x += dx
            self.pan_y += dy
            self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))
            
        self.drag_start_x, self.drag_start_y = event.x, event.y

    def on_mouse_up(self, event):
        self.is_panning = False

    def draw_floorplan(self, floorplan: Floorplan, cost: float = 0.0, temp: float = 0.0, iteration: int = 0):
        self.plan = floorplan
        self.sync_chip_dimensions()
        self.canvas.delete("all")
        
        if self.show_grid.get():
            grid_spacing = 50 * self.zoom_factor
            w = self.canvas.winfo_width() if self.canvas.winfo_width() > 10 else 1200
            h = self.canvas.winfo_height() if self.canvas.winfo_height() > 10 else 800
            
            offset_x = self.pan_x % grid_spacing
            offset_y = self.pan_y % grid_spacing
            
            for i in range(int(w // grid_spacing) + 2):
                x = offset_x + (i * grid_spacing)
                self.canvas.create_line(x, 0, x, h, fill="#eaeaea")
            for i in range(int(h // grid_spacing) + 2):
                y = offset_y + (i * grid_spacing)
                self.canvas.create_line(0, y, w, y, fill="#eaeaea")
                
        chip_x1 = self.pan_x
        chip_y1 = self.pan_y
        chip_x2 = (self.plan.chip_width * self.zoom_factor) + self.pan_x
        chip_y2 = (self.plan.chip_height * self.zoom_factor) + self.pan_y
        
        self.canvas.create_rectangle(chip_x1, chip_y1, chip_x2, chip_y2, outline="black", width=2, dash=(8, 4))
        self.canvas.create_text(chip_x1, chip_y1 - 10, text="Chip Die Boundary (μm)", font=("Arial", 10, "italic", "bold"), anchor="sw")
        
        for net in floorplan.nets:
            if len(net.connected_blocks) >= 2:
                for i in range(len(net.connected_blocks) - 1):
                    b1, b2 = net.connected_blocks[i], net.connected_blocks[i+1]
                    x1 = (b1.x + b1.width/2) * self.zoom_factor + self.pan_x
                    y1 = (b1.y + b1.height/2) * self.zoom_factor + self.pan_y
                    x2 = (b2.x + b2.width/2) * self.zoom_factor + self.pan_x
                    y2 = (b2.y + b2.height/2) * self.zoom_factor + self.pan_y
                    self.canvas.create_line(x1, y1, x2, y2, fill="#a0a0a0", width=2, dash=(4, 4))
        
        for block in floorplan.blocks:
            x1 = (block.x) * self.zoom_factor + self.pan_x
            y1 = (block.y) * self.zoom_factor + self.pan_y
            x2 = (block.x + block.width) * self.zoom_factor + self.pan_x
            y2 = (block.y + block.height) * self.zoom_factor + self.pan_y
            
            outline = "#ff4757" if block == self.selected_block else "#2f3542"
            width = 4 if block == self.selected_block else 2
            self.canvas.create_rectangle(x1, y1, x2, y2, fill="#70a1ff", outline=outline, width=width)
            self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=block.name, font=("Arial", max(8, int(10*self.zoom_factor)), "bold"))
            
        self.canvas.create_text(10, 10, text=f"Cost: {cost:.2f} | Temp: {temp:.2f}", font=("Arial", 12, "bold"), anchor="nw", fill="black")
        
        if iteration > 0:
            self.iterations_data.append(iteration)
            self.cost_data.append(cost)
            self.temp_data.append(temp)
            
            self.ax_cost.clear()
            self.ax_cost.set_title("Cost vs Iterations", fontsize=10)
            self.ax_cost.set_ylabel("Cost")
            self.ax_cost.plot(self.iterations_data, self.cost_data, color="#1e90ff")
            
            self.ax_temp.clear()
            self.ax_temp.set_title("Temperature Decay", fontsize=10)
            self.ax_temp.set_xlabel("Iterations")
            self.ax_temp.set_ylabel("Temperature")
            self.ax_temp.plot(self.iterations_data, self.temp_data, color="#ff4757")
            
            self.plot_canvas.draw_idle() 
            
        self.master.update()