import tkinter as tk
from app.core.models import Floorplan
from app.metrics.cost import calculate_total_cost

class Visualizer:
    def __init__(self, master_window, initial_plan: Floorplan, start_cb=None):
        self.master = master_window
        self.master.title("SiliconMap - Live Optimization")
        self.plan = initial_plan
        
        # 1. Add a control panel with a button
        self.control_frame = tk.Frame(master_window)
        self.control_frame.pack(pady=10)
        
        if start_cb:
            self.btn_opt = tk.Button(self.control_frame, text="Run Optimizer", command=start_cb, font=("Arial", 14))
            self.btn_opt.pack()

        self.canvas = tk.Canvas(master_window, width=800, height=800, bg="white")
        self.canvas.pack()

        # 2. State variables for dragging
        self.selected_block = None
        self.drag_start_x = 0
        self.drag_start_y = 0

        # 3. Bind Mouse Events to the canvas
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.draw_floorplan(self.plan, calculate_total_cost(self.plan))

    def on_mouse_down(self, event):
        offset_x, offset_y = 200, 200
        # Iterate in reverse so if blocks overlap, you grab the one on top
        for block in reversed(self.plan.blocks):
            x1 = block.x + offset_x
            y1 = block.y + offset_y
            x2 = x1 + block.width
            y2 = y1 + block.height
            
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.selected_block = block
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                break

    def on_mouse_drag(self, event):
        if self.selected_block:
            # Calculate how far the mouse moved
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            
            # Move the block
            self.selected_block.x += dx
            self.selected_block.y += dy
            
            # Reset start position for the next frame of the drag
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            
            # Live update the UI and cost while dragging
            live_cost = calculate_total_cost(self.plan)
            self.draw_floorplan(self.plan, cost=live_cost, temp=0.0)

    def on_mouse_up(self, event):
        self.selected_block = None

    def draw_floorplan(self, floorplan: Floorplan, cost: float = 0.0, temp: float = 0.0):
        self.plan = floorplan # Update internal reference
        self.canvas.delete("all")
        offset_x, offset_y = 200, 200
        
        # Draw Wires
        for net in floorplan.nets:
            if len(net.connected_blocks) >= 2:
                for i in range(len(net.connected_blocks) - 1):
                    b1 = net.connected_blocks[i]
                    b2 = net.connected_blocks[i+1]
                    x1 = b1.x + offset_x + (b1.width / 2)
                    y1 = b1.y + offset_y + (b1.height / 2)
                    x2 = b2.x + offset_x + (b2.width / 2)
                    y2 = b2.y + offset_y + (b2.height / 2)
                    self.canvas.create_line(x1, y1, x2, y2, fill="gray", dash=(4, 4))
        
        # Draw Blocks
        for block in floorplan.blocks:
            x1 = block.x + offset_x
            y1 = block.y + offset_y
            x2 = x1 + block.width
            y2 = y1 + block.height
            
            # Highlight the block in red if you are currently dragging it
            outline_color = "red" if block == self.selected_block else "blue"
            line_width = 3 if block == self.selected_block else 2
            
            self.canvas.create_rectangle(x1, y1, x2, y2, fill="#ADD8E6", outline=outline_color, width=line_width)
            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=block.name)
            
        self.canvas.create_text(400, 30, text=f"Cost: {cost:.2f}  |  Temp: {temp:.2f}", font=("Arial", 16))
        self.master.update()