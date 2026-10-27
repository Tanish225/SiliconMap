import tkinter as tk
from tkinter import ttk

DEFAULT_CHIP = (400.0, 400.0)
MIN_DIM, MAX_DIM = 50.0, 20000.0


def _center(top):
    top.update_idletasks()
    w, h = top.winfo_reqwidth(), top.winfo_reqheight()
    x = (top.winfo_screenwidth() - w) // 2
    y = (top.winfo_screenheight() - h) // 3
    top.geometry(f"+{x}+{y}")


def _number(text, label, lo, hi):
    try:
        v = float(text)
    except ValueError:
        raise ValueError(f"{label} must be a number.")
    if not (lo <= v <= hi):
        raise ValueError(f"{label} must be between {lo:g} and {hi:g}.")
    return v


def _open_modal(parent, title):
    top = tk.Toplevel(parent)
    top.title(title)
    top.resizable(False, False)
    if parent.winfo_viewable():      # transient() on a hidden root would hide the dialog
        top.transient(parent)
    return top


def ask_chip_size(parent, default=DEFAULT_CHIP):
    """Startup dialog. Returns (width, height). Closing it keeps the default size."""
    result = {"value": default}
    top = _open_modal(parent, "SiliconMap - Chip Size")
    frm = ttk.Frame(top, padding=18)
    frm.pack()

    ttk.Label(frm, text="Set the chip die size", font=("Segoe UI", 13, "bold")).grid(
        row=0, column=0, columnspan=4, sticky="w")
    ttk.Label(frm, text="You can change it later from the 'Chip & Run' tab.",
              foreground="#636e72").grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))

    w_var = tk.StringVar(value=f"{default[0]:g}")
    h_var = tk.StringVar(value=f"{default[1]:g}")
    ttk.Label(frm, text="Width (\u03bcm)").grid(row=2, column=0, sticky="e", padx=4, pady=4)
    ttk.Entry(frm, textvariable=w_var, width=10).grid(row=2, column=1, pady=4)
    ttk.Label(frm, text="Height (\u03bcm)").grid(row=2, column=2, sticky="e", padx=4, pady=4)
    ttk.Entry(frm, textvariable=h_var, width=10).grid(row=2, column=3, pady=4)

    presets = ttk.Frame(frm)
    presets.grid(row=3, column=0, columnspan=4, pady=6)
    for side in (200, 300, 400, 600, 800):
        ttk.Button(presets, text=f"{side}\u00d7{side}", width=8,
                   command=lambda s=side: (w_var.set(str(s)), h_var.set(str(s)))).pack(side=tk.LEFT, padx=2)

    err = ttk.Label(frm, text="", foreground="#d63031", wraplength=320)
    err.grid(row=4, column=0, columnspan=4, sticky="w")

    def confirm(event=None):
        try:
            w = _number(w_var.get(), "Width", MIN_DIM, MAX_DIM)
            h = _number(h_var.get(), "Height", MIN_DIM, MAX_DIM)
        except ValueError as e:
            err.config(text=str(e))
            return
        result["value"] = (w, h)
        top.destroy()

    def use_default():
        result["value"] = default
        top.destroy()

    btns = ttk.Frame(frm)
    btns.grid(row=5, column=0, columnspan=4, pady=(10, 0))
    ttk.Button(btns, text="Start", command=confirm).pack(side=tk.LEFT, padx=4)
    ttk.Button(btns, text=f"Use default ({default[0]:g}\u00d7{default[1]:g})", command=use_default).pack(side=tk.LEFT, padx=4)

    top.bind("<Return>", confirm)
    top.protocol("WM_DELETE_WINDOW", use_default)
    _center(top)
    top.wait_visibility()
    top.grab_set()
    parent.wait_window(top)
    return result["value"]


def ask_custom_block(parent):
    """Dialog for a user-defined block. Returns dict(name,width,height,power) or None."""
    result = {"value": None}
    top = _open_modal(parent, "Custom Component")
    frm = ttk.Frame(top, padding=16)
    frm.pack()
    vars_ = {"name": tk.StringVar(value="CUSTOM"), "width": tk.StringVar(value="80"),
             "height": tk.StringVar(value="60"), "power": tk.StringVar(value="10")}
    labels = [("Name", "name"), ("Width (\u03bcm)", "width"), ("Height (\u03bcm)", "height"), ("Power (W)", "power")]
    for r, (text, key) in enumerate(labels):
        ttk.Label(frm, text=text).grid(row=r, column=0, sticky="e", padx=4, pady=4)
        ttk.Entry(frm, textvariable=vars_[key], width=14).grid(row=r, column=1, pady=4)
    err = ttk.Label(frm, text="", foreground="#d63031", wraplength=240)
    err.grid(row=4, column=0, columnspan=2, sticky="w")

    def confirm(event=None):
        name = vars_["name"].get().strip().replace(" ", "_")
        if not name:
            err.config(text="Name cannot be empty.")
            return
        try:
            w = _number(vars_["width"].get(), "Width", 1, MAX_DIM)
            h = _number(vars_["height"].get(), "Height", 1, MAX_DIM)
            p = _number(vars_["power"].get(), "Power", 0, 100000)
        except ValueError as e:
            err.config(text=str(e))
            return
        result["value"] = {"name": name, "width": w, "height": h, "power": p}
        top.destroy()

    ttk.Button(frm, text="Add to chip", command=confirm).grid(row=5, column=0, columnspan=2, pady=(10, 0))
    top.bind("<Return>", confirm)
    _center(top)
    top.wait_visibility()
    top.grab_set()
    parent.wait_window(top)
    return result["value"]
