import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from chart_json import write_chart_spec
from graph_output import save_export_or_interactive

BG = "#1D1D20"
PRIMARY = "#fbfbff"
SEC = "#909094"
GRID = "#333333"
SPINE = "#444444"
COLORS = ["#8DE5A1", "#A1C9F4", "#FFB482", "#FF9F9B", "#D0BBFF"]
GOLD = "#FFD400"

plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "text.color": PRIMARY,
        "axes.labelcolor": PRIMARY,
        "xtick.color": PRIMARY,
        "ytick.color": PRIMARY,
        "axes.edgecolor": SPINE,
        "grid.color": GRID,
        "font.family": "sans-serif",
    }
)

DOW_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DOW_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def style_ax(ax, *, grid_axis="y"):
    for spine in ax.spines.values():
        spine.set_edgecolor(SPINE)
    ax.tick_params(colors=PRIMARY, labelsize=9)
    if grid_axis == "y":
        ax.yaxis.grid(True, linestyle="--", alpha=0.25)
    elif grid_axis == "x":
        ax.xaxis.grid(True, linestyle="--", alpha=0.25)
    elif grid_axis == "both":
        ax.grid(True, linestyle="--", alpha=0.2)
    ax.set_axisbelow(True)


def cyclical_pair(values, period):
    angle = 2 * np.pi * values / period
    return np.c_[np.sin(angle), np.cos(angle)]


def choose_k(x_scaled, base_df):
    rows = []
    for k in range(2, 6):
        model = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = model.fit_predict(x_scaled)
        sil = silhouette_score(x_scaled, labels)
        label_counts = pd.Series(labels).value_counts(normalize=True)
        probe = base_df[["hour", "day_of_week_n"]].copy()
        probe["label"] = labels
        names = []
        for label in sorted(probe["label"].unique()):
            sub = probe[probe["label"] == label]
            names.append(cluster_name(float(sub["hour"].mean()), float(sub["day_of_week_n"].mean())))
        rows.append(
            {
                "k": k,
                "silhouette": sil,
                "min_share": float(label_counts.min()),
                "semantic_duplicate": len(set(names)) < len(names),
            }
        )

    score_df = pd.DataFrame(rows)
    best_sil = score_df["silhouette"].max()

    # Prefer the smallest K that is close to the best score.
    # This avoids splitting one real pattern into two lookalike clusters.
    candidates = score_df[
        (score_df["silhouette"] >= best_sil - 0.03)
        & (score_df["min_share"] >= 0.12)
        & (~score_df["semantic_duplicate"])
    ]
    chosen_k = int(candidates["k"].min()) if not candidates.empty else int(
        score_df.sort_values(["semantic_duplicate", "silhouette", "min_share"], ascending=[True, False, False]).iloc[0]["k"]
    )
    return score_df, chosen_k


def cluster_name(avg_hour, avg_day):
    if avg_hour < 15:
        return "Lunch / early afternoon"
    return "Evening"


def cluster_explanation(name):
    if name == "Lunch / early afternoon":
        return (
            "Possible explanation: catered lunches, seminars, and daytime events "
            "leave food around midday, so posts spike before and after lunch."
        )
    return (
        "Possible explanation: classes, meetings, club activities, socials, and "
        "other events commonly end in the evening and create leftover food posts."
    )


def top_labels(series, labels, top_n=2):
    counts = series.value_counts().head(top_n)
    return ", ".join(labels[idx] if isinstance(idx, (int, np.integer)) else idx for idx in counts.index)


print("=" * 65)
print("CLUSTERING - Buffet Alert Timing Patterns")
print("=" * 65)

cl_df = food_df[food_df["is_food_post"] == True].copy()

print(f"\nFood posts used : {len(cl_df):,}")
print("Clustering focus: hour of day + day of week")
print("Month is kept for explanation only, not for building clusters.")
print("Reason         : the old version split one real timing pattern into lookalike seasonal clusters.")

# Use only interpretable timing features for clustering.
x_raw = np.c_[
    cyclical_pair(cl_df["hour"].to_numpy(), 24),
    cyclical_pair(cl_df["day_of_week_n"].to_numpy(), 7),
]
x_scaled = StandardScaler().fit_transform(x_raw)

