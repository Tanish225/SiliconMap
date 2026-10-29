"""Interconnect delay modeling and timing evaluation for VLSI placement.

Theoretical References:
1. W. C. Elmore, "The Transient Response of Damped Linear Networks with Particular
   Regard to Wideband Amplifiers", Journal of Applied Physics, 19(1): 55-63, 1948.
   - Foundational first-moment approximation (Elmore Delay) for distributed RC circuits.
2. H. B. Bakoglu, "Circuits, Interconnections, and Packaging for VLSI", Addison-Wesley, 1990.
   - Closed-form distributed RC interconnect delay formulation:
     tau = R_driver * (C_wire + C_load) + R_wire * (0.5 * C_wire + C_load)
         = R_driver * C_load + (R_driver * c0 + r0 * C_load) * L + 0.5 * r0 * c0 * L^2
3. T. Koide and S. Wakabayashi, "A timing-driven floorplanning algorithm with the
   Elmore delay model for building block layout", Integration: The VLSI Journal, 28(1): 57-75, 1999.
   - Incorporation of Elmore delay into Simulated Annealing placement, balancing
     critical path delay and total latency against thermal and physical layout constraints.
"""
from typing import Dict, Optional, Tuple
from app.core.models import Floorplan, Net

# ---------------------------------------------------------------------------
# Technology & Interconnect Parameters (Deep Submicron Copper / Low-k standard)
# ---------------------------------------------------------------------------
# Driver equivalent on-resistance (Ohms)
R_DRIVER: float = 120.0

# Pin / gate input load capacitance per sink (fF = 1e-15 F)
C_LOAD: float = 4.0

# Interconnect resistance per micrometer (Ohms / um)
R_WIRE_PER_UM: float = 0.08

# Interconnect capacitance per micrometer (fF / um)
C_WIRE_PER_UM: float = 0.18

# Multiplier for the critical path (worst net delay) in the timing penalty
CRITICAL_NET_WEIGHT: float = 3.0

# Default cost function weight for timing delay in simulated annealing
DELAY_WEIGHT: float = 25.0


def calculate_net_delay(
    net: Net,
    r_driver: float = R_DRIVER,
    c_load: float = C_LOAD,
    r_wire: float = R_WIRE_PER_UM,
    c_wire: float = C_WIRE_PER_UM,
) -> float:
    """Calculate the Elmore propagation delay of a net in picoseconds (ps).

    Under Bakoglu's distributed RC model:
        t_fs = R_d * C_L_tot + (R_d * c_w + r_w * C_load_per_sink) * L + 0.5 * r_w * c_w * L^2
    Returns delay in picoseconds (ps = fs / 1000).
    """
    if len(net.connected_blocks) < 2:
        return 0.0

    x_coords = [b.x + (b.width / 2.0) for b in net.connected_blocks]
    y_coords = [b.y + (b.height / 2.0) for b in net.connected_blocks]
    length_um = (max(x_coords) - min(x_coords)) + (max(y_coords) - min(y_coords))

    num_sinks = max(1, len(net.connected_blocks) - 1)
    c_load_tot = num_sinks * c_load

    # Femtoseconds (1 Ohm * 1 fF = 1 fs)
    t_gate_fs = r_driver * c_load_tot
    t_linear_fs = (r_driver * c_wire + r_wire * (c_load_tot / num_sinks)) * length_um
    t_quad_fs = 0.5 * r_wire * c_wire * (length_um ** 2)

    total_fs = t_gate_fs + t_linear_fs + t_quad_fs
    return total_fs / 1000.0  # Convert fs to picoseconds (ps)


def calculate_delay_stats(floorplan: Floorplan) -> dict:
    """Evaluate timing delay metrics across all nets in the floorplan.

    Returns:
        total_delay: Sum of delays across all nets (ps)
        max_delay: Critical path / worst-case net delay (ps)
        critical_net: Name of the net with maximum delay (or None if no nets)
        avg_delay: Average net delay (ps)
        net_delays: Mapping of net name -> delay (ps)
        penalty: Combined timing cost (total_delay + CRITICAL_NET_WEIGHT * max_delay)
    """
    net_delays: Dict[str, float] = {}
    max_delay = 0.0
    critical_net: Optional[str] = None
    total_delay = 0.0

    for net in floorplan.nets:
        if len(net.connected_blocks) < 2:
            continue
        delay = calculate_net_delay(net)
        net_delays[net.name] = delay
        total_delay += delay
        if delay > max_delay:
            max_delay = delay
            critical_net = net.name

    count = len(net_delays)
    avg_delay = (total_delay / count) if count > 0 else 0.0
    penalty = total_delay + (CRITICAL_NET_WEIGHT * max_delay)

    return {
        "total_delay": total_delay,
        "max_delay": max_delay,
        "critical_net": critical_net,
        "avg_delay": avg_delay,
        "net_delays": net_delays,
        "penalty": penalty,
    }
