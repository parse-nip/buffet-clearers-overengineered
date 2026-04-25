"""Step 7: Location analysis — building, room type, floor, and time patterns."""

import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from chart_json import write_chart_spec
from graph_output import save_and_close_if_exporting

# ── Design tokens (Zerve dark theme) ──────────────────────────────────────────
VIZ_BG     = "#1D1D20"
VIZ_TEXT   = "#fbfbff"
VIZ_SEC    = "#909094"
VIZ_COLORS = [
    "#A1C9F4", "#FFB482", "#8DE5A1", "#FF9F9B", "#D0BBFF",
    "#1F77B4", "#9467BD", "#8C564B", "#C49C94", "#E377C2",
    "#BCBD22", "#17BECF", "#AEC7E8", "#FFBB78", "#98DF8A",
]
VIZ_GOLD  = "#ffd400"
VIZ_GREEN = "#17b26a"

# ── Location extraction ────────────────────────────────────────────────────────
#
# Building patterns — ordered most-specific first so SCIS2 matches before SOE
# or SCIS, and SOSS/CIS matches before a bare CIS might be misread elsewhere.
#
_BUILDING_RULES = [
    # SCIS2 / SOE-SCIS2 combined building
    ("SCIS2",       re.compile(r'\bscis\s*2\b|\bscis2\b', re.I)),
    # SOE  (School of Economics — also labels the SOE/SCIS2 physical building)
    ("SOE",         re.compile(r'\bsoe\b', re.I)),
    # SCIS / SCIS1  (School of Computing & Information Systems, building 1)
    ("SCIS",        re.compile(r'\bscis\s*1\b|\bscis1\b|\bscis\b', re.I)),
    # SOA  (School of Accountancy)
    ("SOA",         re.compile(r'\bsoa\b', re.I)),
    # SOB / LKCSB  (Lee Kong Chian School of Business; SOB is student shorthand)
    ("SOB/LKCSB",   re.compile(r'\bsob\b|\blkcsb\b', re.I)),
    # Connexion / Connex / SMUC  (SMU Connexion building)
    ("Connexion",   re.compile(
        r'\bconnex(?:ion)?\b|\bsmuc\b|\bsmu\s+connexion\b|\bsmu\s+connex\b', re.I
    )),
    # SOSS / CIS  (School of Social Sciences / College of Integrative Studies — same building)
    ("SOSS/CIS",    re.compile(r'\bsoss\b|\bsoss[/\s]+cis\b|\bcis\b', re.I)),
    # SOL / YPHSL  (Yong Pung How School of Law)
    ("SOL",         re.compile(r'\bsol\b|\byphsl\b|\byphls\b|\byph\s*sl\b', re.I)),
    # LKS Library  (Li Ka Shing Library — distinct from LKCSB school)
    ("LKS Library", re.compile(r'\blks\b|\bli\s+ka\s+shing\b', re.I)),
    # Admin Building
    ("Admin",       re.compile(r'\badmin\b', re.I)),
    # OSL  (Office of Student Life / OSL Lounge)
    ("OSL",         re.compile(r'\bosl\b', re.I)),
]

# Room-type patterns — ALC before SR/CR to avoid ambiguity on "classroom" keywords
_ROOM_TYPE_RULES = [
    ("ALC",           re.compile(r'\balc\b|\bactive\s+learning\s+(?:cr|classroom|class)\b', re.I)),
    ("SR",            re.compile(r'\bsr\b|\bseminar\s+room\b|\bsmnr\b', re.I)),
    ("CR",            re.compile(r'\bcr\b|\bclassroom\b', re.I)),
    ("GSR",           re.compile(r'\bgsr\b|\bgroup\s+study\s+room\b', re.I)),
    ("Function Room", re.compile(r'\bfunction\s+(?:room|lounge)\b', re.I)),
    ("Meeting Pod",   re.compile(r'\bmeeting\s+pod\b', re.I)),
    ("Lounge",        re.compile(r'\blounge\b', re.I)),
    ("Lab",           re.compile(r'\bcomputing\s+lab\b|\bcomputing\s+lab\b|\blab\b', re.I)),
    ("Training Room", re.compile(r'\btraining\s+room\b', re.I)),
    ("Hall",          re.compile(r'\bhall\b', re.I)),
    ("Auditorium",    re.compile(r'\bauditorium\b', re.I)),
    ("Event Space",   re.compile(r'\bevent\s+(?:space|square|catering\s+area)\b', re.I)),
]