score_df, _best_k_auto = choose_k(x_scaled, cl_df)
best_k = 2

model = KMeans(n_clusters=best_k, random_state=42, n_init=20)
cl_df["cluster_raw"] = model.fit_predict(x_scaled)

raw_summary = (
    cl_df.groupby("cluster_raw")
    .agg(
        size=("cluster_raw", "size"),
        avg_hour=("hour", "mean"),
        avg_day=("day_of_week_n", "mean"),
    )
    .sort_values(["avg_hour", "avg_day"])
    .reset_index()
)

cluster_order = raw_summary["cluster_raw"].tolist()
cluster_map = {old: new for new, old in enumerate(cluster_order)}
cl_df["cluster"] = cl_df["cluster_raw"].map(cluster_map)

summary_rows = []
for c in range(best_k):
    sub = cl_df[cl_df["cluster"] == c]
    avg_hour = float(sub["hour"].mean())
    avg_day = float(sub["day_of_week_n"].mean())
    name = cluster_name(avg_hour, avg_day)
    hour_counts = sub["hour"].value_counts().sort_values(ascending=False)
    peak_hours = ", ".join(f"{int(h):02d}:00" for h in hour_counts.head(3).index)
    top_days = top_labels(sub["day_of_week_n"], DOW_SHORT, top_n=2)
    top_months = top_labels(sub["month"] - 1, MONTH_SHORT, top_n=2)
    weekend_share = float(sub["is_weekend"].mean() * 100)
    summary_rows.append(
        {
            "cluster": c,
            "name": name,
            "size": len(sub),
            "share_pct": len(sub) / len(cl_df) * 100,
            "avg_hour": avg_hour,
            "avg_day": avg_day,
            "peak_hours": peak_hours,
            "top_days": top_days,
            "weekend_share": weekend_share,
            "top_months": top_months,
            "explanation": cluster_explanation(name),
        }
    )

summary_df = pd.DataFrame(summary_rows).sort_values(["avg_hour", "avg_day"]).reset_index(drop=True)
summary_df["color"] = [COLORS[i % len(COLORS)] for i in range(len(summary_df))]

print(f"\nChosen K       : {best_k}")
print("Rule used      : force two clusters so the two evening patterns are combined.")
print("Why            : the previous split into early-week evening and late-week evening was valid, but you asked for one simpler evening cluster.")

print("\nRESULTS")
print("-" * 65)
for row in summary_df.itertuples(index=False):
    print(f"{row.name}  ({row.share_pct:.1f}% of food posts)")
    print(f"  Peak hours        : {row.peak_hours}")
    print(f"  Strongest days    : {row.top_days}")
    print(f"  Weekend share     : {row.weekend_share:.1f}%")
    print(f"  Strongest months  : {row.top_months}")
    print(f"  Interpretation    : {row.explanation}")

overall_lines = []
if any(summary_df["name"] == "Lunch / early afternoon"):
    overall_lines.append(
        "One clear cluster is a lunch-centered pattern, which is a sensible campus-food behavior."
    )
if any(summary_df["name"] == "Evening"):
    overall_lines.append(
        "All later-day alerts are now combined into one evening cluster, so the result is easier to read at a glance."
    )
overall_lines.append(
    "Month still matters in the summaries, but it no longer forces the model to create duplicate-looking clusters."
)

print("\nOVERALL INTERPRETATION")
print("-" * 65)
for line in overall_lines:
    print(f"- {line}")


# Chart 1: silhouette score by K
fig1, ax1 = plt.subplots(figsize=(8.5, 5))
fig1.patch.set_facecolor(BG)
ax1.set_facecolor(BG)
bars = ax1.bar(score_df["k"], score_df["silhouette"], color=COLORS[1], width=0.65)
for bar, row in zip(bars, score_df.itertuples(index=False)):
    if int(row.k) == best_k:
        bar.set_color(GOLD)
    ax1.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.006,
        f"{row.silhouette:.3f}",
        ha="center",
        va="bottom",
        fontsize=8,
        color=PRIMARY,
    )
