"""
optimization_result_plotting.py

Unified plotting module for:
1. Installed charging capacity maps (Cartopy)
2. Cumulative evacuation curves
3. Performance comparison plots

Designed for staggered evacuation experiments.

Author: Helen Lu
Date: 2026-05-21
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import seaborn as sns

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import Normalize
import matplotlib.cm as cm
import matplotlib as mpl
from matplotlib.pyplot import rc_context
from matplotlib.ticker import FormatStrFormatter


# =========================
# --- GLOBAL STYLE --------
# =========================

COMPARISON_COLORS = {
    "base_case": "#222222",
    "early_evac": "#1b9e77",
    "uniform_evac": "#4c78a8",
    "delayed_evac": "#d95f02",
}

COMPARISON_MARKERS = {
    "base_case": "o",
    "early_evac": "s",
    "uniform_evac": "^",
    "delayed_evac": "D",
}


# =========================
# --- GRAPH UTILITIES -----
# =========================

def build_graph(df_node, df_arc):
    G = nx.Graph()
    nodes = df_node["Nodes"].astype(int).tolist()
    G.add_nodes_from(nodes)

    for _, row in df_arc.iterrows():
        G.add_edge(int(row["From"]), int(row["To"]))

    return G


def get_positions(df_node):
    pos = {}
    for _, row in df_node.iterrows():
        pos[int(row["Nodes"])] = (row["Long"], row["Lat"])
    return pos


# =========================
# --- CAPACITY MAP --------
# =========================

def plot_capacity_map(
    df_node,
    df_arc,
    df_charcap,
    scenario_name="Scenario",
    save_path=None,
    coords=(-123.31, -121.98, 37.95, 38.86),
    vmin=None,
    vmax=None,
    cmap="vlag",
):
    plt.close('all')
    G = build_graph(df_node, df_arc)
    pos = get_positions(df_node)

    cap_dict = df_charcap.set_index("Nodes")["CharCap"].to_dict()
    nodes = list(G.nodes())
    node_values = np.array([cap_dict.get(n, 0.0) for n in nodes])

    if vmin is None:
        vmin = node_values.min()
    if vmax is None:
        vmax = node_values.max()

    norm = Normalize(vmin=vmin, vmax=vmax)

    # fig = plt.figure(figsize=(10, 7))
    # ax = plt.axes(projection=ccrs.Mercator())
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Mercator())
    min_lon, max_lon, min_lat, max_lat = coords
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())

    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.add_feature(cfeature.LAND, alpha=0.1)
    ax.add_feature(cfeature.OCEAN, alpha=0.05)

    # edges
    for u, v in G.edges():
        ax.plot(
            [pos[u][0], pos[v][0]],
            [pos[u][1], pos[v][1]],
            color="gray",
            linewidth=1,
            alpha=0.6,
            transform=ccrs.PlateCarree()
        )

    # nodes
    cmap_obj=sns.color_palette(cmap, as_cmap=True)
    sc = ax.scatter(
        [pos[n][0] for n in nodes],
        [pos[n][1] for n in nodes],
        c=node_values,
        cmap=cmap_obj,
        norm=norm,
        s=180,
        edgecolor=None,
        transform=ccrs.PlateCarree(),
        zorder=3,
    )

    # labels
    for n in nodes:
        x, y = pos[n]
        val = cap_dict.get(n, 0.0)
        ax.text(x, y + 0.015, f"{val:.3f}",
                fontsize=10, ha="center",
                transform=ccrs.PlateCarree())
        ax.text(x, y, str(n),
            fontsize=10, ha="center", va="center",
            color="black", fontweight="bold",
            transform=ccrs.PlateCarree(),
            zorder=5)

    cbar = plt.colorbar(sc, ax=ax, fraction=0.035, pad=0.04, shrink=0.3)
    cbar.set_label("Charging capacity (thousand cars)")

    ax.set_title(f"{scenario_name}\nInstalled charging capacity")

    # ax.set_xlim(min_lon, max_lon)
    # ax.set_ylim(min_lat, max_lat)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()
    return fig, ax


def plot_capacity_from_folder(
    result_folder,
    df_node,
    df_arc,
    scenario_name=None,
    save_dir="../output/figures",
    global_vmin=None,
    global_vmax=None,
):
    s_path = os.path.join(result_folder, "s_values.csv")
    df_charcap = pd.read_csv(s_path)

    if scenario_name is None:
        scenario_name = os.path.basename(result_folder)

    os.makedirs(save_dir, exist_ok=True)

    vmax = global_vmax if global_vmax is not None else df_charcap["CharCap"].max()
    vmin = global_vmin if global_vmin is not None else 0

    save_path = os.path.join(save_dir, f"{scenario_name}_capacity.png")

    return plot_capacity_map(
        df_node, df_arc, df_charcap,
        scenario_name=scenario_name,
        save_path=save_path,
        vmax=vmax,
        vmin=vmin
    )


def plot_capacity_multiple(
    result_folders,
    df_node,
    df_arc,
    global_vmin=None,
    global_vmax=None,
    save_dir="../output/figures"
):
    if global_vmax is not None:
        vmax = global_vmax
    else:
        vmax = 0
        for folder in result_folders.values():
            df = pd.read_csv(os.path.join(folder, "s_values.csv"))
            vmax = max(vmax, df["CharCap"].max())
    vmin = global_vmin if global_vmin is not None else 0
    

    figs = {}
    for name, folder in result_folders.items():
        figs[name] = plot_capacity_from_folder(
            folder, df_node, df_arc,
            scenario_name=name,
            save_dir=save_dir,
            global_vmin=vmin,
            global_vmax=vmax
        )
    return figs


# =========================
# --- EVAC CURVE ----------
# =========================

def expected_cumulative_curve(result_folder, N_s, prob_dict):
    df_y = pd.read_csv(os.path.join(result_folder, "y_values.csv"))
    df_z = pd.read_csv(os.path.join(result_folder, "z_values.csv"))

    safe_nodes = set(int(n) for n in N_s)

    combined = pd.concat([
        df_y[["Nodes", "Times", "Scenarios", "NumCars"]],
        df_z[["Nodes", "Times", "Scenarios", "NumCars"]],
    ])

    combined["Nodes"] = combined["Nodes"].astype(int)
    combined = combined[combined["Nodes"].isin(safe_nodes)]

    grouped = combined.groupby(["Scenarios", "Times"], as_index=False)["NumCars"].sum()
    grouped["Prob"] = grouped["Scenarios"].map(prob_dict).fillna(0.0)

    grouped["Expected"] = grouped["NumCars"] * grouped["Prob"]

    result = grouped.groupby("Times", as_index=False)["Expected"].sum()
    result["Hours"] = result["Times"] / 4

    return result.sort_values("Times")


# Helper function
SCENARIO_LABELS = {
    "base_case": "Base case",
    "early_evac": "Early staggered",
    "uniform_evac": "Uniform staggered",
    "delayed_evac": "Delayed staggered",
}

def clean_label(name):
    return SCENARIO_LABELS.get(name, name)

def plot_cumulative_curve(
    result_folders,
    N_s,
    prob_dict,
    Total_cars,
    save_path=None,
    scenario_labels=None,
    scenario_order=None,
):
    fig, ax = plt.subplots(figsize=(7, 4.5))

    scenario_names = (
        scenario_order if scenario_order is not None
        else list(result_folders.keys())
    )

    for name in scenario_names:
        folder = result_folders[name]
        curve = expected_cumulative_curve(folder, N_s, prob_dict)

        label = (
            scenario_labels.get(name, name)
            if scenario_labels is not None
            else clean_label(name)
        )

        ax.plot(
            curve["Hours"],
            curve["Expected"],
            label=label,
            marker=COMPARISON_MARKERS.get(name, "o"),
            color=COMPARISON_COLORS.get(name, None),
            linewidth=2,
        )

    ax.axhline(Total_cars, linestyle="--", color="red", label="Total EVs")

    ax.set_xlabel("Time (hours)")
    ax.set_ylabel("Expected evacuated EVs")
    ax.set_title("Cumulative evacuation comparison")
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()
    return fig, ax


# =========================
# --- PERFORMANCE ---------
# =========================

def compute_metrics(result_folder, N_s, prob_dict, Total_cars, T):
    curve = expected_cumulative_curve(result_folder, N_s, prob_dict)

    num_evac = curve["Expected"].iloc[-1]

    increments = curve["Expected"].diff().fillna(curve["Expected"])
    weighted_time = (curve["Times"] * increments).sum()

    avg_time = weighted_time / num_evac if num_evac > 0 else 0
    avg_time_all = (weighted_time + (4*T)*(Total_cars-num_evac)) / Total_cars

    return num_evac, avg_time, avg_time_all


def plot_performance(
    result_folders,
    N_s,
    prob_dict,
    Total_cars,
    T,
    save_path=None,
    scenario_order=None,
    scenario_labels=None,
):
    """
    Universal performance plot:
    - works with ANY set of scenarios
    - optional ordering
    - optional label mapping
    - automatically detects base_case if present
    """

    rows = []

    for name, folder in result_folders.items():
        num, avg, avg_all = compute_metrics(folder, N_s, prob_dict, Total_cars, T)
        rows.append({
            "Scenario": name,
            "NumEvac": num,
            "AvgTime": avg # avg evac time of successfully evacuated EVs across stochastic scenarios
        })

    df = pd.DataFrame(rows)
    df["AvgTime"] = df["AvgTime"] / 4   # convert to hours

    # =========================
    # --- ORDERING (FLEXIBLE) --
    # =========================
    if scenario_order is not None:
        # user-specified order
        df["Scenario"] = pd.Categorical(
            df["Scenario"],
            categories=scenario_order,
            ordered=True
        )
        df = df.sort_values("Scenario")
    else:
        # default: keep insertion order
        df = df.set_index("Scenario").loc[result_folders.keys()].reset_index()

    # =========================
    # --- LABELS (FLEXIBLE) ---
    # =========================
    def get_label(name):
        if scenario_labels:
            return scenario_labels.get(name, name)
        return name.replace("_", " ").title()

    labels = [get_label(s) for s in df["Scenario"]]

    # =========================
    # --- PLOTTING ------------
    # =========================
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    bars1 = axes[0].bar(labels, df["NumEvac"])
    axes[0].set_title("Evacuated EVs (thousand cars)")
    axes[0].grid(axis="y", alpha=0.3)
    axes[0].set_ylim(0, df['NumEvac'].max()*1.1)
    axes[0].set_xticklabels(axes[0].get_xticklabels(), fontsize=10, rotation=45, ha='right')

    bars2 = axes[1].bar(labels, df["AvgTime"])
    axes[1].set_title("Average evacuation time (hours, successful EVs)")
    axes[1].grid(axis="y", alpha=0.3)
    axes[1].set_ylim(0, df['AvgTime'].max()*1.1)
    axes[1].set_xticklabels(axes[1].get_xticklabels(), fontsize=10, rotation=45, ha='right')
    axes[1].yaxis.set_major_formatter(FormatStrFormatter('%.2f'))


    # =========================
    # --- BASE CASE COMPARISON
    # =========================
    if "base_case" in df["Scenario"].values:
        base_row = df[df["Scenario"] == "base_case"].iloc[0]

        for bars, metric, ax in zip(
            [bars1, bars2],
            ["NumEvac", "AvgTime"],
            axes
        ):
            base_val = base_row[metric]

            for bar, val in zip(bars, df[metric]):
                if base_val != 0:
                    delta = 100 * (val - base_val) / base_val
                    ax.text(
                        bar.get_x() + bar.get_width()/2,
                        bar.get_height(),
                        f"{delta:+.1f}%",
                        ha="center",
                        va="bottom",
                        fontsize=10,
                    )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    plt.show()
    return fig, axes