def _extract_room_code(text):
    """Return (floor_str, room_str) or (None, None).

    Tries patterns in order:
      1. Room-type prefix + basement floor  e.g. SR B1-1, SRB1-1
      2. Standalone basement code           e.g. b2-01, B1-09
      3. Room-type prefix + regular floor   e.g. CR1-1, GSR 3-16, SR 2.8
      4. Standalone floor-room code         e.g. 3-2, 4-5 (floor 1-7 only)
    """
    # 1. Room type + basement  (SR B1-1, GSRB2-04, ALC B1-2)
    m = re.search(r'(?:SR|CR|GSR|ALC|Lab)\s*([bB][1-2])-([0-9]{1,3})', text, re.I)
    if m:
        return m.group(1).upper(), m.group(2)

    # 2. Standalone basement  (b1-01, B2-03)
    m = re.search(r'\b([bB][1-2])-([0-9]{1,3})\b', text)
    if m:
        return m.group(1).upper(), m.group(2)

    # 3. Room type + regular floor  (CR1-1, SR 2-16, GSR2-4, SR 2.8, SR2.1)
    m = re.search(r'(?:SR|CR|GSR|ALC|Lab)\s*([1-7])[.-]([0-9]{1,3})(?!\d)', text, re.I)
    if m:
        return m.group(1), m.group(2)

    # 4. Standalone floor-room (only digits 1-7 before dash to skip dates/IDs)
    m = re.search(r'(?<![/\d])([1-7])-([0-9]{1,3})(?!\d)', text)
    if m:
        return m.group(1), m.group(2)

    return None, None


def _extract_floor_only(text):
    """Return canonical floor string (e.g. '3', 'B1') from floor-only mentions."""
    # level / lvl / lv  (case-insensitive, optional space)
    m = re.search(r'(?:level|lvl|lv)\s*([0-9]+)', text, re.I)
    if m:
        return m.group(1)
    # Capital-L shorthand: L3, L5, Lv4 — word-boundary ensures we skip LKCSB/SOL
    m = re.search(r'\bL([0-9]+)\b', text)
    if m:
        return m.group(1)
    # Basement shorthand not followed by a dash (otherwise handled by room code)
    m = re.search(r'\b[bB]([0-9])\b(?!-)', text)
    if m:
        return f"B{m.group(1)}"
    return None


def extract_location_features(text):
    """Return dict with keys: building, room_type, floor, room_code."""
    result = {"building": None, "room_type": None, "floor": None, "room_code": None}

    for name, pat in _BUILDING_RULES:
        if pat.search(text):
            result["building"] = name
            break

    for name, pat in _ROOM_TYPE_RULES:
        if pat.search(text):
            result["room_type"] = name
            break

    floor_raw, room_raw = _extract_room_code(text)
    if floor_raw is not None:
        result["floor"] = floor_raw
        result["room_code"] = f"{floor_raw.upper()}-{room_raw}"
    else:
        result["floor"] = _extract_floor_only(text)

    return result


# ── Build location DataFrame ───────────────────────────────────────────────────
food_posts = food_df[food_df["is_food_post"]].copy()
food_posts["datetime"] = pd.to_datetime(food_posts["datetime"])