ax1.set_xticks(score_df["k"])
ax1.set_xlabel("Number of clusters (K)", fontsize=11, color=PRIMARY)
ax1.set_ylabel("Silhouette score", fontsize=11, color=PRIMARY)
ax1.set_title("Cluster choice - simpler K wins when scores are close", fontsize=13, color=PRIMARY, pad=12)
style_ax(ax1, grid_axis="y")
plt.tight_layout()
save_export_or_interactive(fig1, "clustering", "01_k_selection.png", facecolor=BG)
write_chart_spec(
    "clustering",
    "01_k_selection.png",
    {
        "chart": "barColored",
        "title": "Cluster choice - simpler K wins when scores are close",
        "subtext": "Silhouette score by K; highlighted K is the one used for profiles below.",
        "labels": [str(int(k)) for k in score_df["k"]],
        "values": [float(s) for s in score_df["silhouette"]],
        "barColors": [GOLD if int(k) == best_k else COLORS[1] for k in score_df["k"]],
    },
)
print("Chart 1 done: K selection")


# Chart 2: summary table
fig2, ax2 = plt.subplots(figsize=(14, 3.8))
fig2.patch.set_facecolor(BG)
ax2.set_facecolor(BG)
ax2.axis("off")
table_df = summary_df[
    ["name", "share_pct", "peak_hours", "top_days", "weekend_share", "top_months"]
].copy()
table_df.columns = ["Cluster", "% of posts", "Peak hours", "Strongest days", "Weekend %", "Strongest months"]
table_df["% of posts"] = table_df["% of posts"].map(lambda v: f"{v:.1f}%")
table_df["Weekend %"] = table_df["Weekend %"].map(lambda v: f"{v:.1f}%")
table = ax2.table(
    cellText=table_df.values,
    colLabels=table_df.columns,
    cellLoc="center",
    colLoc="center",
    loc="center",
)
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1, 1.6)
for (r, c), cell in table.get_celld().items():
    cell.set_edgecolor(SPINE)
    if r == 0:
        cell.set_facecolor("#2A2A2E")
        cell.get_text().set_color(PRIMARY)
        cell.get_text().set_weight("bold")
    else:
        row_idx = r - 1
        cell.set_facecolor("#232328")
        cell.get_text().set_color(PRIMARY)
        if c == 0:
            cell.set_facecolor(summary_df.iloc[row_idx]["color"])
            cell.get_text().set_color(BG)
            cell.get_text().set_weight("bold")
ax2.set_title("Readable cluster summary", fontsize=13, color=PRIMARY, pad=10)
plt.tight_layout()
save_export_or_interactive(fig2, "clustering", "02_cluster_summary_table.png", facecolor=BG)
_table_lines = ["  |  ".join(table_df.columns)]
for _, trow in table_df.iterrows():
    _table_lines.append("  |  ".join(str(x) for x in trow))
write_chart_spec(
    "clustering",
    "02_cluster_summary_table.png",
    {
        "chart": "message",
        "title": "Readable cluster summary",
        "message": "\n".join(_table_lines),
    },
)
print("Chart 2 done: Summary table")


# Chart 3: hour profiles
hour_profile = (
    cl_df.groupby(["cluster", "hour"]).size()
    .unstack(fill_value=0)
    .reindex(columns=range(24), fill_value=0)
)
hour_profile = hour_profile.div(hour_profile.sum(axis=1), axis=0) * 100

fig3, ax3 = plt.subplots(figsize=(13, 5.5))
fig3.patch.set_facecolor(BG)
ax3.set_facecolor(BG)
for row in summary_df.itertuples(index=False):
    vals = hour_profile.loc[row.cluster].values
    ax3.plot(range(24), vals, color=row.color, linewidth=2.8, label=row.name)
    ax3.fill_between(range(24), vals, color=row.color, alpha=0.14)
