
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from graph_output import save_graph

# ── Zerve design constants ──────────────────────────────────────────────
BG_COLOR   = "#1D1D20"
TEXT_COLOR = "#fbfbff"
SEC_COLOR  = "#909094"

# 12 distinct, visually balanced month colours
MONTH_COLORS = [
    "#A1C9F4",  # Jan  – light blue
    "#FFB482",  # Feb  – orange
    "#8DE5A1",  # Mar  – green
    "#FF9F9B",  # Apr  – coral
    "#D0BBFF",  # May  – lavender
    "#ffd400",  # Jun  – gold
    "#1F77B4",  # Jul  – blue
    "#9467BD",  # Aug  – purple
    "#8C564B",  # Sep  – brown
    "#C49C94",  # Oct  – tan
    "#E377C2",  # Nov  – pink
    "#17b26a",  # Dec  – green (success)
]

MONTH_NAMES = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
]

# ── Aggregate food posts by ISO week ───────────────────────────────────
fp = food_df[food_df["is_food_post"] == True].copy()
fp["date"]    = pd.to_datetime(fp["date"])
fp["week"]    = fp["date"].dt.isocalendar().week.astype(int)
fp["month"]   = fp["date"].dt.month
fp["year"]    = fp["date"].dt.year

# Count alerts per (year, week) and get dominant month for each week
week_counts = (
    fp.groupby(["year", "week"])
    .agg(count=("msg_id", "count"), month=("month", lambda x: x.mode()[0]))
    .reset_index()
)

# Sort chronologically: year first, then week
week_counts = week_counts.sort_values(["year", "week"]).reset_index(drop=True)

# Build x-axis labels  e.g. "W01\n2023"
week_counts["label"] = week_counts.apply(
    lambda r: f"W{r['week']:02d}\n{r['year']}", axis=1
)

# ── Plot ────────────────────────────────────────────────────────────────
fig_week_month, ax_wm = plt.subplots(figsize=(22, 7))
fig_week_month.patch.set_facecolor(BG_COLOR)
ax_wm.set_facecolor(BG_COLOR)

x = np.arange(len(week_counts))
bar_colors = [MONTH_COLORS[m - 1] for m in week_counts["month"]]

bars_wm = ax_wm.bar(x, week_counts["count"], color=bar_colors,
                    width=0.8, edgecolor="none", zorder=2)

# ── Axis styling ────────────────────────────────────────────────────────
ax_wm.set_xlabel("Week of Year", color=SEC_COLOR, fontsize=11, labelpad=8)
ax_wm.set_ylabel("Food Alert Count", color=SEC_COLOR, fontsize=11, labelpad=8)
ax_wm.set_title("Food Alert Activity by Week of Year\nColoured by Month",
                color=TEXT_COLOR, fontsize=15, fontweight="bold", pad=16)

# Tick labels – show every ~4th week to avoid crowding
step = max(1, len(week_counts) // 30)
ax_wm.set_xticks(x[::step])
ax_wm.set_xticklabels(week_counts["label"].iloc[::step],
                      fontsize=7.5, color=SEC_COLOR, rotation=45, ha="right")
ax_wm.tick_params(axis="y", colors=SEC_COLOR, labelsize=9)
ax_wm.tick_params(axis="x", colors=SEC_COLOR, length=0)

# Subtle horizontal grid
ax_wm.yaxis.grid(True, color="#3a3a3f", linewidth=0.5, zorder=0)
ax_wm.set_axisbelow(True)

for _sp in ax_wm.spines.values():
    _sp.set_visible(False)

# ── Legend: one patch per month that actually appears in the data ───────
present_months = sorted(week_counts["month"].unique())
legend_patches = [
    mpatches.Patch(facecolor=MONTH_COLORS[m - 1], label=MONTH_NAMES[m - 1])
    for m in present_months
]

ax_wm.legend(
    handles=legend_patches,
    title="Month",
    title_fontsize=9,
    fontsize=8,
    loc="upper left",
    frameon=True,
    framealpha=0.25,
    facecolor=BG_COLOR,
    edgecolor=SEC_COLOR,
    labelcolor=TEXT_COLOR,
    ncol=2,
    bbox_to_anchor=(0.0, 1.0),
)

plt.tight_layout()
if save_graph(
    fig_week_month,
    "weekly_alerts",
    "food_alerts_by_week_year_colored_by_month.png",
    facecolor=BG_COLOR,
):
    plt.close(fig_week_month)
else:
    plt.show()

print(f"Chart rendered: {len(week_counts)} weeks across "
      f"{week_counts['year'].nunique()} year(s), "
      f"{len(present_months)} months present.")
print(week_counts[["label","month","count"]].to_string(index=False))