loc_rows = food_posts["text"].apply(extract_location_features)
loc_extra = pd.DataFrame(list(loc_rows), index=food_posts.index)
loc_df = pd.concat([food_posts, loc_extra], axis=1)

# Only rows where we detected a building
with_building = loc_df[loc_df["building"].notna()].copy()

print(f"Food posts total          : {len(food_posts):,}")
print(f"With building detected    : {len(with_building):,}  "
      f"({len(with_building)/len(food_posts)*100:.1f}%)")
print(f"With room type detected   : {loc_df['room_type'].notna().sum():,}")
print(f"With floor detected       : {loc_df['floor'].notna().sum():,}")
print()
print("Building counts:")
for b, c in with_building["building"].value_counts().items():
    print(f"  {b:<18} {c:>4}")


# ── Shared helpers ─────────────────────────────────────────────────────────────
def style_ax(ax, title, xlabel="", ylabel=""):
    ax.set_facecolor(VIZ_BG)
    ax.set_title(title, color=VIZ_TEXT, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, color=VIZ_SEC, fontsize=10)
    ax.set_ylabel(ylabel, color=VIZ_SEC, fontsize=10)
    ax.tick_params(colors=VIZ_SEC, labelsize=9)
    for sp in ax.spines.values():
        sp.set_edgecolor("#3a3a3d")
    return ax


DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

FLOOR_ORDER = ["B2", "B1", "1", "2", "3", "4", "5", "6", "7"]

# Sorted buildings for consistent ordering across charts
BUILDING_ORDER = (
    with_building["building"].value_counts().index.tolist()
)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Building frequency — horizontal bar
# ══════════════════════════════════════════════════════════════════════════════
bld_counts = with_building["building"].value_counts()

fig1, ax = plt.subplots(figsize=(9, 5), facecolor=VIZ_BG)
ax.set_facecolor(VIZ_BG)

colors_b = [VIZ_COLORS[i % len(VIZ_COLORS)] for i in range(len(bld_counts))]
bars = ax.barh(bld_counts.index[::-1], bld_counts.values[::-1],
               color=colors_b[::-1], height=0.65, zorder=3)

for bar in bars:
    w = bar.get_width()
    ax.text(w + 1, bar.get_y() + bar.get_height() / 2, str(int(w)),
            va="center", ha="left", color=VIZ_TEXT, fontsize=9)

ax.set_xlim(0, bld_counts.max() * 1.15)
ax.xaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
style_ax(ax, "Building Frequency in Food Posts", "Number of Posts", "Building")
fig1.tight_layout()
save_and_close_if_exporting(fig1, "location_viz", "01_building_frequency.png", facecolor=VIZ_BG)
write_chart_spec(
    "location_viz",
    "01_building_frequency.png",
    {
        "chart": "barh",
        "title": "Building Frequency in Food Posts",
        "subtext": "Count of food posts where a building was detected in text",
        "categories": [str(x) for x in bld_counts.index[::-1]],
        "values": [int(x) for x in bld_counts.values[::-1]],
    },
)
print("Chart 1 done: Building frequency")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Room type frequency — horizontal bar
# ══════════════════════════════════════════════════════════════════════════════
rt_counts = loc_df["room_type"].dropna().value_counts()

fig2, ax = plt.subplots(figsize=(9, 5), facecolor=VIZ_BG)
ax.set_facecolor(VIZ_BG)

colors_rt = [VIZ_GOLD if v == rt_counts.index[0] else VIZ_COLORS[i % len(VIZ_COLORS)]
             for i, v in enumerate(rt_counts.index)]
bars2 = ax.barh(rt_counts.index[::-1], rt_counts.values[::-1],
                color=colors_rt[::-1], height=0.65, zorder=3)

for bar in bars2:
    w = bar.get_width()
    ax.text(w + 0.5, bar.get_y() + bar.get_height() / 2, str(int(w)),
            va="center", ha="left", color=VIZ_TEXT, fontsize=9)

