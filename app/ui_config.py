# app/ui_config.py
from __future__ import annotations

# Default toggles (safe/public)
DEFAULT_SWITCHES = {
    "space_constraint": True,
    "demands_scenario_test": False,
    "space_group_numbay_test": False,
}

# Default scalar parameters (safe/public)
DEFAULT_PARAMS = {
    "BackEndLoading": 1.0,
    "FactoryHours": 160.0,
    "FactoryDays": 20,
    "movement_penalty_per_meter": 0.2,
    "utilization_balance_penalty": 1.0,
    "big_m": 100000.0,
    "excess_space_penalty_index": 0.5,
    "unmet_demand_penalty": 25.0,
    "reinstallation_penalty_index": 1.0,
}

# Penalty weights as a named bundle (your original pattern)
DEFAULT_PENALTY_WEIGHTS = {
    "Unmet demand weight": 1.0,
    "Movement weight": 1.0,
    "Reinstallation weight": 1.0,
    "Utilization balance weight": 1.0,
    "Excess space weight": 1.0,
}

# Layout defaults (positions = for movement distance calc)
DEFAULT_POSITIONS = {
    "SG_A": (0.0, 0.0),
    "SG_B": (10.0, 0.0),
    "SG_C": (0.0, 8.0),
    "SG_D": (10.0, 8.0),
}

# Bay sizes (space capacity proxy)
DEFAULT_BAY_SIZES = {
    "SG_A": 12.0,
    "SG_B": 10.0,
    "SG_C": 8.0,
    "SG_D": 6.0,
}

# Reinstallation costs (per move / per assigned unit scaling)
DEFAULT_REINSTALL_COSTS = {
    "SG_A": 1.0,
    "SG_B": 1.2,
    "SG_C": 1.5,
    "SG_D": 1.8,
}
