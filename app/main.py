# app/main.py
from __future__ import annotations

import streamlit as st
import pandas as pd

from app.ui_config import (
    DEFAULT_PARAMS,
    DEFAULT_PENALTY_WEIGHTS,
    DEFAULT_POSITIONS,
    DEFAULT_BAY_SIZES,
    DEFAULT_REINSTALL_COSTS,
    DEFAULT_SWITCHES,
)
from app.sample_data import make_synthetic_instance
from app.optimizer import OptimizeInputs, solve_lp


st.set_page_config(page_title="LP Utilization Optimizer (Public Demo)", layout="wide")
st.title("LP Utilization Optimizer (Public Demo)")

# --- Initialize session state ---
def _init_state():
    for k, v in DEFAULT_PARAMS.items():
        st.session_state.setdefault(k, v)

    st.session_state.setdefault("penalty_weights", DEFAULT_PENALTY_WEIGHTS.copy())
    st.session_state.setdefault("switches", DEFAULT_SWITCHES.copy())
    st.session_state.setdefault("positions", DEFAULT_POSITIONS.copy())
    st.session_state.setdefault("bay_sizes", DEFAULT_BAY_SIZES.copy())
    st.session_state.setdefault("reinstall_costs", DEFAULT_REINSTALL_COSTS.copy())

_init_state()

# --- Sidebar: scalar parameters ---
st.sidebar.header("Parameters")
st.session_state.BackEndLoading = st.sidebar.number_input(
    "BackEnd Loading", min_value=0.0, max_value=5.0,
    value=float(st.session_state.BackEndLoading), step=0.1
)
st.session_state.FactoryHours = st.sidebar.number_input(
    "Factory Hours", min_value=0.0, max_value=1000.0,
    value=float(st.session_state.FactoryHours), step=1.0
)
st.session_state.FactoryDays = st.sidebar.number_input(
    "Factory Days", min_value=1, max_value=31,
    value=int(st.session_state.FactoryDays), step=1
)

st.session_state.movement_penalty_per_meter = st.sidebar.number_input(
    "Movement Penalty (per meter)", min_value=0.0, max_value=10.0,
    value=float(st.session_state.movement_penalty_per_meter), step=0.1
)
st.session_state.utilization_balance_penalty = st.sidebar.number_input(
    "Utilization Balance Penalty", min_value=0.0, max_value=50.0,
    value=float(st.session_state.utilization_balance_penalty), step=0.5
)
st.session_state.big_m = st.sidebar.number_input(
    "Big-M Constant", min_value=1000.0, max_value=10_000_000.0,
    value=float(st.session_state.big_m), step=100_000.0
)
st.session_state.excess_space_penalty_index = st.sidebar.number_input(
    "Excess Capacity Penalty Index", min_value=0.0, max_value=10.0,
    value=float(st.session_state.excess_space_penalty_index), step=0.1
)
st.session_state.unmet_demand_penalty = st.sidebar.number_input(
    "Unmet Demand Cost (per unit)", min_value=0.0, max_value=100.0,
    value=float(st.session_state.unmet_demand_penalty), step=1.0
)
st.session_state.reinstallation_penalty_index = st.sidebar.number_input(
    "Reinstallation Penalty Index", min_value=0.0, max_value=10.0,
    value=float(st.session_state.reinstallation_penalty_index), step=0.1
)

# --- Sidebar: penalty weights ---
st.sidebar.header("Penalty Weights")
pw = st.session_state["penalty_weights"]
for label, default_value in DEFAULT_PENALTY_WEIGHTS.items():
    pw[label] = st.sidebar.number_input(label, value=float(pw.get(label, default_value)), step=0.1)
st.session_state["penalty_weights"] = pw