ax.set_xlim(0, rt_counts.max() * 1.15)
ax.xaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
style_ax(ax, "Room Type Frequency in Food Posts", "Number of Posts", "Room Type")
fig2.tight_layout()
save_and_close_if_exporting(fig2, "location_viz", "02_room_type_frequency.png", facecolor=VIZ_BG)
write_chart_spec(
    "location_viz",
    "02_room_type_frequency.png",
    {
        "chart": "barh",
        "title": "Room Type Frequency in Food Posts",
        "subtext": "Champion (most common) highlighted",
        "highlight": "first",
        "reverseY": True,
        "categories": [str(x) for x in rt_counts.index.tolist()],
        "values": [int(x) for x in rt_counts.values.tolist()],
    },
)
print("Chart 2 done: Room type frequency")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Floor distribution — vertical bar
# ══════════════════════════════════════════════════════════════════════════════
floor_counts_raw = loc_df["floor"].dropna().value_counts()
present_floors   = [f for f in FLOOR_ORDER if f in floor_counts_raw.index]
floor_counts     = floor_counts_raw.reindex(present_floors, fill_value=0)

floor_colors = [
    "#FF9F9B" if str(f).startswith("B") else VIZ_COLORS[int(f) % len(VIZ_COLORS)]
    for f in present_floors
]

fig3, ax = plt.subplots(figsize=(9, 5), facecolor=VIZ_BG)
ax.set_facecolor(VIZ_BG)

bars3 = ax.bar(floor_counts.index, floor_counts.values,
               color=floor_colors, width=0.65, zorder=3)

for bar in bars3:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h + 1, str(int(h)),
            ha="center", va="bottom", color=VIZ_TEXT, fontsize=9)

ax.set_ylim(0, floor_counts.max() * 1.15)
ax.yaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
style_ax(ax, "Floor Distribution of Food Posts", "Floor", "Number of Posts")
fig3.tight_layout()
save_and_close_if_exporting(fig3, "location_viz", "03_floor_distribution.png", facecolor=VIZ_BG)
write_chart_spec(
    "location_viz",
    "03_floor_distribution.png",
    {
        "chart": "barColored",
        "title": "Floor Distribution of Food Posts",
        "subtext": "Basement levels tinted separately from numeric floors",
        "labels": [str(f) for f in floor_counts.index.tolist()],
        "values": [int(x) for x in floor_counts.values.tolist()],
        "barColors": [str(c) for c in floor_colors],
    },
)
print("Chart 3 done: Floor distribution")


# ══════════════════════════════════════════════════════════════════════════════
# 4. Building × Day of Week — heatmap
# ══════════════════════════════════════════════════════════════════════════════
bld_dow = (
    with_building.groupby(["building", "day_of_week"])
    .size()
    .unstack(fill_value=0)
    .reindex(index=BUILDING_ORDER, columns=DAY_ORDER, fill_value=0)
)

fig4, ax = plt.subplots(figsize=(11, 5), facecolor=VIZ_BG)
ax.set_facecolor(VIZ_BG)

im4 = ax.imshow(bld_dow.values, aspect="auto", cmap="plasma", interpolation="nearest")

ax.set_yticks(range(len(BUILDING_ORDER)))
ax.set_yticklabels(BUILDING_ORDER, color=VIZ_SEC, fontsize=9)
ax.set_xticks(range(7))
ax.set_xticklabels(DAY_SHORT, color=VIZ_SEC, fontsize=9)

# Annotate cells
for i in range(len(BUILDING_ORDER)):
    for j in range(7):
        val = bld_dow.values[i, j]
        if val > 0:
            ax.text(j, i, str(int(val)), ha="center", va="center",
                    color="white" if val > bld_dow.values.max() * 0.5 else VIZ_SEC,
                    fontsize=7.5, fontweight="bold")

