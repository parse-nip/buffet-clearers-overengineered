
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from graph_output import save_export_or_interactive

# ── Zerve Design System ────────────────────────────────────────────────────────
BG      = '#1D1D20'
PRIMARY = '#fbfbff'
SEC     = '#909094'
COLORS  = ['#A1C9F4', '#FFB482', '#8DE5A1', '#FF9F9B', '#D0BBFF',
           '#1F77B4', '#9467BD', '#8C564B', '#E377C2', '#F7B6D2']
GOLD    = '#ffd400'

plt.rcParams.update({
    'figure.facecolor': BG, 'axes.facecolor': BG,
    'text.color': PRIMARY, 'axes.labelcolor': PRIMARY,
    'xtick.color': PRIMARY, 'ytick.color': PRIMARY,
    'axes.edgecolor': '#444', 'grid.color': '#333',
    'font.family': 'sans-serif',
})

# ─────────────────────────────────────────────────────────────────────────────
# 1.  FEATURES  (temporal only — day of week, time of day, month of year)
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 65)
print("K-MEANS CLUSTERING — Buffet Alert Patterns")
print("=" * 65)

_cl_df = food_df[food_df['is_food_post'] == True].copy()

# Cyclical encoding so that hour 23 and hour 0 are adjacent, not 23 apart
_cl_df['hour_sin']  = np.sin(2 * np.pi * _cl_df['hour'] / 24)
_cl_df['hour_cos']  = np.cos(2 * np.pi * _cl_df['hour'] / 24)
_cl_df['dow_sin']   = np.sin(2 * np.pi * _cl_df['day_of_week_n'] / 7)
_cl_df['dow_cos']   = np.cos(2 * np.pi * _cl_df['day_of_week_n'] / 7)
_cl_df['month_sin'] = np.sin(2 * np.pi * (_cl_df['month'] - 1) / 12)
_cl_df['month_cos'] = np.cos(2 * np.pi * (_cl_df['month'] - 1) / 12)

_FEATURES = ['hour_sin', 'hour_cos', 'dow_sin', 'dow_cos', 'month_sin', 'month_cos']

X_cl = _cl_df[_FEATURES].to_numpy()
_scaler = StandardScaler()
X_scaled = _scaler.fit_transform(X_cl)

print(f"\n  Food posts : {len(_cl_df):,}")
print(f"  Features   : day of week · time of day · month of year  (cyclical)")

# ─────────────────────────────────────────────────────────────────────────────
# 2.  ELBOW — pick K
# ─────────────────────────────────────────────────────────────────────────────
K_RANGE = range(2, 11)
_inertias = []
for _k in K_RANGE:
    _inertias.append(KMeans(n_clusters=_k, random_state=42, n_init=10).fit(X_scaled).inertia_)

_diffs2 = np.diff(np.diff(_inertias))
_best_k = list(K_RANGE)[int(np.argmax(_diffs2)) + 1]

print(f"\n  Optimal K  : {_best_k}  (elbow method)")

# ─────────────────────────────────────────────────────────────────────────────
# 3.  FIT & LABEL CLUSTERS
# ─────────────────────────────────────────────────────────────────────────────
_cl_df['cluster'] = KMeans(n_clusters=_best_k, random_state=42, n_init=10).fit_predict(X_scaled)

_DOW_NAMES   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
_MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
_BUCKET_ORDER = ['Early (0–9)', 'Morning (9–12)', 'Lunch (12–14)',
                 'Afternoon (14–17)', 'Evening (17–20)', 'Night (20–24)']

def _time_bucket(h):
    if h < 9:  return 'Early (0–9)'
    if h < 12: return 'Morning (9–12)'
    if h < 14: return 'Lunch (12–14)'
    if h < 17: return 'Afternoon (14–17)'
    if h < 20: return 'Evening (17–20)'
    return 'Night (20–24)'

_cl_df['time_bucket'] = _cl_df['hour'].apply(_time_bucket)

print(f"\n  {'Cluster':<10} {'Size':>6}  {'Avg hour':>9}  {'Top day':>9}  {'Top month':>10}")
print(f"  {'─'*10} {'─'*6}  {'─'*9}  {'─'*9}  {'─'*10}")
for _c in range(_best_k):
    _sub = _cl_df[_cl_df['cluster'] == _c]
    _avg_h = _sub['hour'].mean()
    _top_d = _DOW_NAMES[int(_sub['day_of_week_n'].mode().iloc[0])]
    _top_m = _MONTH_NAMES[int(_sub['month'].mode().iloc[0]) - 1]
    print(f"  Cluster {_c:<2} {len(_sub):>6}  {_avg_h:>7.1f}h  {_top_d:>9}  {_top_m:>10}")

# ─────────────────────────────────────────────────────────────────────────────
# 4.  CHARTS
# ─────────────────────────────────────────────────────────────────────────────

