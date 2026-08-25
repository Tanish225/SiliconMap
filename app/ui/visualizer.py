import tkinter as tk
from tkinter import messagebox, filedialog
import json
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app.core.models import Floorplan, Block
from app.metrics.cost import calculate_total_cost

class Visualizer:
    def __init__(self, master_window, initial_plan: Floorplan, start_cb=None, load_cb=None):
        self.master = master_window
        self.master.title("SiliconMap - Advanced CAD Interface")
        self.master.geometry("1200x800")
        self.plan = initial_plan
        
        # --- CAMERA STATE ---
        self.zoom_factor = 1.0
        self.pan_x = 100.0
        self.pan_y = 100.0
        self.show_grid = tk.BooleanVar(value=True)
        self.is_panning = False
        
        # --- LAYOUT SETUP ---
        self.main_frame = tk.Frame(master_window)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.left_frame = tk.Frame(self.main_frame, width=200)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.center_frame = tk.Frame(self.main_frame)
        self.center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.right_frame = tk.Frame(self.main_frame, width=300)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # --- LEFT PANEL: CONTROLS ---
        self.settings_frame = tk.LabelFrame(self.left_frame, text="Algorithm Parameters", font=("Arial", 10, "bold"))
        self.settings_frame.pack(fill=tk.X, pady=5)
        tk.Label(self.settings_frame, text="Initial Temp:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.temp_var = tk.StringVar(value="5000.0")
        tk.Entry(self.settings_frame, textvariable=self.temp_var, width=8).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self.settings_frame, text="Cooling Rate:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.cooling_var = tk.StringVar(value="0.999")
        tk.Entry(self.settings_frame, textvariable=self.cooling_var, width=8).grid(row=1, column=1, padx=5, pady=5)
        
        self.toolbar_frame = tk.LabelFrame(self.left_frame, text="Add Components", font=("Arial", 10, "bold"))
        self.toolbar_frame.pack(fill=tk.X, pady=5)
        components = [("ALU", 80, 60), ("REG", 40, 40), ("CACHE", 100, 80), ("MUX", 30, 20), ("CTRL", 40, 30)]
        for name, w, h in components:
            tk.Button(self.toolbar_frame, text=f"+ {name}", 
                      command=lambda n=name, width=w, height=h: self.spawn_block(n, width, height)).pack(fill=tk.X, padx=5, pady=2)

        self.action_frame = tk.LabelFrame(self.left_frame, text="Actions", font=("Arial", 10, "bold"))
        self.action_frame.pack(fill=tk.X, pady=5)
        if load_cb:
            tk.Button(self.action_frame, text="📂 Load JSON", command=load_cb).pack(fill=tk.X, padx=5, pady=2)
        if start_cb:
            self.btn_opt = tk.Button(self.action_frame, text="▶ Run Optimizer", command=start_cb, bg="#d4edda")
            self.btn_opt.pack(fill=tk.X, padx=5, pady=2)
        tk.Button(self.action_frame, text="💾 Save Results", command=self.export_results).pack(fill=tk.X, padx=5, pady=2)

        # --- CENTER PANEL: CANVAS & VIEW CONTROLS ---
        self.view_controls = tk.Frame(self.center_frame)
        self.view_controls.pack(fill=tk.X, pady=(0, 5))
        
        tk.Button(self.view_controls, text="➕ Zoom In", command=lambda: self.apply_zoom(1.2)).pack(side=tk.LEFT, padx=2)
        tk.Button(self.view_controls, text="➖ Zoom Out", command=lambda: self.apply_zoom(0.8)).pack(side=tk.LEFT, padx=2)
        tk.Button(self.view_controls, text="🎯 Center View", command=self.center_view).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(self.view_controls, text="Show Grid", variable=self.show_grid, 
                       command=lambda: self.draw_floorplan(self.plan)).pack(side=tk.LEFT, padx=10)

        self.canvas = tk.Canvas(self.center_frame, bg="#fafafa", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # --- RIGHT PANEL: GRAPH ---
        self.graph_frame = tk.LabelFrame(self.right_frame, text="Cost Optimization Analytics", font=("Arial", 10, "bold"))
        self.graph_frame.pack(fill=tk.BOTH, expand=True)

        self.fig = Figure(figsize=(4, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Iterations")
        self.ax.set_ylabel("Cost")
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.iterations_data = []
        self.cost_data = []

        # --- MOUSE BINDINGS ---
        self.selected_block = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        # Bind canvas resize to re-center dynamically if needed
        self.canvas.bind("<Configure>", lambda e: self.draw_floorplan(self.plan))

        self.draw_floorplan(self.plan, calculate_total_cost(self.plan))

    # --- CAMERA METHODS ---
    def apply_zoom(self, factor):
        self.zoom_factor *= factor
        self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))

    def center_view(self):
        """Calculates the bounding box of all blocks and centers the camera on it."""
        if not self.plan.blocks:
            self.pan_x, self.pan_y = 100.0, 100.0
            self.zoom_factor = 1.0
        else:
            min_x = min(b.x for b in self.plan.blocks)
            max_x = max(b.x + b.width for b in self.plan.blocks)
            min_y = min(b.y for b in self.plan.blocks)
            max_y = max(b.y + b.height for b in self.plan.blocks)
            
            center_x, center_y = (min_x + max_x) / 2, (min_y + max_y) / 2
            
            # Reset zoom to 1.0 and calculate pan needed to put the center of the blocks at the center of the canvas
            self.zoom_factor = 1.0
            canvas_w = self.canvas.winfo_width() if self.canvas.winfo_width() > 10 else 600
            canvas_h = self.canvas.winfo_height() if self.canvas.winfo_height() > 10 else 600
            
            self.pan_x = (canvas_w / 2) - center_x
            self.pan_y = (canvas_h / 2) - center_y
            
        self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))

    # --- HELPERS ---
    def get_initial_temp(self) -> float:
        try: return float(self.temp_var.get())
        except ValueError: return 5000.0

    def get_cooling_rate(self) -> float:
        try: return float(self.cooling_var.get())
        except ValueError: return 0.999

    def set_new_floorplan(self, new_plan: Floorplan):
        self.plan = new_plan
        self.reset_plot()
        self.center_view()

    def reset_plot(self):
        self.iterations_data.clear()
        self.cost_data.clear()
        self.ax.clear()
        self.ax.set_xlabel("Iterations")
        self.ax.set_ylabel("Cost")
        self.plot_canvas.draw()

    def spawn_block(self, base_name: str, width: float, height: float):
        count = sum(1 for b in self.plan.blocks if b.name.startswith(base_name))
        new_name = f"{base_name}_{count + 1}" if count > 0 else base_name
        
        # Spawn in the center of the current camera view
        spawn_world_x = ((self.canvas.winfo_width() / 2) - self.pan_x) / self.zoom_factor
        spawn_world_y = ((self.canvas.winfo_height() / 2) - self.pan_y) / self.zoom_factor
        
        new_block = Block(name=new_name, width=width, height=height, x=spawn_world_x, y=spawn_world_y)
        self.plan.blocks.append(new_block)
        self.draw_floorplan(self.plan, calculate_total_cost(self.plan))

    def export_results(self):
        try:
            export_data = {
                "blocks": [{"name": b.name, "x": round(b.x, 2), "y": round(b.y, 2), "width": b.width, "height": b.height} for b in self.plan.blocks],
                "nets": [{"name": n.name, "blocks": [b.name for b in n.connected_blocks]} for n in self.plan.nets]
            }
            with open("optimized_layout.json", "w") as f:
                json.dump(export_data, f, indent=4)
            self.fig.savefig("cost_graph.png")
            messagebox.showinfo("Success", "Saved 'optimized_layout.json' and 'cost_graph.png'")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save files: {str(e)}")

    # --- INTERACTIVITY & DRAWING ---
    def on_mouse_down(self, event):
        self.drag_start_x, self.drag_start_y = event.x, event.y
        self.selected_block = None
        self.is_panning = False
        
        # Convert screen click to world coordinates to check intersection
        world_x = (event.x - self.pan_x) / self.zoom_factor
        world_y = (event.y - self.pan_y) / self.zoom_factor
        
        for block in reversed(self.plan.blocks):
            if block.x <= world_x <= block.x + block.width and block.y <= world_y <= block.y + block.height:
                self.selected_block = block
                return
                
        # If no block was clicked, we are panning the camera
        self.is_panning = True

    def on_mouse_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        if self.selected_block:
            # Move block (scale movement by zoom factor)
            self.selected_block.x += dx / self.zoom_factor
            self.selected_block.y += dy / self.zoom_factor
            self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))
        elif self.is_panning:
            # Move camera
            self.pan_x += dx
            self.pan_y += dy
            self.draw_floorplan(self.plan, cost=calculate_total_cost(self.plan))
            
        self.drag_start_x, self.drag_start_y = event.x, event.y

    def on_mouse_up(self, event):
        self.selected_block = None
        self.is_panning = False

    def draw_floorplan(self, floorplan: Floorplan, cost: float = 0.0, temp: float = 0.0, iteration: int = 0):
        self.plan = floorplan
        self.canvas.delete("all")
        
        # Draw Background Grid
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
        
        # Draw Wires
        for net in floorplan.nets:
            if len(net.connected_blocks) >= 2:
                for i in range(len(net.connected_blocks) - 1):
                    b1, b2 = net.connected_blocks[i], net.connected_blocks[i+1]
                    
                    x1 = (b1.x + b1.width/2) * self.zoom_factor + self.pan_x
                    y1 = (b1.y + b1.height/2) * self.zoom_factor + self.pan_y
                    x2 = (b2.x + b2.width/2) * self.zoom_factor + self.pan_x
                    y2 = (b2.y + b2.height/2) * self.zoom_factor + self.pan_y
                    
                    self.canvas.create_line(x1, y1, x2, y2, fill="#a0a0a0", width=2, dash=(4, 4))
        
        # Draw Blocks
        for block in floorplan.blocks:
            x1 = (block.x) * self.zoom_factor + self.pan_x
            y1 = (block.y) * self.zoom_factor + self.pan_y
            x2 = (block.x + block.width) * self.zoom_factor + self.pan_x
            y2 = (block.y + block.height) * self.zoom_factor + self.pan_y
            
            outline = "#ff4757" if block == self.selected_block else "#2f3542"
            width = 3 if block == self.selected_block else 2
            self.canvas.create_rectangle(x1, y1, x2, y2, fill="#70a1ff", outline=outline, width=width)
            self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=block.name, font=("Arial", max(8, int(10*self.zoom_factor)), "bold"))
            
        # Draw HUD stats
        self.canvas.create_text(10, 10, text=f"Cost: {cost:.2f} | Temp: {temp:.2f}", font=("Arial", 12, "bold"), anchor="nw")
        
        # Update Graph
        if iteration > 0:
            self.iterations_data.append(iteration)
            self.cost_data.append(cost)
            self.ax.plot(self.iterations_data, self.cost_data, color="#1e90ff")
            self.plot_canvas.draw_idle() # draw_idle prevents UI freezing during rapid updates
            
        self.master.update()