cbar4 = fig4.colorbar(im4, ax=ax, pad=0.01)
cbar4.ax.tick_params(colors=VIZ_SEC, labelsize=8)
cbar4.set_label("Post Count", color=VIZ_SEC, fontsize=9)

ax.set_title("Building × Day of Week", color=VIZ_TEXT, fontsize=13,
             fontweight="bold", pad=12)
for sp in ax.spines.values():
    sp.set_edgecolor("#3a3a3d")

fig4.tight_layout()
save_and_close_if_exporting(fig4, "location_viz", "04_building_by_day_of_week.png", facecolor=VIZ_BG)
write_chart_spec(
    "location_viz",
    "04_building_by_day_of_week.png",
    {
        "chart": "heatmap",
        "title": "Building × Day of Week",
        "subtext": "Post counts (plasma). Focus a cell to read the value; no pop-up tooltips.",
        "xAxisName": "Day",
        "yAxisName": "Building",
        "xCategories": [str(d) for d in DAY_SHORT],
        "yCategories": [str(b) for b in BUILDING_ORDER],
        "data": [[int(x) for x in row] for row in bld_dow.values.tolist()],
    },
)
print("Chart 4 done: Building × day of week")


# ══════════════════════════════════════════════════════════════════════════════
# 5. Building × Hour — heatmap (row-normalised to % so small buildings show up)
# ══════════════════════════════════════════════════════════════════════════════
bld_hr = (
    with_building.groupby(["building", "hour"])
    .size()
    .unstack(fill_value=0)
    .reindex(index=BUILDING_ORDER, fill_value=0)
    .reindex(columns=range(24), fill_value=0)
)

# Normalise each row to 0–100 %
row_max = bld_hr.values.max(axis=1, keepdims=True)
row_max[row_max == 0] = 1
bld_hr_norm = bld_hr.values / row_max * 100

fig5, ax = plt.subplots(figsize=(14, 5), facecolor=VIZ_BG)
ax.set_facecolor(VIZ_BG)

im5 = ax.imshow(bld_hr_norm, aspect="auto", cmap="YlOrRd", interpolation="nearest",
                vmin=0, vmax=100)

ax.set_yticks(range(len(BUILDING_ORDER)))
ax.set_yticklabels(BUILDING_ORDER, color=VIZ_SEC, fontsize=9)
ax.set_xticks(range(24))
ax.set_xticklabels([f"{h:02d}" for h in range(24)],
                   color=VIZ_SEC, fontsize=7.5, rotation=45, ha="right")

cbar5 = fig5.colorbar(im5, ax=ax, pad=0.01)
cbar5.ax.tick_params(colors=VIZ_SEC, labelsize=8)
cbar5.set_label("% of building's posts (row max=100)", color=VIZ_SEC, fontsize=8)

ax.set_title("Building × Hour of Day  (row-normalised)", color=VIZ_TEXT,
             fontsize=13, fontweight="bold", pad=12)
ax.set_xlabel("Hour", color=VIZ_SEC, fontsize=10)
for sp in ax.spines.values():
    sp.set_edgecolor("#3a3a3d")

fig5.tight_layout()
save_and_close_if_exporting(fig5, "location_viz", "05_building_by_hour.png", facecolor=VIZ_BG)
write_chart_spec(
    "location_viz",
    "05_building_by_hour.png",
    {
        "chart": "heatmap",
        "title": "Building × Hour of Day  (row-normalised)",
        "subtext": "% of each building’s max hourly count (0–100 per row). Focus a cell to read the value.",
        "xAxisName": "Hour",
        "yAxisName": "Building",
        "xCategories": [f"{h:02d}" for h in range(24)],
        "yCategories": [str(b) for b in BUILDING_ORDER],
        "data": [[float(x) for x in row] for row in bld_hr_norm.tolist()],
    },
)
print("Chart 5 done: Building × hour")