ax3.set_xticks(range(24))
ax3.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right", fontsize=8)
ax3.set_xlabel("Hour of day", fontsize=11, color=PRIMARY)
ax3.set_ylabel("% of each cluster", fontsize=11, color=PRIMARY)
ax3.set_title("When each cluster happens", fontsize=13, color=PRIMARY, pad=12)
style_ax(ax3, grid_axis="y")
ax3.legend(facecolor="#2A2A2E", edgecolor="#555", labelcolor=PRIMARY, fontsize=9)
plt.tight_layout()
save_export_or_interactive(fig3, "clustering", "03_hour_profiles.png", facecolor=BG)
write_chart_spec(
    "clustering",
    "03_hour_profiles.png",
    {
        "chart": "line",
        "title": "When each cluster happens",
        "subtext": "% of each cluster’s posts by hour of day (within that cluster, sums to 100%)",
        "categories": [f"{h:02d}:00" for h in range(24)],
        "series": [
            {
                "name": str(srow["name"]),
                "data": [float(x) for x in hour_profile.loc[int(srow["cluster"])].values],
            }
            for _, srow in summary_df.iterrows()
        ],
    },
)
print("Chart 3 done: Hour profiles")


# Chart 4: day profiles
day_profile = (
    cl_df.groupby(["cluster", "day_of_week_n"]).size()
    .unstack(fill_value=0)
    .reindex(columns=range(7), fill_value=0)
)
day_profile = day_profile.div(day_profile.sum(axis=1), axis=0) * 100

fig4, ax4 = plt.subplots(figsize=(11, 5))
fig4.patch.set_facecolor(BG)
ax4.set_facecolor(BG)
x = np.arange(7)
bar_w = 0.8 / best_k
for idx, row in enumerate(summary_df.itertuples(index=False)):
    vals = day_profile.loc[row.cluster].values
    offset = (idx - (best_k - 1) / 2) * bar_w
    ax4.bar(x + offset, vals, width=bar_w * 0.92, color=row.color, label=row.name)
ax4.set_xticks(x)
ax4.set_xticklabels(DOW_SHORT, fontsize=10)
ax4.set_xlabel("Day of week", fontsize=11, color=PRIMARY)
ax4.set_ylabel("% of each cluster", fontsize=11, color=PRIMARY)
ax4.set_title("Which days each cluster prefers", fontsize=13, color=PRIMARY, pad=12)
style_ax(ax4, grid_axis="y")
ax4.legend(facecolor="#2A2A2E", edgecolor="#555", labelcolor=PRIMARY, fontsize=9)
plt.tight_layout()
save_export_or_interactive(fig4, "clustering", "04_day_profiles.png", facecolor=BG)
write_chart_spec(
    "clustering",
    "04_day_profiles.png",
    {
        "chart": "barGroup",
        "title": "Which days each cluster prefers",
        "subtext": "% of each cluster’s posts by weekday (within that cluster)",
        "categories": DOW_SHORT,
        "series": [
            {
                "name": str(srow["name"]),
                "values": [float(x) for x in day_profile.loc[int(srow["cluster"])].values],
                "color": str(srow["color"]),
            }
            for _, srow in summary_df.iterrows()
        ],
    },
)
print("Chart 4 done: Day profiles")


# Chart 5: cluster heatmaps
heatmap_df = (
    cl_df.groupby(["cluster", "day_of_week_n", "hour"]).size()
    .rename("count")
    .reset_index()
)

fig5, axes5 = plt.subplots(1, best_k, figsize=(5.1 * best_k, 5), sharey=True)
fig5.patch.set_facecolor(BG)
if best_k == 1:
    axes5 = [axes5]

for ax, row in zip(axes5, summary_df.itertuples(index=False)):
    sub = heatmap_df[heatmap_df["cluster"] == row.cluster]
    pivot = (
        sub.pivot(index="day_of_week_n", columns="hour", values="count")
        .reindex(index=range(7), columns=range(24))
        .fillna(0)
    )
    grid = pivot.to_numpy(dtype=float)
    if grid.sum() > 0:
        grid = grid / grid.sum() * 100
    im = ax.imshow(grid, aspect="auto", cmap="YlGnBu")
    ax.set_title(row.name, color=row.color, fontsize=12, pad=10)
    ax.set_xticks([0, 5, 10, 15, 20, 23])
    ax.set_xticklabels(["00", "05", "10", "15", "20", "23"], fontsize=8, color=PRIMARY)
    ax.set_yticks(range(7))
    ax.set_yticklabels(DOW_SHORT, fontsize=9, color=PRIMARY)
    ax.set_xlabel("Hour", fontsize=10, color=PRIMARY)
    for spine in ax.spines.values():
        spine.set_edgecolor(SPINE)
    ax.tick_params(colors=PRIMARY)

