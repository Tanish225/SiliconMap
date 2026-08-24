import tkinter as tk
from app.core.models import Floorplan

class Visualizer:
    def __init__(self, master_window, initial_plan: Floorplan):
        self.master = master_window
        self.master.title("SiliconMap - Live Optimization")
        
        # Create an 800x800 canvas
        self.canvas = tk.Canvas(master_window, width=800, height=800, bg="white")
        self.canvas.pack()
        
        self.draw_floorplan(initial_plan)

    def draw_floorplan(self, floorplan: Floorplan, cost: float = 0.0, temp: float = 0.0):
        # Clear the previous drawing
        self.canvas.delete("all")
        
        # Offset so blocks aren't stuck against the top-left edge
        offset_x, offset_y = 200, 200
        
        # Draw the wires (Nets) first so they stay behind the blocks
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
        
        # Draw the Blocks
        for block in floorplan.blocks:
            x1 = block.x + offset_x
            y1 = block.y + offset_y
            x2 = x1 + block.width
            y2 = y1 + block.height
            
            self.canvas.create_rectangle(x1, y1, x2, y2, fill="#ADD8E6", outline="blue", width=2)
            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=block.name)
            
        # Draw the stats
        self.canvas.create_text(400, 30, text=f"Cost: {cost:.2f}  |  Temp: {temp:.2f}", font=("Arial", 16))
        
        # Force the UI to refresh immediately
        self.master.update()