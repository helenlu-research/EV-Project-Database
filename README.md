[![DOI](https://zenodo.org/badge/804596288.svg)](https://zenodo.org/doi/10.5281/zenodo.11251877)

# EV-Project Wildfire Case Study Repository

## Overview

This repository contains the code, input data, and representative outputs for a Sonoma County wildfire case study on electric-vehicle evacuation planning under disrupted road and charging infrastructure.

The study is organized around stochastic network optimization models implemented in Pyomo and solved with Gurobi. Across the notebooks in this repository, the workflow studies how evacuation outcomes change under:

- different initial EV battery-charge distributions,
- different effective charging speeds,
- different charging-station installation budgets,
- fixed or staggered evacuation release patterns, and
- stochastic road and charging-capacity disruptions.

Recent updates to the repository add a staggered-start evacuation extension and supporting plotting/utilities, but this README is written as the canonical guide to the full repository.

## Study logic

At a high level, the repository follows this logic:

1. Build the Sonoma transportation and evacuation network from the input files.
2. Generate initial EV counts by node and battery-charge level.
3. Construct stochastic disruption scenarios for road and charging capacity.
4. Solve a Pyomo optimization model that allocates charging capacity and routes EVs over time.
5. Save decision-variable outputs and summary metrics for each scenario family.
6. Compare results across battery distributions, charging-speed assumptions, and staggered evacuation-release profiles.

## Repository structure

```text
EV-Project-Database/
├── README.md
├── code/
│   ├── car_number_initialization_normal.ipynb
│   ├── car_number_initialization_half_speed.ipynb
│   ├── wildfire_even_sensitivity.ipynb
│   ├── half_speed_sensitivity.ipynb
│   ├── double_speed_sensitivity.ipynb
│   ├── staggered_evacuation_sensitivity.ipynb
│   ├── distributions.py
│   ├── optimization_result_plotting.py
│   └── archive/
├── input/
│   ├── arcs_sonoma_15min.xlsx
│   ├── nodes_sonoma_15min.xlsx
│   ├── safe_nodes_15min.xlsx
│   ├── charging_cap_damFac_3hrs.csv
│   ├── road_cap_damFac_3hrs.csv
│   └── car_charge_distribution/
└── output/
    ├── car_charge_distribution/
    └── numerical_results/
```

## Main code components

### 1. Initialization notebooks

These notebooks generate the initial number of EVs at each node and charge level.

- `code/car_number_initialization_normal.ipynb`
  Creates three initial battery-distribution cases for the normal charging-speed setting:
  - `even_battery`
  - `high_battery`
  - `low_battery`
- `code/car_number_initialization_half_speed.ipynb`
  Creates the corresponding initial battery-distribution cases for the half-speed charging setting.

Outputs are written to `output/car_charge_distribution/`. Matching CSV files used by the optimization notebooks are also stored in `input/car_charge_distribution/`.

### 2. Charging-speed sensitivity notebooks

These notebooks implement the main optimization model under different charging-speed assumptions.

- `code/wildfire_even_sensitivity.ipynb`
  Base wildfire case-study workflow for normal charging speed.
- `code/half_speed_sensitivity.ipynb`
  Variant for slower charging, with a finer charge-level discretization.
- `code/double_speed_sensitivity.ipynb`
  Variant for faster charging.

Each notebook loops over:

- battery-distribution assumptions: `even_battery`, `high_battery`, `low_battery`
- budget levels: `1, 4, 7, 10, 13, 16, 19` million dollars
- evacuation time window: currently `T = 2` hours in the saved sensitivity runs

The notebooks save both detailed decision outputs and summary result tables.

### 3. Staggered-start evacuation notebook

- `code/staggered_evacuation_sensitivity.ipynb`

This notebook extends the base model by changing the evacuation release profile over time. Instead of assuming all EVs are ready to evacuate immediately, it generates time-distributed releases `R_ilt` and compares:

- `early_evac`
- `uniform_evac`
- `delayed_evac`

The default matched comparison in this notebook uses:

- budget `B = 10` million dollars
- evacuation time window `T = 2` hours
- total EV demand `73.203` thousand vehicles

The staggered-start workflow writes scenario-specific output folders under `output/numerical_results/staggered_start/` and a summary table named `staggered_scenario_results_B10_T2.csv`.

### 4. Reusable Python modules

- `code/distributions.py`
  Contains helper functions for generating staggered evacuation-release distributions using Beta distributions. It also includes validation and summary-statistics utilities.
- `code/optimization_result_plotting.py`
  Contains plotting utilities for:
  - installed charging-capacity maps,
  - cumulative evacuation curves,
  - performance-comparison charts across scenarios.

## Input data

The maintained Sonoma case-study notebooks use the following inputs:

- `input/nodes_sonoma_15min.xlsx`
  Node-level attributes including coordinates and EV totals.
- `input/arcs_sonoma_15min.xlsx`
  Directed or undirected network connections used to build the transportation graph.
- `input/safe_nodes_15min.xlsx`
  Indicator table identifying safe destinations.
- `input/charging_cap_damFac_3hrs.csv`
  Scenario-based charging-capacity damage factors.
- `input/road_cap_damFac_3hrs.csv`
  Scenario-based road-capacity damage factors.
- `input/car_charge_distribution/*.csv`
  Initial EV distributions by node and charge level.

## Optimization model summary

The core notebooks share the same modeling structure.

### Sets and time structure

- Nodes and arcs are built from the Sonoma network files.
- Safe nodes are filtered from `safe_nodes_15min.xlsx`.
- Charge levels are discretized and indexed by `L`.
- Time is represented in quarter-hour steps through `range(4*T + 1)`.
- Stochastic disruption scenarios are indexed from the damage-factor input files.

### Main decision variables

The notebooks save four primary outputs:

- `s_values.csv`
  Charging capacity installed at each node.
- `x_values.csv`
  Vehicle flow on arcs over charge level, time, and disruption scenario.
- `y_values.csv`
  Vehicle counts remaining in the network state variables.
- `z_values.csv`
  Vehicle counts accumulated at safe nodes.

### Objective and metrics

The optimization model uses scenario probabilities and solves for an allocation/routing plan that maximizes evacuation performance under disruption, subject to:

- charging-capacity installation budget constraints,
- road-capacity constraints,
- charging-capacity constraints,
- flow-balance constraints, and
- battery-charge transition logic.

After solving, the notebooks compute:

- expected number of evacuated EVs,
- average evacuation time among successfully evacuated EVs,
- average evacuation time across all EVs,
- total runtime.

## Code and data flow

The repository’s main workflow can be read as the following pipeline.

### A. Build initial charge distributions

1. Read node-level EV totals from `input/nodes_sonoma_15min.xlsx`.
2. Assign EVs across charge levels for one of the battery-distribution assumptions.
3. Write charge-distribution CSVs to `output/car_charge_distribution/`.
4. Use the corresponding files in `input/car_charge_distribution/` as model input for optimization notebooks.

### B. Build scenario-dependent network parameters

1. Read road and charging damage factors from:
   - `input/road_cap_damFac_3hrs.csv`
   - `input/charging_cap_damFac_3hrs.csv`
2. Convert these tables into time- and scenario-indexed parameters.
3. Combine them with the network topology and initial EV distributions.

### C. Solve the optimization model

1. Choose a charging-speed notebook or the staggered-start notebook.
2. Set key parameters such as:
   - `L` for charge-level resolution,
   - `T` for evacuation horizon in hours,
   - `B` for installation budget,
   - battery-distribution case or staggered-release scenario.
3. Solve the Pyomo model with Gurobi.
4. Export detailed decision-variable CSVs to a scenario-specific output folder.

### D. Summarize and compare results

1. Aggregate the detailed outputs into performance metrics.
2. Save sensitivity-analysis summary tables for each scenario family.
3. For staggered-start comparisons, use `optimization_result_plotting.py` to generate:
   - charging-capacity maps,
   - cumulative evacuation curves,
   - cross-scenario performance bar charts.

## Output organization

Representative outputs included in the repository are grouped under:

- `output/car_charge_distribution/`
  Generated initial EV charge distributions.
- `output/numerical_results/even_battery_normal_speed/`
- `output/numerical_results/high_battery_normal_speed/`
- `output/numerical_results/low_battery_normal_speed/`
- `output/numerical_results/high_battery_half_speed/`
- `output/numerical_results/low_battery_half_speed/`
- `output/numerical_results/high_battery_double_speed/`
- `output/numerical_results/low_battery_double_speed/`
- `output/numerical_results/staggered_start/`

Within a scenario folder, the standard output files are:

- `s_values.csv`
- `x_values.csv`
- `y_values.csv`
- `z_values.csv`

Some folders such as `output/numerical_results/even_battery_half_speed copy/` and `output/numerical_results/even_battery_double_speed copy/` appear to be legacy or duplicated result directories and should not be treated as the primary maintained outputs.

## Running the repository

### Requirements

This repository does not currently ship with a pinned `requirements.txt` or environment file. To run the maintained notebooks, you will need a Python environment that includes at least:

- `jupyter`
- `numpy`
- `pandas`
- `scipy`
- `matplotlib`
- `seaborn`
- `networkx`
- `pyomo`
- `gurobipy`
- `cartopy`
- `openpyxl`

All maintained optimization notebooks use Gurobi through Pyomo:

- `pyomo.environ`
- `pyomo.opt`
- `gurobipy`

You will need a working Gurobi installation and a valid license. Some notebooks contain an example `GRB_LICENSE_FILE` path that should be updated for your local machine or removed if your environment is already configured correctly.

### Recommended execution order

Because the notebooks use relative paths such as `../input/` and `../output/`, run them with the working directory set to `code/`.

For the charging-speed sensitivity workflow:

1. Run `code/car_number_initialization_normal.ipynb` for normal or double-speed cases.
2. Run `code/car_number_initialization_half_speed.ipynb` for half-speed cases.
3. Run one of:
   - `code/wildfire_even_sensitivity.ipynb`
   - `code/half_speed_sensitivity.ipynb`
   - `code/double_speed_sensitivity.ipynb`
4. Inspect scenario folders and summary CSV outputs under `output/numerical_results/`.

For the staggered-start workflow:

1. Ensure the base Sonoma inputs and initial charge distributions are present.
2. Run `code/staggered_evacuation_sensitivity.ipynb`.
3. Review:
   - staggered scenario result folders under `output/numerical_results/staggered_start/`
   - summary table `staggered_scenario_results_B10_T2.csv`
4. Run the plotting cells in the notebook to generate comparison figures using `code/optimization_result_plotting.py`.

## Notes on maintained versus legacy material

The primary maintained workflow is the Sonoma wildfire case study described above. A few notebooks in the repository remain exploratory or archival:

- `code/archive/`
- notebooks that still reference older paths such as `../data_wildfire/` or `../fig_wildfire/`

These files may still be useful for reference, but they should not be treated as the primary reproducible pipeline for the repository.

## Citation

If you use this repository, please cite the associated project record linked by the DOI badge above.
