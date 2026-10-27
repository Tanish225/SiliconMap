"""Standard component library: kind -> (width, height, power, fill colour)."""

COMPONENT_LIBRARY = {
    #  kind       width height power  colour
    "ALU":      (120, 100, 80.0, "#ff7675"),
    "FPU":      (130, 100, 70.0, "#e17055"),
    "CTRL":     (80,   60, 30.0, "#fdcb6e"),
    "DECODER":  (70,   50, 12.0, "#ffeaa7"),
    "REG":      (60,   60, 10.0, "#74b9ff"),
    "CACHE":    (160, 120, 40.0, "#a29bfe"),
    "RAM":      (200, 140, 25.0, "#6c5ce7"),
    "ROM":      (100,  80,  3.0, "#b2bec3"),
    "MUX":      (40,   40,  5.0, "#81ecec"),
    "DMA":      (90,   60, 18.0, "#55efc4"),
    "UART":     (60,   40,  4.0, "#00cec9"),
    "GPIO":     (50,   40,  3.0, "#00b894"),
    "ADC":      (70,   60,  8.0, "#fab1a0"),
    "PLL":      (50,   50, 15.0, "#fd79a8"),
    "PMU":      (80,   70, 20.0, "#e84393"),
}

CUSTOM_COLOR = "#dfe6e9"
DEFAULT_POWER = 10.0


def kind_of(name: str) -> str:
    """Guess the component kind from a block name like 'ALU_2' or 'cache_1'."""
    base = name.split("_")[0].upper()
    return base if base in COMPONENT_LIBRARY else "CUSTOM"


def colour_of(kind: str) -> str:
    return COMPONENT_LIBRARY[kind][3] if kind in COMPONENT_LIBRARY else CUSTOM_COLOR


def default_power(name: str) -> float:
    kind = kind_of(name)
    return COMPONENT_LIBRARY[kind][2] if kind in COMPONENT_LIBRARY else DEFAULT_POWER