# --- Fig 1: Elbow curve -------------------------------------------------------
fig1, ax1 = plt.subplots(figsize=(9, 5))
fig1.patch.set_facecolor(BG)
ax1.set_facecolor(BG)
ax1.plot(list(K_RANGE), _inertias, color=COLORS[0], linewidth=2.2,
         marker='o', markersize=7, zorder=3, label='Inertia')
ax1.scatter([_best_k], [_inertias[_best_k - list(K_RANGE)[0]]],
            color=GOLD, s=130, zorder=5, edgecolors='none', label=f'Chosen K={_best_k}')
ax1.axvline(_best_k, color=GOLD, linewidth=1.2, linestyle='--', alpha=0.55)
ax1.set_xticks(list(K_RANGE))
ax1.set_xlabel('Number of Clusters (K)', color=PRIMARY, fontsize=11)
ax1.set_ylabel('Inertia (Within-cluster SSE)', color=PRIMARY, fontsize=11)
ax1.set_title('K-Means Elbow Curve — Buffet Alert Clusters', color=PRIMARY, fontsize=13, pad=12)
ax1.tick_params(colors=PRIMARY, labelsize=9)
for sp in ax1.spines.values():
    sp.set_edgecolor('#444')
ax1.yaxis.grid(True, linestyle='--', alpha=0.25)
ax1.set_axisbelow(True)
ax1.legend(facecolor='#2a2a2e', edgecolor='#555', labelcolor=PRIMARY, fontsize=9)
plt.tight_layout()
save_export_or_interactive(fig1, "clustering", "01_elbow_curve.png", facecolor=BG)
print("Chart 1 done: Elbow curve")


# --- Fig 2: Hour × Day scatter (main intuitive view) -------------------------
# Jitter day_of_week slightly so overlapping points are visible
_rng = np.random.default_rng(0)
_jitter = _rng.uniform(-0.35, 0.35, size=len(_cl_df))

fig2, ax2 = plt.subplots(figsize=(13, 6))
fig2.patch.set_facecolor(BG)
ax2.set_facecolor(BG)

for _c in range(_best_k):
    _mask = _cl_df['cluster'].values == _c
    ax2.scatter(
        _cl_df.loc[_mask, 'hour'].values,
        _cl_df.loc[_mask, 'day_of_week_n'].values + _jitter[_mask],
        color=COLORS[_c % len(COLORS)], alpha=0.45, s=16,
        label=f'Cluster {_c}', edgecolors='none',
    )

ax2.set_xticks(range(24))
ax2.set_xticklabels([f'{h:02d}:00' for h in range(24)],
                    rotation=45, ha='right', fontsize=7.5, color=PRIMARY)
ax2.set_yticks(range(7))
ax2.set_yticklabels(_DOW_NAMES, fontsize=10, color=PRIMARY)
ax2.set_xlabel('Hour of Day', color=PRIMARY, fontsize=11)
ax2.set_ylabel('Day of Week', color=PRIMARY, fontsize=11)
ax2.set_title('When Each Cluster Posts — Hour of Day vs Day of Week',
              color=PRIMARY, fontsize=13, pad=12)
ax2.tick_params(colors=PRIMARY, labelsize=9)
for sp in ax2.spines.values():
    sp.set_edgecolor('#444')
ax2.xaxis.grid(True, linestyle='--', alpha=0.2)
ax2.yaxis.grid(True, linestyle='--', alpha=0.2)
ax2.set_axisbelow(True)
ax2.legend(facecolor='#2a2a2e', edgecolor='#555', labelcolor=PRIMARY, fontsize=9)
plt.tight_layout()
save_export_or_interactive(fig2, "clustering", "02_hour_vs_day_scatter.png", facecolor=BG)
print("Chart 2 done: Hour × day scatter")


# --- Fig 3: Time-bucket profile per cluster (normalised %) -------------------
# Shows what "character" each cluster has: lunchtime, evening, etc.
_bucket_pct = (
    _cl_df.groupby(['cluster', 'time_bucket']).size()
    .unstack(fill_value=0)
    .reindex(columns=_BUCKET_ORDER, fill_value=0)
)
_bucket_pct = _bucket_pct.div(_bucket_pct.sum(axis=1), axis=0) * 100

fig3, ax3 = plt.subplots(figsize=(11, 5))
fig3.patch.set_facecolor(BG)
ax3.set_facecolor(BG)

_x = np.arange(len(_BUCKET_ORDER))
_bar_w = 0.8 / _best_k
for _c in range(_best_k):
    _vals = _bucket_pct.loc[_c].values if _c in _bucket_pct.index else np.zeros(len(_BUCKET_ORDER))
    _offset = (_c - (_best_k - 1) / 2) * _bar_w
    _bars = ax3.bar(_x + _offset, _vals, width=_bar_w * 0.9,
                    color=COLORS[_c % len(COLORS)], label=f'Cluster {_c}')
    for _bar in _bars:
        _h = _bar.get_height()
        if _h > 4:
            ax3.text(_bar.get_x() + _bar.get_width() / 2, _h + 0.8,
                     f'{_h:.0f}%', ha='center', va='bottom', color=PRIMARY, fontsize=7)