# ══════════════════════════════════════════════════════════════════════════════
# 6. Building activity over time — stacked area (monthly, top-8 buildings)
# ══════════════════════════════════════════════════════════════════════════════
TOP_N_BLD = 8
top_buildings = BUILDING_ORDER[:TOP_N_BLD]

with_building["month_period"] = with_building["datetime"].dt.to_period("M")
time_bld = (
    with_building[with_building["building"].isin(top_buildings)]
    .groupby(["month_period", "building"])
    .size()
    .unstack(fill_value=0)
    .reindex(columns=top_buildings, fill_value=0)
)
time_bld.index = time_bld.index.astype(str)

fig6, ax = plt.subplots(figsize=(14, 6), facecolor=VIZ_BG)
ax.set_facecolor(VIZ_BG)

ax.stackplot(range(len(time_bld)),
             [time_bld[b].values for b in top_buildings],
             labels=top_buildings,
             colors=VIZ_COLORS[:TOP_N_BLD],
             alpha=0.85)

ax.set_xticks(range(len(time_bld)))
ax.set_xticklabels(time_bld.index, rotation=45, ha="right", color=VIZ_SEC, fontsize=7.5)
ax.yaxis.grid(True, color="#3a3a3d", linewidth=0.5, zorder=0)
ax.set_axisbelow(True)

legend = ax.legend(loc="upper left", framealpha=0.2, labelcolor=VIZ_TEXT,
                   facecolor="#2a2a2d", edgecolor="#3a3a3d", fontsize=8,
                   ncol=2)
style_ax(ax, "Building Activity Over Time (top 8)", "Month", "Post Count")
fig6.tight_layout()
save_and_close_if_exporting(fig6, "location_viz", "06_building_over_time.png", facecolor=VIZ_BG)
write_chart_spec(
    "location_viz",
    "06_building_over_time.png",
    {
        "chart": "stackedArea",
        "title": "Building Activity Over Time (top 8)",
        "subtext": "Stacked post counts by month in the export",
        "categories": [str(x) for x in time_bld.index.tolist()],
        "series": [
            {"name": str(b), "data": [int(x) for x in time_bld[str(b)].values]} for b in top_buildings
        ],
    },
)
print("Chart 6 done: Building over time")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Building × Floor — heatmap
# ══════════════════════════════════════════════════════════════════════════════
with_floor = with_building[with_building["floor"].notna()].copy()
# Keep only floors that appear in our canonical list
with_floor = with_floor[with_floor["floor"].isin(FLOOR_ORDER)]

bld_floor = (
    with_floor.groupby(["building", "floor"])
    .size()
    .unstack(fill_value=0)
    .reindex(index=BUILDING_ORDER, fill_value=0)
)
present_f = [f for f in FLOOR_ORDER if f in bld_floor.columns]
bld_floor = bld_floor.reindex(columns=present_f, fill_value=0)

fig7, ax = plt.subplots(figsize=(10, 5), facecolor=VIZ_BG)
ax.set_facecolor(VIZ_BG)

im7 = ax.imshow(bld_floor.values, aspect="auto", cmap="plasma", interpolation="nearest")

ax.set_yticks(range(len(BUILDING_ORDER)))
ax.set_yticklabels(BUILDING_ORDER, color=VIZ_SEC, fontsize=9)
ax.set_xticks(range(len(present_f)))
ax.set_xticklabels([f"Floor {f}" for f in present_f], color=VIZ_SEC, fontsize=9, rotation=30, ha="right")

for i in range(len(BUILDING_ORDER)):
    for j in range(len(present_f)):
        val = bld_floor.values[i, j]
        if val > 0:
            ax.text(j, i, str(int(val)), ha="center", va="center",
                    color="white" if val > bld_floor.values.max() * 0.5 else VIZ_SEC,
                    fontsize=8, fontweight="bold")