# --- Sidebar: switches ---
st.sidebar.header("Switches")
sw = st.session_state["switches"]
sw["space_constraint"] = st.sidebar.checkbox("Space Constraint", value=bool(sw.get("space_constraint", True)))
sw["demands_scenario_test"] = st.sidebar.checkbox("Demands Scenario Test", value=bool(sw.get("demands_scenario_test", False)))
sw["space_group_numbay_test"] = st.sidebar.checkbox("Space Group NumBay Test", value=bool(sw.get("space_group_numbay_test", False)))
st.session_state["switches"] = sw

# --- Config tabs ---
st.header("Configuration")
tab1, tab2, tab3 = st.tabs(["🔧 Positions", "📐 Bay Sizes", "💰 Reinstallation Costs"])

with tab1:
    st.subheader("Configure Positions")
    pos = st.session_state["positions"]
    updated = {}
    for sg, (x, y) in pos.items():
        st.markdown(f"**{sg}**")
        c1, c2 = st.columns(2)
        with c1:
            nx = st.number_input(f"{sg} X", value=float(x), format="%.2f", key=f"{sg}_x")
        with c2:
            ny = st.number_input(f"{sg} Y", value=float(y), format="%.2f", key=f"{sg}_y")
        updated[sg] = (float(nx), float(ny))
    st.session_state["positions"] = updated

with tab2:
    st.subheader("Configure Bay Sizes")
    bays = st.session_state["bay_sizes"]
    updated = {}
    for sg, v in bays.items():
        updated[sg] = st.number_input(f"{sg} Bay Size", value=float(v), format="%.2f", key=f"{sg}_bay")
    st.session_state["bay_sizes"] = updated

with tab3:
    st.subheader("Configure Reinstallation Costs")
    rc = st.session_state["reinstall_costs"]
    updated = {}
    for sg, v in rc.items():
        updated[sg] = st.number_input(f"{sg} Reinstall Cost", value=float(v), format="%.2f", key=f"{sg}_cost")
    st.session_state["reinstall_costs"] = updated

# --- Data section ---
st.header("Synthetic Data (Public Demo)")
seed = st.number_input("Random seed", min_value=0, max_value=10_000, value=7, step=1)
instance = make_synthetic_instance(seed=int(seed))

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Demand**")
    st.dataframe(instance["demand"], use_container_width=True)
    st.markdown("**Capacity**")
    st.dataframe(instance["capacity"], use_container_width=True)

with c2:
    st.markdown("**Processing times (hours/unit)**")
    st.dataframe(instance["processing"].pivot(index="product_group", columns="space_group", values="hours_per_unit"),
                 use_container_width=True)
    st.markdown("**Baseline assignment**")
    st.dataframe(instance["baseline"], use_container_width=True)

# --- Run button (styled) ---
st.markdown("""
<style>
div.stButton > button {
    display: block;
    width: 100%;
    padding: 1em;
    font-size: 1.1em;
    font-weight: 700;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

st.header("Optimization")
run = st.button("Run Model")

if run:
    params = {k: float(st.session_state[k]) for k in DEFAULT_PARAMS.keys()}
    inp = OptimizeInputs(
        demand=instance["demand"],
        capacity=instance["capacity"],
        processing=instance["processing"],
        baseline=instance["baseline"],
        positions=st.session_state["positions"],
        bay_sizes=st.session_state["bay_sizes"],
        reinstall_costs=st.session_state["reinstall_costs"],
        switches=st.session_state["switches"],
        params=params,
        penalty_weights=st.session_state["penalty_weights"],
    )
    res = solve_lp(inp)

    kpis = res["kpis"]
    st.success(f"✅ Solved. Status: {kpis['status']}")
    st.write({
        "Objective": kpis["objective_value"],
        "Total unmet units": kpis["total_unmet_units"],
        "Avg utilization": kpis["avg_utilization"],
        "Max utilization": kpis["max_utilization"],
    })

    st.subheader("Utilization by Space Group")
    st.dataframe(res["utilization"], use_container_width=True)

    st.subheader("Allocation (units and hours)")
    st.dataframe(res["allocation"], use_container_width=True)

    st.subheader("Unmet demand (if any)")
    st.dataframe(res["unmet"], use_container_width=True)
