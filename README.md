# LP Utilization Optimizer (Public Demo)

A public, IP-safe Streamlit dashboard demonstrating a **linear programming (LP)** approach to equipment/workload reallocation under operational constraints.

This repo uses **synthetic data only** and an **open-source solver (PuLP + CBC)**.

## What it does
- Generates a synthetic demand/capacity scenario
- Lets you edit:
  - penalty weights
  - space-group coordinates (for movement distance cost)
  - bay sizes (space proxy)
  - reinstallation costs
- Solves an LP to allocate product-group demand across space groups:
  - respects capacity constraints
  - optionally respects a space constraint proxy
  - penalizes unmet demand
  - penalizes movement and reinstallation costs
  - includes a utilization balancing penalty

## Run locally
```bash
python -m venv .venv
# activate venv
pip install -r requirements.txt
streamlit run app/main.py