cbar7 = fig7.colorbar(im7, ax=ax, pad=0.01)
cbar7.ax.tick_params(colors=VIZ_SEC, labelsize=8)
cbar7.set_label("Post Count", color=VIZ_SEC, fontsize=9)

ax.set_title("Building × Floor Heatmap", color=VIZ_TEXT, fontsize=13,
             fontweight="bold", pad=12)
for sp in ax.spines.values():
    sp.set_edgecolor("#3a3a3d")

fig7.tight_layout()
save_and_close_if_exporting(fig7, "location_viz", "07_building_floor_heatmap.png", facecolor=VIZ_BG)
write_chart_spec(
    "location_viz",
    "07_building_floor_heatmap.png",
    {
        "chart": "heatmap",
        "title": "Building × Floor Heatmap",
        "subtext": "Post counts (plasma). Focus a cell to read the value; no pop-up tooltips.",
        "xAxisName": "Floor",
        "yAxisName": "Building",
        "xCategories": [f"Floor {f}" for f in present_f],
        "yCategories": [str(b) for b in BUILDING_ORDER],
        "data": [[int(x) for x in row] for row in bld_floor.values.tolist()],
    },
)
print("Chart 7 done: Building × floor")


# ══════════════════════════════════════════════════════════════════════════════
# 8. Room type × Hour — heatmap
# ══════════════════════════════════════════════════════════════════════════════
with_rt = loc_df[loc_df["room_type"].notna()].copy()
rt_order = loc_df["room_type"].value_counts().index.tolist()

rt_hr = (
    with_rt.groupby(["room_type", "hour"])
    .size()
    .unstack(fill_value=0)
    .reindex(index=rt_order, fill_value=0)
    .reindex(columns=range(24), fill_value=0)
)

# Row-normalise to %
rmax = rt_hr.values.max(axis=1, keepdims=True)
rmax[rmax == 0] = 1
rt_hr_norm = rt_hr.values / rmax * 100

fig8, ax = plt.subplots(figsize=(14, 5), facecolor=VIZ_BG)
ax.set_facecolor(VIZ_BG)

im8 = ax.imshow(rt_hr_norm, aspect="auto", cmap="magma", interpolation="nearest",
                vmin=0, vmax=100)

ax.set_yticks(range(len(rt_order)))
ax.set_yticklabels(rt_order, color=VIZ_SEC, fontsize=9)
ax.set_xticks(range(24))
ax.set_xticklabels([f"{h:02d}" for h in range(24)],
                   color=VIZ_SEC, fontsize=7.5, rotation=45, ha="right")

cbar8 = fig8.colorbar(im8, ax=ax, pad=0.01)
cbar8.ax.tick_params(colors=VIZ_SEC, labelsize=8)
cbar8.set_label("% of room type's posts (row max=100)", color=VIZ_SEC, fontsize=8)

ax.set_title("Room Type × Hour of Day  (row-normalised)", color=VIZ_TEXT,
             fontsize=13, fontweight="bold", pad=12)
ax.set_xlabel("Hour", color=VIZ_SEC, fontsize=10)
for sp in ax.spines.values():
    sp.set_edgecolor("#3a3a3d")

fig8.tight_layout()
save_and_close_if_exporting(fig8, "location_viz", "08_room_type_by_hour.png", facecolor=VIZ_BG)
write_chart_spec(
    "location_viz",
    "08_room_type_by_hour.png",
    {
        "chart": "heatmap",
        "title": "Room Type × Hour of Day  (row-normalised)",
        "subtext": "% of each room type’s max hourly count (0–100 per row).",
        "xAxisName": "Hour",
        "yAxisName": "Room type",
        "xCategories": [f"{h:02d}" for h in range(24)],
        "yCategories": [str(x) for x in rt_order],
        "data": [[float(x) for x in row] for row in rt_hr_norm.tolist()],
    },
)
print("Chart 8 done: Room type × hour")


print("\n✅ All 8 location visualizations rendered successfully.")
