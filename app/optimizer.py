# app/optimizer.py
from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Dict, Tuple

import pandas as pd
import pulp


def _distance(pos: Dict[str, Tuple[float, float]], a: str, b: str) -> float:
    ax, ay = pos[a]
    bx, by = pos[b]
    return sqrt((ax - bx) ** 2 + (ay - by) ** 2)


@dataclass
class OptimizeInputs:
    demand: pd.DataFrame
    capacity: pd.DataFrame
    processing: pd.DataFrame
    baseline: pd.DataFrame
    positions: Dict[str, Tuple[float, float]]
    bay_sizes: Dict[str, float]
    reinstall_costs: Dict[str, float]
    switches: Dict[str, bool]
    params: Dict[str, float]
    penalty_weights: Dict[str, float]


def solve_lp(inp: OptimizeInputs) -> dict:
    """
    LP:
    Decision x[pg, sg] = units of pg allocated to sg
    slack u[pg] = unmet units of demand (penalized)

    Capacity constraint (hours):
    sum_pg x[pg,sg] * hours_per_unit[pg,sg] <= capacity_hours[sg]

    Demand satisfaction:
    sum_sg x[pg,sg] + u[pg] = demand_units[pg]

    Optional space constraint proxy (bays):
    sum_pg x[pg,sg] * bay_factor <= bay_sizes[sg]
    (Here bay_factor is derived from hours_per_unit scaled—public demo only)
    """
    demand = inp.demand.copy()
    cap = inp.capacity.copy()
    proc = inp.processing.copy()
    base = inp.baseline.copy()

    pgs = demand["product_group"].tolist()
    sgs = cap["space_group"].tolist()

    dem = dict(zip(demand["product_group"], demand["demand_units"].astype(float)))
    cap_hours = dict(zip(cap["space_group"], cap["capacity_hours"].astype(float)))
    base_sg = dict(zip(base["product_group"], base["baseline_space_group"]))

    hpu = {(r.product_group, r.space_group): float(r.hours_per_unit) for r in proc.itertuples(index=False)}

    # Costs
    movement_cost_per_unit = inp.params["movement_penalty_per_meter"]
    unmet_penalty = inp.params["unmet_demand_penalty"]
    reinstall_index = inp.params["reinstallation_penalty_index"]
    excess_space_index = inp.params["excess_space_penalty_index"]
    util_balance_penalty = inp.params["utilization_balance_penalty"]

    w_unmet = inp.penalty_weights["Unmet demand weight"]
    w_move = inp.penalty_weights["Movement weight"]
    w_reinstall = inp.penalty_weights["Reinstallation weight"]
    w_utilbal = inp.penalty_weights["Utilization balance weight"]
    w_excess = inp.penalty_weights["Excess space weight"]

    prob = pulp.LpProblem("Utilization_Reallocation", pulp.LpMinimize)

    x = pulp.LpVariable.dicts("x", (pgs, sgs), lowBound=0, cat="Continuous")
    u = pulp.LpVariable.dicts("unmet", pgs, lowBound=0, cat="Continuous")

    # For utilization balancing, we introduce utilization variables per sg
    util = pulp.LpVariable.dicts("util", sgs, lowBound=0, cat="Continuous")
    util_avg = pulp.LpVariable("util_avg", lowBound=0, cat="Continuous")
    util_dev_pos = pulp.LpVariable.dicts("util_dev_pos", sgs, lowBound=0, cat="Continuous")
    util_dev_neg = pulp.LpVariable.dicts("util_dev_neg", sgs, lowBound=0, cat="Continuous")

    # Objective components
    move_terms = []
    reinstall_terms = []
    unmet_terms = []
    excess_terms = []
    utilbal_terms = []

    # Movement + reinstall cost based on baseline SG
    for pg in pgs:
        bsg = base_sg[pg]
        for sg in sgs:
            d = _distance(inp.positions, bsg, sg)
            move_terms.append(movement_cost_per_unit * d * x[pg][sg])

            # reinstall cost uses per-SG factor (demo proxy)
            reinstall_terms.append(reinstall_index * inp.reinstall_costs[sg] * x[pg][sg])

    for pg in pgs:
        unmet_terms.append(unmet_penalty * u[pg])

    # Capacity & util definition
    for sg in sgs:
        hours_used = pulp.lpSum(x[pg][sg] * hpu[(pg, sg)] for pg in pgs)
        prob += hours_used <= cap_hours[sg], f"cap_hours_{sg}"
        prob += util[sg] == hours_used / cap_hours[sg], f"util_def_{sg}"

        # Excess "space" proxy: encourage not wasting bay capacity if switch on (demo)
        # We'll approximate bays used proportional to hours used / 40
        if inp.switches.get("space_constraint", True):
            bays_used = hours_used / 40.0
            prob += bays_used <= float(inp.bay_sizes[sg]), f"bay_{sg}"

        # Penalize unused capacity lightly (optional preference)
        excess_terms.append(excess_space_index * (1 - util[sg]))

    # Demand satisfaction
    for pg in pgs:
        prob += pulp.lpSum(x[pg][sg] for sg in sgs) + u[pg] == dem[pg], f"demand_{pg}"

    # Utilization balancing around average
    prob += util_avg == pulp.lpSum(util[sg] for sg in sgs) / len(sgs), "util_avg_def"
    for sg in sgs:
        prob += util[sg] - util_avg == util_dev_pos[sg] - util_dev_neg[sg], f"util_dev_{sg}"
        utilbal_terms.append(util_balance_penalty * (util_dev_pos[sg] + util_dev_neg[sg]))

    prob += (
        w_move * pulp.lpSum(move_terms)
        + w_reinstall * pulp.lpSum(reinstall_terms)
        + w_unmet * pulp.lpSum(unmet_terms)
        + w_excess * pulp.lpSum(excess_terms)
        + w_utilbal * pulp.lpSum(utilbal_terms)
    ), "total_cost"

    # Solve with CBC (open-source)
    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)

    status_str = pulp.LpStatus.get(prob.status, "Unknown")

    alloc_rows = []
    for pg in pgs:
        for sg in sgs:
            val = pulp.value(x[pg][sg])
            if val is not None and val > 1e-6:
                alloc_rows.append((pg, sg, float(val), float(hpu[(pg, sg)] * val)))
    alloc = pd.DataFrame(alloc_rows, columns=["product_group", "space_group", "units", "hours_used"])

    util_rows = []
    for sg in sgs:
        util_val = pulp.value(util[sg])
        util_rows.append((sg, float(cap_hours[sg]), float(util_val) if util_val is not None else None))
    util_df = pd.DataFrame(util_rows, columns=["space_group", "capacity_hours", "utilization"])

    unmet_rows = []
    for pg in pgs:
        unmet_val = pulp.value(u[pg]) or 0.0
        unmet_rows.append((pg, float(dem[pg]), float(unmet_val)))
    unmet_df = pd.DataFrame(unmet_rows, columns=["product_group", "demand_units", "unmet_units"])

    kpis = {
        "status": status_str,
        "objective_value": float(pulp.value(prob.objective)) if pulp.value(prob.objective) is not None else None,
        "total_unmet_units": float(unmet_df["unmet_units"].sum()),
        "avg_utilization": float(util_df["utilization"].mean()) if util_df["utilization"].notna().any() else None,
        "max_utilization": float(util_df["utilization"].max()) if util_df["utilization"].notna().any() else None,
    }

    return {
        "kpis": kpis,
        "allocation": alloc.sort_values(["product_group", "space_group"]).reset_index(drop=True),
        "utilization": util_df.sort_values("space_group").reset_index(drop=True),
        "unmet": unmet_df.sort_values("product_group").reset_index(drop=True),
    }
