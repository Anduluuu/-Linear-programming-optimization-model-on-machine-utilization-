# app/sample_data.py
from __future__ import annotations

import numpy as np
import pandas as pd


def make_synthetic_instance(seed: int = 7) -> dict[str, pd.DataFrame]:
    """
    Creates synthetic data for a public portfolio demo:
    - space groups (SG_*)
    - product groups (PG_*)
    - demand per product group
    - capacity per space group (in "hours" units)
    - processing time per unit (hours per unit) by (PG, SG)
    - current assignment baseline (for reinstall/movement cost reference)
    """
    rng = np.random.default_rng(seed)

    space_groups = ["SG_A", "SG_B", "SG_C", "SG_D"]
    product_groups = ["PG_1", "PG_2", "PG_3", "PG_4", "PG_5"]

    # Demand per product group (units)
    demand = pd.DataFrame({
        "product_group": product_groups,
        "demand_units": rng.integers(12, 35, size=len(product_groups)),
    })

    # Capacity per space group (available hours)
    cap = pd.DataFrame({
        "space_group": space_groups,
        "capacity_hours": rng.integers(220, 360, size=len(space_groups)).astype(float),
    })

    # Processing time per unit (hours) for each (PG, SG)
    rows = []
    for pg in product_groups:
        for sg in space_groups:
            rows.append((pg, sg, float(rng.uniform(4.0, 14.0))))
    proc = pd.DataFrame(rows, columns=["product_group", "space_group", "hours_per_unit"])

    # Baseline assignment (where work is currently done), used for movement/reinstall cost
    baseline = pd.DataFrame({
        "product_group": product_groups,
        "baseline_space_group": rng.choice(space_groups, size=len(product_groups)),
    })

    return {
        "demand": demand,
        "capacity": cap,
        "processing": proc,
        "baseline": baseline,
    }
