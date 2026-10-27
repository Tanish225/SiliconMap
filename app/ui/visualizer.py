import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.core.models import Floorplan, Block, Net
from app.core.library import COMPONENT_LIBRARY, colour_of, kind_of
from app.core.feasibility import check_feasibility
from app.metrics.cost import cost_breakdown, calculate_overlap_area
from app.ui.dialogs import ask_custom_block, MIN_DIM, MAX_DIM

BG, PANEL, DARK = "#f4f6f8", "#ffffff", "#1f2d3d"
ACCENT, DANGER, OKAY, WARN = "#0984e3", "#d63031", "#00b894", "#e17055"
MIN_BLOCK = 5.0
HANDLE = 9


class Visualizer:
    def __init__(self, master_window, initial_plan: Floorplan, start_cb=None, load_cb=None):
        self.master = master_window
        self.master.title("SiliconMap - VLSI Placement Optimizer")
        self.master.geometry("1360x820")
        self.master.minsize(1100, 680)
        self.master.configure(bg=BG)
        self.plan = initial_plan

        self.zoom, self.pan_x, self.pan_y = 1.0, 40.0, 40.0
        self.show_grid = tk.BooleanVar(value=True)
        self.show_heat = tk.BooleanVar(value=False)
        self.rotation_var = tk.BooleanVar(value=True)
        self.selected_block = None
        self.mode = None            # "move" | "resize" | "pan"
        self.running = False
        self._fitted = False
        self.iterations_data, self.cost_data, self.temp_data = [], [], []

        self._style()
        self._build_header()
        body = tk.Frame(self.master, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 0))
        self._build_left(body)
        self._build_right(body)
        self._build_center(body, start_cb, load_cb)
        self._build_status()
        self._bind_events()
        self.load_form()
        self.refresh()

    # ------------------------------------------------------------------ styling / layout
    def _style(self):
        s = ttk.Style(self.master)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", background=BG, font=("Segoe UI", 9))
        s.configure("TLabel", background=BG, foreground=DARK)
        s.configure("TFrame", background=BG)
        s.configure("TLabelframe", background=BG, bordercolor="#dfe6e9")
        s.configure("TLabelframe.Label", background=BG, foreground=DARK, font=("Segoe UI", 9, "bold"))
        s.configure("TCheckbutton", background=BG, foreground=DARK)
        s.configure("TNotebook", background=BG)
        s.configure("TNotebook.Tab", padding=(14, 6))
        s.configure("TButton", padding=5)
        s.configure("Accent.TButton", background=ACCENT, foreground="white", font=("Segoe UI", 10, "bold"), padding=7)
        s.map("Accent.TButton", background=[("active", "#0773c5"), ("disabled", "#b2bec3")])
        s.configure("Danger.TButton", foreground=DANGER)

    def _build_header(self):
        bar = tk.Frame(self.master, bg=DARK, height=46)
        bar.pack(fill=tk.X)
        tk.Label(bar, text="\u25a6  SiliconMap", bg=DARK, fg="white", font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Label(bar, text="VLSI placement optimizer  \u2022  simulated annealing", bg=DARK, fg="#b2bec3",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

    def _build_left(self, parent):
        left = ttk.Frame(parent, width=310)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)
        nb = ttk.Notebook(left)
        nb.pack(fill=tk.BOTH, expand=True)
        tab_build, tab_setup = ttk.Frame(nb, padding=6), ttk.Frame(nb, padding=6)
        nb.add(tab_build, text="Components")
        nb.add(tab_setup, text="Chip & Run")

        # --- component library
        lib = ttk.LabelFrame(tab_build, text="Component library", padding=6)
        lib.pack(fill=tk.X)
        grid = tk.Frame(lib, bg=BG)
        grid.pack(fill=tk.X)
        grid.columnconfigure((0, 1), weight=1, uniform="lib")
        self.hint_var = tk.StringVar(value="Click a component to add it to the die")
        for i, (kind, (w, h, p, col)) in enumerate(COMPONENT_LIBRARY.items()):
            b = tk.Button(grid, text=kind, bg=col, activebackground=col, relief="flat", bd=0, cursor="hand2",
                          font=("Segoe UI", 9, "bold"), command=lambda k=kind: self.spawn_kind(k))
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2, ipady=3)
            b.bind("<Enter>", lambda e, k=kind, w=w, h=h, p=p: self.hint_var.set(f"{k}: {w} \u00d7 {h} \u03bcm, {p:g} W"))
            b.bind("<Leave>", lambda e: self.hint_var.set("Click a component to add it to the die"))
        ttk.Label(lib, textvariable=self.hint_var, foreground="#636e72").pack(anchor="w", pady=(4, 2))
        ttk.Button(lib, text="\uff0b Custom component...", command=self.add_custom).pack(fill=tk.X, pady=(2, 0))

        # --- selected block editor
        sel = ttk.LabelFrame(tab_build, text="Selected block", padding=6)
        sel.pack(fill=tk.X, pady=(8, 0))
        self.name_var, self.w_var, self.h_var, self.p_var = (tk.StringVar() for _ in range(4))
        self.form_entries = []
        for r, (text, var) in enumerate([("Name", self.name_var), ("Width (\u03bcm)", self.w_var),
                                         ("Height (\u03bcm)", self.h_var), ("Power (W)", self.p_var)]):
            ttk.Label(sel, text=text).grid(row=r, column=0, sticky="e", padx=4, pady=3)
            e = ttk.Entry(sel, textvariable=var, width=12)
            e.grid(row=r, column=1, sticky="ew", pady=3)
            e.bind("<Return>", lambda ev: self.apply_selected_edits())
            self.form_entries.append(e)
        sel.columnconfigure(1, weight=1)
        self.btn_apply = ttk.Button(sel, text="Apply changes", command=self.apply_selected_edits)
        self.btn_apply.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        row = ttk.Frame(sel)
        row.grid(row=5, column=0, columnspan=2, sticky="ew")
        row.columnconfigure((0, 1, 2), weight=1, uniform="a")
        self.btn_rot = ttk.Button(row, text="Rotate", command=self.rotate_selected)
        self.btn_con = ttk.Button(row, text="Connect", command=self.open_connect_dialog)
        self.btn_del = ttk.Button(row, text="Delete", style="Danger.TButton", command=self.delete_selected)
        for c, b in enumerate((self.btn_rot, self.btn_con, self.btn_del)):
            b.grid(row=0, column=c, sticky="ew", padx=1)
        ttk.Label(sel, text="Tip: drag the blue corner handle on the\ncanvas to resize a block.",
                  foreground="#636e72").grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # --- chip + optimizer settings
        chip = ttk.LabelFrame(tab_setup, text="Chip die", padding=6)
        chip.pack(fill=tk.X)
        self.chip_w_var = tk.StringVar(value=f"{self.plan.chip_width:g}")
        self.chip_h_var = tk.StringVar(value=f"{self.plan.chip_height:g}")
        for r, (text, var) in enumerate([("Width (\u03bcm)", self.chip_w_var), ("Height (\u03bcm)", self.chip_h_var)]):
            ttk.Label(chip, text=text).grid(row=r, column=0, sticky="e", padx=4, pady=3)
            e = ttk.Entry(chip, textvariable=var, width=10)
            e.grid(row=r, column=1, sticky="w", pady=3)
            e.bind("<Return>", lambda ev: self.apply_chip_size())
        ttk.Button(chip, text="Apply size", command=self.apply_chip_size).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        opt = ttk.LabelFrame(tab_setup, text="Optimizer", padding=6)
        opt.pack(fill=tk.X, pady=(8, 0))
        self.temp_var, self.cooling_var, self.iter_var = tk.StringVar(value="5000"), tk.StringVar(value="0.999"), tk.StringVar(value="15000")
        for r, (text, var) in enumerate([("Initial temp", self.temp_var), ("Cooling rate", self.cooling_var), ("Iterations", self.iter_var)]):
            ttk.Label(opt, text=text).grid(row=r, column=0, sticky="e", padx=4, pady=3)
            ttk.Entry(opt, textvariable=var, width=10).grid(row=r, column=1, sticky="w", pady=3)
        ttk.Checkbutton(opt, text="Allow 90\u00b0 rotation", variable=self.rotation_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def _build_center(self, parent, start_cb, load_cb):
        center = ttk.Frame(parent)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bar = ttk.Frame(center)
        bar.pack(fill=tk.X, pady=(0, 6))
        for text, cmd in (("\uff0b", lambda: self.zoom_at_center(1.2)), ("\uff0d", lambda: self.zoom_at_center(1 / 1.2)), ("Fit", self.fit_view)):
            ttk.Button(bar, text=text, width=4, command=cmd).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(bar, text="Grid", variable=self.show_grid, command=self.refresh).pack(side=tk.LEFT, padx=(10, 2))
        ttk.Checkbutton(bar, text="Heat map", variable=self.show_heat, command=self.refresh).pack(side=tk.LEFT, padx=2)
        self.btn_opt = ttk.Button(bar, text="\u25b6  Run Optimizer", style="Accent.TButton", command=start_cb)
        self.btn_opt.pack(side=tk.RIGHT, padx=2)
        ttk.Button(bar, text="Save", command=self.export_results).pack(side=tk.RIGHT, padx=2)
        if load_cb:
            ttk.Button(bar, text="Load", command=load_cb).pack(side=tk.RIGHT, padx=2)
        self.canvas = tk.Canvas(center, bg="#dfe6e9", highlightthickness=1, highlightbackground="#b2bec3", cursor="arrow")
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def _build_right(self, parent):
        right = ttk.Frame(parent, width=340)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)
        mf = ttk.LabelFrame(right, text="Layout metrics", padding=6)
        mf.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))
        self.metrics_var = tk.StringVar(value="Run the optimizer to see results.")
        tk.Label(mf, textvariable=self.metrics_var, justify="left", anchor="w", bg=BG, fg=DARK, font=("Consolas", 9)).pack(fill=tk.X)
        gf = ttk.LabelFrame(right, text="Real-time analytics", padding=4)
        gf.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.fig = Figure(figsize=(3.2, 3.6), dpi=100)
        self.ax_cost = self.fig.add_subplot(211)
        self.ax_temp = self.fig.add_subplot(212)
        self._style_axes()
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=gf)
        self.plot_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_status(self):
        bar = tk.Frame(self.master, bg=DARK, height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        self.stats_var, self.msg_var = tk.StringVar(), tk.StringVar()
        tk.Label(bar, textvariable=self.stats_var, bg=DARK, fg="white", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=12, pady=4)
        self.msg_label = tk.Label(bar, textvariable=self.msg_var, bg=DARK, fg="#dfe6e9", font=("Segoe UI", 9, "bold"))
        self.msg_label.pack(side=tk.RIGHT, padx=12)

    def _bind_events(self):
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_mouse_down)
        c.bind("<B1-Motion>", self.on_mouse_drag)
        c.bind("<ButtonRelease-1>", self.on_mouse_up)
        c.bind("<Configure>", self.on_configure)
        c.bind("<MouseWheel>", self.on_wheel)
        c.bind("<Button-4>", self.on_wheel)
        c.bind("<Button-5>", self.on_wheel)
        self.master.bind("<Delete>", self.delete_selected)

    def _style_axes(self):
        self.ax_cost.set_title("Cost vs iterations", fontsize=9)
        self.ax_cost.set_ylabel("Cost", fontsize=8)
        self.ax_temp.set_title("Temperature decay", fontsize=9)
        self.ax_temp.set_xlabel("Iterations", fontsize=8)
        self.ax_temp.set_ylabel("Temperature", fontsize=8)
        for ax in (self.ax_cost, self.ax_temp):
            ax.tick_params(labelsize=7)
            ax.grid(True, alpha=0.25)
        self.fig.tight_layout(pad=1.6)

    # ------------------------------------------------------------------ status helpers
    def set_message(self, text, level="info"):
        colours = {"info": "#dfe6e9", "ok": "#55efc4", "warn": "#fdcb6e", "error": "#ff7675"}
        self.msg_var.set(text)
        self.msg_label.config(fg=colours.get(level, "#dfe6e9"))

    def update_stats(self):
        p = self.plan
        bd = cost_breakdown(p)
        self.stats_var.set(f"Blocks: {len(p.blocks)}   Nets: {len(p.nets)}   Utilization: {p.utilization() * 100:.0f}%   "
                           f"Overlaps: {bd['overlap_count']}   Out of bounds: {'yes' if bd['out_of_bounds'] > 0.01 else 'no'}")
        return bd

    def show_insufficient(self, feas, action):
        side = feas.suggested_side
        messagebox.showwarning(
            "Dimension not sufficient",
            f"The chip dimension is not sufficient to accommodate {action}.\n\n{feas.message()}"
            + (f"\n\nSuggested die size: {side} \u00d7 {side} \u03bcm." if side else ""))

    def refresh(self):
        bd = self.update_stats()
        self.draw_floorplan(self.plan, bd["total"])

    # ------------------------------------------------------------------ chip size
    def apply_chip_size(self):
        """Commit the chip size from the entry boxes. Returns True if accepted."""
        try:
            w = float(self.chip_w_var.get())
            h = float(self.chip_h_var.get())
            if not (MIN_DIM <= w <= MAX_DIM and MIN_DIM <= h <= MAX_DIM):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid size", f"Chip width and height must be numbers between {MIN_DIM:g} and {MAX_DIM:g} \u03bcm.")
            self._reset_chip_entries()
            return False
        feas = check_feasibility(self.plan.blocks, w, h, self.rotation_var.get())
        if feas.hard_fail:
            self.show_insufficient(feas, "the placed components")
            self._reset_chip_entries()
            return False
        self.resize_chip(w, h)
        if not feas.ok:
            self.set_message("Die may be too tight for these components", "warn")
        return True

    def resize_chip(self, w, h):
        self.plan.chip_width, self.plan.chip_height = float(w), float(h)
        self._reset_chip_entries()
        for b in self.plan.blocks:                       # pull any stray block back inside the die
            b.x = min(max(b.x, 0.0), max(0.0, w - b.width))
            b.y = min(max(b.y, 0.0), max(0.0, h - b.height))
        self.fit_view()

    def _reset_chip_entries(self):
        self.chip_w_var.set(f"{self.plan.chip_width:g}")
        self.chip_h_var.set(f"{self.plan.chip_height:g}")

    # ------------------------------------------------------------------ adding components
    def spawn_kind(self, kind):
        w, h, p, _ = COMPONENT_LIBRARY[kind]
        self.spawn_block(kind, w, h, p, kind)

    def add_custom(self):
        d = ask_custom_block(self.master)
        if d:
            self.spawn_block(d["name"], d["width"], d["height"], d["power"], kind_of(d["name"]))

    def find_free_spot(self, w, h):
        """First position (scanning from the top-left, which fragments the die least) where the new
        block overlaps nothing. Finer scan if crowded. Returns None if there is no gap."""
        W, H = self.plan.chip_width, self.plan.chip_height
        for step in (max(10, int(max(W, H) / 60)), max(5, int(max(W, H) / 120)), max(2, int(max(W, H) / 200))):
            for y in range(0, int(H - h) + 1, step):
                for x in range(0, int(W - w) + 1, step):
                    if all(min(x + w, b.x + b.width) - max(x, b.x) <= 0 or min(y + h, b.y + b.height) - max(y, b.y) <= 0
                           for b in self.plan.blocks):
                        return float(x), float(y)
        return None

    def spawn_block(self, base_name, width, height, power, kind="CUSTOM"):
        if self.running:
            return
        name = self.plan.unique_name(base_name)
        new_block = Block(name=name, width=width, height=height, power_watts=power, kind=kind)
        feas = check_feasibility(self.plan.blocks + [new_block], self.plan.chip_width, self.plan.chip_height, self.rotation_var.get())
        if feas.hard_fail:
            self.show_insufficient(feas, f"{name}")
            return
        spot = self.find_free_spot(width, height)
        msg, level = f"Added {name}", "info"
        if spot:
            new_block.x, new_block.y = spot
            self.plan.blocks.append(new_block)
        elif feas.placement:                                  # no gap, but a legal arrangement exists: rearrange
            self.plan.blocks.append(new_block)
            for b in self.plan.blocks:
                b.x, b.y, b.width, b.height = feas.placement[b.name]
            msg = f"Added {name} (blocks were rearranged to make room)"
        else:                                                 # tight die: drop it in the middle, optimizer will resolve it
            new_block.x = max(0.0, (self.plan.chip_width - width) / 2)
            new_block.y = max(0.0, (self.plan.chip_height - height) / 2)
            self.plan.blocks.append(new_block)
            msg, level = "No free space - die is too tight; consider a larger chip", "warn"
        self.select(new_block)
        self.set_message(msg, level)

    def select(self, block):
        self.selected_block = block
        self.load_form()
        self.refresh()

    def load_form(self):
        b = self.selected_block
        state = "normal" if b else "disabled"
        for e in self.form_entries:
            e.config(state=state)
        for w in (self.btn_apply, self.btn_rot, self.btn_con, self.btn_del):
            w.config(state=state)
        if b:
            self.name_var.set(b.name)
            self.w_var.set(f"{b.width:g}")
            self.h_var.set(f"{b.height:g}")
            self.p_var.set(f"{b.power_watts:g}")
        else:
            for v in (self.name_var, self.w_var, self.h_var, self.p_var):
                v.set("")

    def apply_selected_edits(self):
        b = self.selected_block
        if not b or self.running:
            return
        name = self.name_var.get().strip().replace(" ", "_")
        try:
            w = float(self.w_var.get()); h = float(self.h_var.get()); p = float(self.p_var.get())
            if w < MIN_BLOCK or h < MIN_BLOCK or p < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid value", f"Width and height must be numbers \u2265 {MIN_BLOCK:g} and power must be \u2265 0.")
            self.load_form()
            return
        if not name or any(o is not b and o.name == name for o in self.plan.blocks):
            messagebox.showerror("Invalid name", "Block names must be unique and not empty.")
            self.load_form()
            return
        old = (b.width, b.height)
        b.width, b.height = w, h
        feas = check_feasibility(self.plan.blocks, self.plan.chip_width, self.plan.chip_height, self.rotation_var.get())
        if feas.hard_fail:
            b.width, b.height = old
            self.show_insufficient(feas, f"{name} at {w:g} \u00d7 {h:g}")
            self.load_form()
            return
        b.name, b.power_watts = name, p
        b.x = min(max(b.x, 0.0), max(0.0, self.plan.chip_width - w))
        b.y = min(max(b.y, 0.0), max(0.0, self.plan.chip_height - h))
        self.set_message(f"Updated {name}" if feas.ok else "Die may be too tight for these components", "info" if feas.ok else "warn")
        self.load_form()
        self.refresh()

    def rotate_selected(self):
        b = self.selected_block
        if not b or self.running:
            return
        if b.height > self.plan.chip_width or b.width > self.plan.chip_height:
            messagebox.showwarning("Dimension not sufficient", f"{b.name} does not fit in the die when rotated.")
            return
        b.rotate()
        b.x = min(max(b.x, 0.0), self.plan.chip_width - b.width)
        b.y = min(max(b.y, 0.0), self.plan.chip_height - b.height)
        self.load_form()
        self.refresh()

    def delete_selected(self, event=None):
        if event is not None and isinstance(self.master.focus_get(), (tk.Entry, ttk.Entry, ttk.Combobox)):
            return                                           # Delete key inside a text box edits text only
        if self.selected_block and not self.running:
            self.plan.blocks.remove(self.selected_block)
            for net in self.plan.nets:
                if self.selected_block in net.connected_blocks:
                    net.connected_blocks.remove(self.selected_block)
            self.plan.nets = [n for n in self.plan.nets if len(n.connected_blocks) > 1]
            self.select(None)

    def open_connect_dialog(self):
        if not self.selected_block:
            messagebox.showwarning("Warning", "Please click a block to select it first!")
            return
        options = [b.name for b in self.plan.blocks if b != self.selected_block]
        if not options:
            messagebox.showinfo("Connect", "Add at least one more block to connect to.")
            return
        top = tk.Toplevel(self.master)
        top.title("Connect blocks")
        top.transient(self.master)
        top.resizable(False, False)
        frm = ttk.Frame(top, padding=14)
        frm.pack()
        ttk.Label(frm, text=f"Connect {self.selected_block.name} to:").pack(pady=(0, 8))
        target = tk.StringVar(value=options[0])
        ttk.Combobox(frm, textvariable=target, values=options, state="readonly", width=18).pack(pady=4)

        def make_connection():
            tb = next((b for b in self.plan.blocks if b.name == target.get()), None)
            src = self.selected_block
            if tb:
                exists = any(len(n.connected_blocks) == 2 and set(map(id, n.connected_blocks)) == {id(src), id(tb)} for n in self.plan.nets)
                if exists:
                    messagebox.showinfo("Connect", "These two blocks are already connected.")
                else:
                    self.plan.nets.append(Net(name=f"{src.name}_to_{tb.name}", connected_blocks=[src, tb]))
                    self.refresh()
            top.destroy()
        ttk.Button(frm, text="Create wire", command=make_connection).pack(pady=(8, 0))

    # ------------------------------------------------------------------ view helpers
    def fit_view(self):
        cw = max(self.canvas.winfo_width(), 300)
        ch = max(self.canvas.winfo_height(), 300)
        W, H = self.plan.chip_width, self.plan.chip_height
        z = min((cw - 80) / W, (ch - 80) / H)
        self.zoom = max(0.05, min(z, 6.0))
        self.pan_x = (cw - W * self.zoom) / 2
        self.pan_y = (ch - H * self.zoom) / 2 + 8
        self.refresh()

    def zoom_at(self, sx, sy, factor):
        wx, wy = (sx - self.pan_x) / self.zoom, (sy - self.pan_y) / self.zoom
        self.zoom = max(0.05, min(self.zoom * factor, 20.0))
        self.pan_x, self.pan_y = sx - wx * self.zoom, sy - wy * self.zoom
        self.refresh()

    def zoom_at_center(self, factor):
        self.zoom_at(self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2, factor)

    def on_wheel(self, event):
        up = getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0
        self.zoom_at(event.x, event.y, 1.1 if up else 1 / 1.1)

    def on_configure(self, event):
        if not self._fitted and event.width > 100:
            self._fitted = True
            self.fit_view()
        else:
            self.draw_floorplan(self.plan, cost_breakdown(self.plan)["total"])

    # ------------------------------------------------------------------ optimizer parameters
    def get_optimizer_params(self):
        """Returns (temp, cooling, iterations, allow_rotation) or None after showing an error."""
        try:
            temp = float(self.temp_var.get()); cooling = float(self.cooling_var.get()); iters = int(float(self.iter_var.get()))
            if temp <= 0 or not (0 < cooling < 1) or not (100 <= iters <= 500000):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid optimizer settings",
                                 "Initial temp must be > 0, cooling rate between 0 and 1 (e.g. 0.999) and iterations between 100 and 500000.")
            return None
        return temp, cooling, iters, self.rotation_var.get()

    def set_running(self, flag):
        self.running = flag
        self.btn_opt.config(state="disabled" if flag else "normal", text="Optimizing..." if flag else "\u25b6  Run Optimizer")
        if flag:
            self.selected_block = None
            self.load_form()
            self.set_message("Optimizing...", "info")

    def set_new_floorplan(self, new_plan: Floorplan):
        self.plan = new_plan
        self.selected_block = None
        self._reset_chip_entries()
        self.reset_plot()
        self.load_form()
        self.fit_view()
        feas = check_feasibility(new_plan.blocks, new_plan.chip_width, new_plan.chip_height, self.rotation_var.get())
        if not feas.ok:
            self.set_message("Loaded layout does not fit the die", "warn")
            self.show_insufficient(feas, "the loaded components")

    def reset_plot(self):
        self.iterations_data.clear(); self.cost_data.clear(); self.temp_data.clear()
        self.ax_cost.clear(); self.ax_temp.clear()
        self._style_axes()
        self.plot_canvas.draw()
        self.metrics_var.set("Run the optimizer to see results.")

    def show_metrics(self):
        bd = cost_breakdown(self.plan)
        self.metrics_var.set(
            f"Total cost    : {bd['total']:,.1f}\n"
            f"Wirelength    : {bd['wirelength']:,.1f} \u03bcm\n"
            f"Overlap area  : {bd['overlap_area']:,.1f} \u03bcm\u00b2 ({bd['overlap_count']} pairs)\n"
            f"Out of bounds : {bd['out_of_bounds']:,.1f} \u03bcm\n"
            f"Congestion    : {bd['congestion']:,.0f}\n"
            f"Thermal score : {bd['thermal']:,.1f}\n"
            f"Legal layout  : {'YES' if bd['legal'] else 'NO'}")
        if bd["legal"]:
            self.set_message("Done - legal layout (no overlaps, inside die)", "ok")
        else:
            self.set_message("Done - layout still has overlaps; enlarge the die or add iterations", "warn")
        self.update_stats()

    # ------------------------------------------------------------------ export
    def export_results(self):
        path = filedialog.asksaveasfilename(title="Save layout", defaultextension=".json", initialfile="optimized_layout.json",
                                            filetypes=(("JSON files", "*.json"),))
        if not path:
            return
        try:
            data = {
                "chip_width": self.plan.chip_width, "chip_height": self.plan.chip_height,
                "blocks": [{"name": b.name, "kind": b.kind, "x": round(b.x, 2), "y": round(b.y, 2),
                            "width": b.width, "height": b.height, "power_watts": b.power_watts} for b in self.plan.blocks],
                "nets": [{"name": n.name, "blocks": [b.name for b in n.connected_blocks]} for n in self.plan.nets],
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
            msg = f"Saved '{path}'"
            if self.iterations_data:
                png = (path[:-5] if path.lower().endswith(".json") else path) + "_cost_graph.png"
                self.fig.savefig(png)
                msg += f" and '{png}'"
            messagebox.showinfo("Success", msg)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save files: {e}")

    # ------------------------------------------------------------------ mouse
    def to_world(self, sx, sy):
        return (sx - self.pan_x) / self.zoom, (sy - self.pan_y) / self.zoom

    def _on_handle(self, event):
        b = self.selected_block
        if not b:
            return False
        hx, hy = (b.x + b.width) * self.zoom + self.pan_x, (b.y + b.height) * self.zoom + self.pan_y
        return abs(event.x - hx) <= HANDLE and abs(event.y - hy) <= HANDLE

    def on_mouse_down(self, event):
        if self.running:
            return
        self.drag_x, self.drag_y = event.x, event.y
        if self._on_handle(event):
            self.mode, self._old_size = "resize", (self.selected_block.width, self.selected_block.height)
            return
        wx, wy = self.to_world(event.x, event.y)
        for block in reversed(self.plan.blocks):
            if block.x <= wx <= block.x + block.width and block.y <= wy <= block.y + block.height:
                self.mode = "move"
                self.select(block)
                return
        self.mode = "pan"
        self.select(None)

    def on_mouse_drag(self, event):
        if self.running or not self.mode:
            return
        dx, dy = event.x - self.drag_x, event.y - self.drag_y
        b = self.selected_block
        if self.mode == "resize" and b:
            wx, wy = self.to_world(event.x, event.y)
            b.width = min(max(wx - b.x, MIN_BLOCK), self.plan.chip_width - b.x)
            b.height = min(max(wy - b.y, MIN_BLOCK), self.plan.chip_height - b.y)
            self.w_var.set(f"{b.width:.0f}"); self.h_var.set(f"{b.height:.0f}")
        elif self.mode == "move" and b:
            b.x = min(max(b.x + dx / self.zoom, 0.0), max(0.0, self.plan.chip_width - b.width))
            b.y = min(max(b.y + dy / self.zoom, 0.0), max(0.0, self.plan.chip_height - b.height))
        elif self.mode == "pan":
            self.pan_x += dx
            self.pan_y += dy
        self.refresh()
        self.drag_x, self.drag_y = event.x, event.y

    def on_mouse_up(self, event):
        b = self.selected_block
        if self.mode == "resize" and b:
            b.width, b.height = round(b.width, 1), round(b.height, 1)
            feas = check_feasibility(self.plan.blocks, self.plan.chip_width, self.plan.chip_height, self.rotation_var.get())
            if feas.hard_fail:
                b.width, b.height = self._old_size
                self.show_insufficient(feas, f"{b.name} at the new size")
            elif not feas.ok:
                self.set_message("Die may be too tight for these components", "warn")
            self.load_form()
            self.refresh()
        self.mode = None

    # ------------------------------------------------------------------ drawing
    @staticmethod
    def _heat_colour(power, max_power):
        t = 0.0 if max_power <= 0 else min(power / max_power, 1.0)
        lo, hi = (116, 185, 255), (255, 71, 87)
        return "#%02x%02x%02x" % tuple(int(a + (b - a) * t) for a, b in zip(lo, hi))

    def draw_floorplan(self, floorplan: Floorplan, cost: float = 0.0, temp: float = 0.0, iteration: int = 0):
        c, z, ox, oy = self.canvas, self.zoom, self.pan_x, self.pan_y
        W, H = floorplan.chip_width, floorplan.chip_height
        c.delete("all")

        # die + grid (grid lines are in die coordinates, every 50 um)
        c.create_rectangle(ox, oy, ox + W * z, oy + H * z, fill="#ffffff", outline=DARK, width=2)
        if self.show_grid.get():
            step = 50
            while step * z < 18:
                step *= 2
            x = 0
            while x <= W:
                c.create_line(ox + x * z, oy, ox + x * z, oy + H * z, fill="#eef1f4")
                if step * z >= 36:
                    c.create_text(ox + x * z + 2, oy - 8, text=f"{x}", anchor="w", font=("Segoe UI", 7), fill="#636e72")
                x += step
            y = 0
            while y <= H:
                c.create_line(ox, oy + y * z, ox + W * z, oy + y * z, fill="#eef1f4")
                y += step
        util = floorplan.utilization() * 100
        c.create_text(ox + W * z, oy + H * z + 6, anchor="ne", font=("Segoe UI", 9, "italic"), fill=DARK,
                      text=f"Die {W:g} \u00d7 {H:g} \u03bcm   |   utilization {util:.0f}%")

        # nets
        for net in floorplan.nets:
            for i in range(len(net.connected_blocks) - 1):
                b1, b2 = net.connected_blocks[i], net.connected_blocks[i + 1]
                c.create_line((b1.x + b1.width / 2) * z + ox, (b1.y + b1.height / 2) * z + oy,
                              (b2.x + b2.width / 2) * z + ox, (b2.y + b2.height / 2) * z + oy,
                              fill="#00897b", width=2, dash=(5, 3))

        # which blocks overlap?
        blocks = floorplan.blocks
        overlapping = set()
        for i in range(len(blocks)):
            for j in range(i + 1, len(blocks)):
                if calculate_overlap_area(blocks[i], blocks[j]) > 0.01:
                    overlapping.update((id(blocks[i]), id(blocks[j])))
        max_power = max((b.power_watts for b in blocks), default=1.0)

        for b in blocks:
            x1, y1 = b.x * z + ox, b.y * z + oy
            x2, y2 = (b.x + b.width) * z + ox, (b.y + b.height) * z + oy
            fill = self._heat_colour(b.power_watts, max_power) if self.show_heat.get() else colour_of(b.kind)
            if b is self.selected_block:
                outline, width = ACCENT, 3
            elif id(b) in overlapping:
                outline, width = DANGER, 3
            else:
                outline, width = "#2f3542", 1
            c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width)
            fs = max(7, min(int(10 * z), 14))
            fpx = fs * 1.4                                   # approx. text height in pixels
            two_lines = (y2 - y1) > 3.2 * fpx and (x2 - x1) > 70
            if x2 - x1 > 28 and y2 - y1 > 16:
                c.create_text((x1 + x2) / 2, (y1 + y2) / 2 - (0.6 * fpx if two_lines else 0), text=b.name,
                              font=("Segoe UI", fs, "bold"), fill="#1e272e")
                if two_lines:
                    c.create_text((x1 + x2) / 2, (y1 + y2) / 2 + 0.75 * fpx,
                                  text=f"{b.width:.0f}\u00d7{b.height:.0f}  {b.power_watts:g}W",
                                  font=("Segoe UI", max(6, fs - 2)), fill="#2d3436")
        if self.selected_block in blocks:
            b = self.selected_block
            hx, hy = (b.x + b.width) * z + ox, (b.y + b.height) * z + oy
            c.create_rectangle(hx - HANDLE / 2, hy - HANDLE / 2, hx + HANDLE / 2, hy + HANDLE / 2, fill=ACCENT, outline="white", width=1)

        c.create_text(12, 12, anchor="nw", font=("Segoe UI", 11, "bold"), fill=DARK,
                      text=f"Cost: {cost:,.1f}" + (f"   Temp: {temp:,.2f}   Iter: {iteration}" if iteration > 0 else ""))

        if iteration > 0:
            self.iterations_data.append(iteration); self.cost_data.append(cost); self.temp_data.append(temp)
            self.ax_cost.clear(); self.ax_temp.clear()
            self._style_axes()
            self.ax_cost.plot(self.iterations_data, self.cost_data, color="#1e90ff")
            self.ax_temp.plot(self.iterations_data, self.temp_data, color="#ff4757")
            self.plot_canvas.draw_idle()
            self.master.update()          # keeps the window responsive while the optimizer runs
        else:
            self.master.update_idletasks()