ax3.set_xticks(_x)
ax3.set_xticklabels(_BUCKET_ORDER, fontsize=9, color=PRIMARY)
ax3.set_ylabel('% of cluster posts', color=PRIMARY, fontsize=11)
ax3.set_xlabel('Time of Day', color=PRIMARY, fontsize=11)
ax3.set_title('Time-of-Day Profile per Cluster  (% within each cluster)',
              color=PRIMARY, fontsize=13, pad=12)
ax3.tick_params(colors=PRIMARY, labelsize=9)
for sp in ax3.spines.values():
    sp.set_edgecolor('#444')
ax3.yaxis.grid(True, linestyle='--', alpha=0.25)
ax3.set_axisbelow(True)
ax3.legend(facecolor='#2a2a2e', edgecolor='#555', labelcolor=PRIMARY, fontsize=9)
plt.tight_layout()
save_export_or_interactive(fig3, "clustering", "03_time_bucket_profile.png", facecolor=BG)
print("Chart 3 done: Time-bucket profile")


# --- Fig 4: Cluster share by hour of day (stacked count) ---------------------
_hour_cluster = (
    _cl_df.groupby(['hour', 'cluster']).size()
    .unstack(fill_value=0)
    .reindex(range(24), fill_value=0)
)

fig4, ax4 = plt.subplots(figsize=(13, 5))
fig4.patch.set_facecolor(BG)
ax4.set_facecolor(BG)
_bottom4 = np.zeros(24)
for _c in range(_best_k):
    _vals4 = _hour_cluster[_c].values if _c in _hour_cluster.columns else np.zeros(24)
    ax4.bar(range(24), _vals4, bottom=_bottom4,
            color=COLORS[_c % len(COLORS)], label=f'Cluster {_c}', width=0.8)
    _bottom4 += _vals4
ax4.set_xticks(range(24))
ax4.set_xticklabels([f'{h:02d}:00' for h in range(24)],
                    rotation=45, ha='right', fontsize=7.5, color=PRIMARY)
ax4.set_xlabel('Hour of Day', color=PRIMARY, fontsize=11)
ax4.set_ylabel('Number of Food Posts', color=PRIMARY, fontsize=11)
ax4.set_title('Cluster Breakdown by Hour of Day', color=PRIMARY, fontsize=13, pad=12)
ax4.tick_params(colors=PRIMARY, labelsize=9)
for sp in ax4.spines.values():
    sp.set_edgecolor('#444')
ax4.yaxis.grid(True, linestyle='--', alpha=0.25)
ax4.set_axisbelow(True)
ax4.legend(facecolor='#2a2a2e', edgecolor='#555', labelcolor=PRIMARY, fontsize=9)
plt.tight_layout()
save_export_or_interactive(fig4, "clustering", "04_cluster_by_hour.png", facecolor=BG)
print("Chart 4 done: Cluster by hour")


# --- Fig 5: Cluster share by day of week (stacked count) ---------------------
_DOW_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
_dow_cluster = (
    _cl_df.groupby(['day_of_week', 'cluster']).size()
    .unstack(fill_value=0)
    .reindex(_DOW_FULL, fill_value=0)
)

fig5, ax5 = plt.subplots(figsize=(10, 5))
fig5.patch.set_facecolor(BG)
ax5.set_facecolor(BG)
_bottom5 = np.zeros(7)
for _c in range(_best_k):
    _vals5 = _dow_cluster[_c].values if _c in _dow_cluster.columns else np.zeros(7)
    ax5.bar(range(7), _vals5, bottom=_bottom5,
            color=COLORS[_c % len(COLORS)], label=f'Cluster {_c}', width=0.7)
    _bottom5 += _vals5
ax5.set_xticks(range(7))
ax5.set_xticklabels(_DOW_FULL, rotation=20, ha='right', fontsize=9.5, color=PRIMARY)
ax5.set_xlabel('Day of Week', color=PRIMARY, fontsize=11)
ax5.set_ylabel('Number of Food Posts', color=PRIMARY, fontsize=11)
ax5.set_title('Cluster Breakdown by Day of Week', color=PRIMARY, fontsize=13, pad=12)
ax5.tick_params(colors=PRIMARY, labelsize=9)
for sp in ax5.spines.values():
    sp.set_edgecolor('#444')
ax5.yaxis.grid(True, linestyle='--', alpha=0.25)
ax5.set_axisbelow(True)
ax5.legend(facecolor='#2a2a2e', edgecolor='#555', labelcolor=PRIMARY, fontsize=9)
plt.tight_layout()
save_export_or_interactive(fig5, "clustering", "05_cluster_by_dow.png", facecolor=BG)
print("Chart 5 done: Cluster by day of week")

print(f"\n✅ K-Means clustering complete: {_best_k} clusters, {len(_cl_df):,} food posts")