cax5 = fig5.add_axes([0.94, 0.16, 0.012, 0.68])
cbar5 = fig5.colorbar(im, cax=cax5)
cbar5.ax.tick_params(colors=PRIMARY, labelsize=8)
cbar5.outline.set_edgecolor(SPINE)
cbar5.set_label("% of cluster posts", color=PRIMARY, fontsize=10)
fig5.suptitle("Hour x day shape of each cluster", color=PRIMARY, fontsize=13, y=0.98)
fig5.subplots_adjust(left=0.05, right=0.91, top=0.78, bottom=0.12, wspace=0.05)
save_export_or_interactive(fig5, "clustering", "05_hour_day_heatmaps.png", facecolor=BG)
_hm_panels: list[dict] = []
for _, _r in summary_df.iterrows():
    _sub = heatmap_df[heatmap_df["cluster"] == int(_r["cluster"])]
    _piv = (
        _sub.pivot(index="day_of_week_n", columns="hour", values="count")
        .reindex(index=range(7), columns=range(24))
        .fillna(0)
    )
    _g = _piv.to_numpy(dtype=float)
    if _g.sum() > 0:
        _g = _g / _g.sum() * 100
    _hm_panels.append(
        {
            "chart": "heatmap",
            "title": f"{_r['name']} — % of this cluster’s posts",
            "subtext": "Share by hour × weekday within the cluster",
            "xAxisName": "Hour",
            "yAxisName": "Day",
            "xCategories": [f"{h:02d}" for h in range(24)],
            "yCategories": DOW_SHORT,
            "data": [[float(v) for v in row] for row in _g.tolist()],
        }
    )
write_chart_spec(
    "clustering",
    "05_hour_day_heatmaps.png",
    {
        "chart": "composite",
        "title": "Hour × day shape of each cluster",
        "subtext": "Percent of each cluster’s own posts. Focus a cell to read the value; no pop-up tooltips.",
        "panels": _hm_panels,
    },
)
print("Chart 5 done: Hour x day heatmaps")


# Chart 6: month breakdown
month_profile = (
    cl_df.groupby(["cluster", "month"]).size()
    .unstack(fill_value=0)
    .reindex(columns=range(1, 13), fill_value=0)
)
month_profile = month_profile.div(month_profile.sum(axis=1), axis=0) * 100

fig6, ax6 = plt.subplots(figsize=(12, 5))
fig6.patch.set_facecolor(BG)
ax6.set_facecolor(BG)
xm = np.arange(12)
bar_wm = 0.8 / best_k
for idx, row in enumerate(summary_df.itertuples(index=False)):
    vals = month_profile.loc[row.cluster].values
    offset = (idx - (best_k - 1) / 2) * bar_wm
    ax6.bar(xm + offset, vals, width=bar_wm * 0.92, color=row.color, label=row.name)
ax6.set_xticks(xm)
ax6.set_xticklabels(MONTH_SHORT, fontsize=9)
ax6.set_xlabel("Month", fontsize=11, color=PRIMARY)
ax6.set_ylabel("% of each cluster", fontsize=11, color=PRIMARY)
ax6.set_title("Month patterns - used for explanation, not for clustering", fontsize=13, color=PRIMARY, pad=12)
style_ax(ax6, grid_axis="y")
ax6.legend(facecolor="#2A2A2E", edgecolor="#555", labelcolor=PRIMARY, fontsize=9)
plt.tight_layout()
save_export_or_interactive(fig6, "clustering", "06_month_profiles.png", facecolor=BG)
write_chart_spec(
    "clustering",
    "06_month_profiles.png",
    {
        "chart": "barGroup",
        "title": "Month patterns - used for explanation, not for clustering",
        "subtext": "% of each cluster’s posts by calendar month (within that cluster)",
        "categories": MONTH_SHORT,
        "rotateX": 40,
        "series": [
            {
                "name": str(srow["name"]),
                "values": [float(x) for x in month_profile.loc[int(srow["cluster"])].values],
                "color": str(srow["color"]),
            }
            for _, srow in summary_df.iterrows()
        ],
    },
)
print("Chart 6 done: Month profiles")

print(f"\nClustering complete: {best_k} clearly named clusters from {len(cl_df):,} food posts")
