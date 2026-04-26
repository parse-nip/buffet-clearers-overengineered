#!/usr/bin/env python3
"""
magic_model.py — Will there be food today?

Generates four charts saved to docs/readme/magic_model/ (and root PNG):
  01_today_heatmap.png     — colour-strip heatmap for today's hours
  02_week_heatmap.png      — 7-day × 24-hour food-probability grid
  03_context_breakdown.png — how each metric contributes today
  04_historical_pattern.png— this day-of-week vs all-days historical pattern

Weights:
  hour of day    40%  — strongest signal
  day of week    30%  — strong context (Fri >> Sun)
  semester       15%  — teaching / exams / break (manually defined)
  month           8%  — mild seasonality
  week of year    7%  — mild weekly cycle

Run:  python magic_model.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.gridspec as gridspec

# ── Weights ────────────────────────────────────────────────────────────────────
W_HOUR     = 0.40
W_DOW      = 0.30
W_SEMESTER = 0.15
W_MONTH    = 0.08
W_WEEK     = 0.07

# ── SMU academic calendar (manually defined) ───────────────────────────────────
# Teaching score follows a ramp-up / plateau / taper within the semester.
# Exams:  moderate — study groups still generate food events
# Break:  very low — campus nearly empty
_CALENDAR: list[tuple[date, date, str, str]] = [
    (date(2023,  8, 14), date(2023, 11, 24), 'teaching', 'S1 23/24'),
    (date(2023, 11, 25), date(2023, 12,  9), 'exams',    'Exams S1 23/24'),
    (date(2023, 12, 10), date(2024,  1, 14), 'break',    'Winter Break'),
    (date(2024,  1, 15), date(2024,  4, 19), 'teaching', 'S2 23/24'),
    (date(2024,  4, 20), date(2024,  5,  4), 'exams',    'Exams S2 23/24'),
    (date(2024,  5,  5), date(2024,  8, 11), 'break',    'Summer 2024'),
    (date(2024,  8, 12), date(2024, 11, 22), 'teaching', 'S1 24/25'),
    (date(2024, 11, 23), date(2024, 12,  7), 'exams',    'Exams S1 24/25'),
    (date(2024, 12,  8), date(2025,  1, 12), 'break',    'Winter Break'),
    (date(2025,  1, 13), date(2025,  4, 18), 'teaching', 'S2 24/25'),
    (date(2025,  4, 19), date(2025,  5,  3), 'exams',    'Exams S2 24/25'),
    (date(2025,  5,  4), date(2025,  8, 10), 'break',    'Summer 2025'),
    (date(2025,  8, 11), date(2025, 11, 21), 'teaching', 'S1 25/26'),
    (date(2025, 11, 22), date(2025, 12,  6), 'exams',    'Exams S1 25/26'),
    (date(2025, 12,  7), date(2026,  1, 11), 'break',    'Winter Break'),
    (date(2026,  1, 12), date(2026,  4, 17), 'teaching', 'S2 25/26'),
    (date(2026,  4, 18), date(2026,  5,  2), 'exams',    'Exams S2 25/26'),
    (date(2026,  5,  3), date(2026,  8, 10), 'break',    'Summer 2026'),
]
_BASE = {'teaching': 1.0, 'exams': 0.45, 'break': 0.05}


def _semester_info(d: date) -> tuple[float, str, str]:
    """(score 0–1, human label, type) for a given date."""
    for start, end, stype, label in _CALENDAR:
        if start <= d <= end:
            score = _BASE[stype]
            if stype == 'teaching':
                total   = (end - start).days
                elapsed = (d - start).days
                frac    = elapsed / total
                if frac < 0.15:
                    score = 0.55 + 0.45 * (frac / 0.15)
                elif frac > 0.80:
                    score = 0.60 + 0.40 * ((1.0 - frac) / 0.20)
                else:
                    score = 1.0
                week_num    = int(elapsed / 7) + 1
                total_weeks = max(int(total / 7), 1)
                label = f'{label}  wk {week_num}/{total_weeks}'
            return score, label, stype
    return 0.05, 'Break / Unknown', 'break'


# ── Design tokens ──────────────────────────────────────────────────────────────
BG      = '#1D1D20'
PRIMARY = '#fbfbff'
SEC     = '#909094'
GREEN   = '#17b26a'
GOLD    = '#ffd400'
RED     = '#f04438'
DIM     = '#2b2b2f'

_CMAP = LinearSegmentedColormap.from_list('food', [RED, GOLD, GREEN])

plt.rcParams.update({
    'figure.facecolor': BG, 'axes.facecolor': BG,
    'text.color': PRIMARY, 'axes.labelcolor': PRIMARY,
    'xtick.color': SEC, 'ytick.color': SEC,
    'axes.edgecolor': '#333', 'grid.color': '#2a2a2e',
    'font.family': 'sans-serif',
})

DOW_NAMES   = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DOW_SHORT   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
MONTH_NAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# ── Paths ───────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
_export_root = os.environ.get("BUFFET_GRAPH_ROOT", "").strip()
if _export_root:
    DOCS_DIR = Path(_export_root) / "magic_model"
else:
    DOCS_DIR = ROOT / "docs" / "readme" / "magic_model"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ── Data ───────────────────────────────────────────────────────────────────────
for _p in [ROOT / 'data' / 'result.json', ROOT / 'data' / 'chat_export.json',
           ROOT / 'data' / 'chat_export.sample.json']:
    if _p.exists():
        _raw = json.loads(_p.read_text(encoding='utf-8'))
        break
else:
    sys.exit('No chat data found. Put data/result.json in the project root.')

_msgs = [m for m in _raw['messages'] if m.get('type') == 'message']

_FOOD_RE = re.compile(
    r'\b(cleared|gone|finished|available|left|remaining|free food|buffet|food alert|'
    r'food|eat|pizza|cake|noodle|rice|lunch|dinner|breakfast|snack|drink|dessert)\b',
    re.IGNORECASE,
)

def _text(msg: dict) -> str:
    raw = msg.get('text', '')
    if isinstance(raw, list):
        return ''.join(t if isinstance(t, str) else t.get('text', '') for t in raw)
    return str(raw)

records = []
for m in _msgs:
    txt = _text(m)
    if m.get('photo') or re.search(r'[@＠]', txt) or _FOOD_RE.search(txt):
        dt = pd.to_datetime(m['date'])
        records.append({
            'hour':  int(dt.hour),
            'dow':   int(dt.weekday()),
            'month': int(dt.month),
            'week':  int(dt.isocalendar()[1]),
        })

df = pd.DataFrame(records)
print(f'Food posts: {len(df):,} / {len(_msgs):,} total messages')

# ── Empirical distributions (peak bin normalised to 1.0) ──────────────────────
def _normed(series: pd.Series, size: int, offset: int = 0) -> np.ndarray:
    counts = np.zeros(size, dtype=float)
    for v in series:
        idx = int(v) - offset
        if 0 <= idx < size:
            counts[idx] += 1
    mx = counts.max()
    return counts / mx if mx > 0 else counts

p_hour  = _normed(df['hour'],  24, offset=0)
p_dow   = _normed(df['dow'],   7,  offset=0)
p_month = _normed(df['month'], 12, offset=1)
p_week  = _normed(df['week'],  53, offset=1)

# ── Today's context ────────────────────────────────────────────────────────────
now         = datetime.now()
today_date  = now.date()
today_hour  = now.hour
today_dow   = now.weekday()
today_month = now.month
today_week  = int(now.isocalendar()[1])

ctx_dow   = float(p_dow[today_dow])
ctx_month = float(p_month[today_month - 1])
ctx_week  = float(p_week[min(today_week - 1, 52)])
ctx_sem, sem_label, sem_type = _semester_info(today_date)
sem_color = {'teaching': GREEN, 'exams': GOLD, 'break': RED}[sem_type]

print(f'Semester: {sem_label}  (score={ctx_sem:.2f}, type={sem_type})')

def _day_scores(d: datetime) -> np.ndarray:
    """Raw (unnormalised) 24-element score array for any given day."""
    _dow   = d.weekday()
    _month = d.month
    _week  = int(d.isocalendar()[1])
    _sem, _, _ = _semester_info(d.date())
    return (W_HOUR * p_hour
            + W_DOW      * float(p_dow[_dow])
            + W_SEMESTER * _sem
            + W_MONTH    * float(p_month[_month - 1])
            + W_WEEK     * float(p_week[min(_week - 1, 52)]))

scores_today = _day_scores(now)
scores_norm  = scores_today / scores_today.max()

future_hours = list(range(today_hour + 1, 24))
best_hour    = max(future_hours, key=lambda h: scores_norm[h]) if future_hours else None

def _save(fig, filename: str, also_root_as: str | None = None) -> None:
    path = DOCS_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG)
    if also_root_as and not _export_root:
        fig.savefig(ROOT / also_root_as, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"  {rel.as_posix()}")


# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — Today heatmap strip
# ─────────────────────────────────────────────────────────────────────────────
def _cell_text_color(score: float, is_past: bool) -> str:
    if is_past:
        return '#555'
    return 'black' if score > 0.60 else PRIMARY

def _draw_heatmap_row(ax, scores_24: np.ndarray, current_hour: int | None,
                      y: float = 0.0, h: float = 1.0, show_pct: bool = True) -> None:
    """Draw one 24-cell heatmap row on ax (data coords: x=hour, y=y..y+h)."""
    for col in range(24):
        s = scores_24[col]
        is_past = current_hour is not None and col < current_hour
        is_now  = current_hour is not None and col == current_hour
        fc      = DIM if is_past else _CMAP(float(s))

        ax.add_patch(plt.Rectangle((col, y), 1, h,
                                   facecolor=fc, edgecolor='#1D1D20', linewidth=0.6, zorder=2))
        if is_now:
            ax.add_patch(plt.Rectangle((col, y), 1, h,
                                       facecolor='none', edgecolor=GOLD, linewidth=2.8, zorder=4))

        tc = _cell_text_color(s, is_past)
        mid_y = y + h / 2
        ax.text(col + 0.5, mid_y + h * 0.16, f'{col:02d}:00',
                ha='center', va='center', fontsize=6.5, color=tc, zorder=5)
        if show_pct and not is_past:
            ax.text(col + 0.5, mid_y - h * 0.16, f'{s:.0%}',
                    ha='center', va='center', fontsize=7.5, color=tc,
                    fontweight='bold', zorder=5)
        elif is_past:
            ax.text(col + 0.5, mid_y, f'{col:02d}', ha='center', va='center',
                    fontsize=7, color='#444', zorder=5)

    # NOW label above
    if current_hour is not None and current_hour < 24:
        ax.annotate('NOW', xy=(current_hour + 0.5, y + h),
                    xytext=(current_hour + 0.5, y + h + 0.22),
                    ha='center', va='bottom', fontsize=8, color=GOLD, fontweight='bold',
                    xycoords='data', textcoords='data',
                    arrowprops=dict(arrowstyle='->', color=GOLD, lw=1.3), zorder=6)


fig1 = plt.figure(figsize=(16, 4.2))
fig1.patch.set_facecolor(BG)
gs1 = gridspec.GridSpec(3, 1, figure=fig1, height_ratios=[1.2, 3.5, 1.3], hspace=0.0)

ax1_title   = fig1.add_subplot(gs1[0])
ax1_heat    = fig1.add_subplot(gs1[1])
ax1_metrics = fig1.add_subplot(gs1[2])

for _ax in (ax1_title, ax1_heat, ax1_metrics):
    _ax.set_facecolor(BG)
    _ax.axis('off')

# Title row
ax1_title.set_xlim(0, 1); ax1_title.set_ylim(0, 1)
title_str = (f'Will there be food?  —  '
             f'{DOW_NAMES[today_dow]} {now.day} {MONTH_NAMES[today_month]} {now.year}')
ax1_title.text(0.01, 0.5, title_str, color=PRIMARY, fontsize=14, fontweight='bold',
               va='center', transform=ax1_title.transAxes)
ax1_title.text(0.99, 0.5, sem_label, color=sem_color, fontsize=9, fontweight='bold',
               va='center', ha='right', transform=ax1_title.transAxes,
               bbox=dict(boxstyle='round,pad=0.35', facecolor='#252528',
                         edgecolor=sem_color, alpha=0.9))

# Heatmap
ax1_heat.set_xlim(0, 24)
ax1_heat.set_ylim(0, 1.55)
_draw_heatmap_row(ax1_heat, scores_norm, current_hour=today_hour, y=0.1, h=1.0)

# Best-next annotation below strip
if best_hour is not None:
    bs = scores_norm[best_hour]
    label_col = GREEN if bs >= 0.65 else GOLD
    ax1_heat.annotate(
        f'best next: {best_hour:02d}:00 ({bs:.0%})',
        xy=(best_hour + 0.5, 0.1),
        xytext=(best_hour + 0.5, -0.15),
        ha='center', va='top', fontsize=8, color=label_col, fontweight='bold',
        xycoords='data', textcoords='data',
        arrowprops=dict(arrowstyle='->', color=SEC, lw=0.9), zorder=6,
    )

# Metric strip
ax1_metrics.set_xlim(0, 1); ax1_metrics.set_ylim(0, 1)
_metrics = [
    ('hour of day',  W_HOUR,     None,      'varies per cell'),
    ('day of week',  W_DOW,      ctx_dow,   DOW_SHORT[today_dow]),
    ('semester',     W_SEMESTER, ctx_sem,   sem_label.split('  ')[0]),
    ('month',        W_MONTH,    ctx_month, MONTH_NAMES[today_month]),
    ('week of year', W_WEEK,     ctx_week,  f'wk {today_week}'),
]
_stripe_colors = [GREEN, '#A1C9F4', sem_color, '#FFB482', '#D0BBFF']
_x = 0.01
for i, (name, weight, score, tag) in enumerate(_metrics):
    score_str = f'{score:.0%}' if score is not None else '--'
    ax1_metrics.text(_x, 0.85, name,                  color=SEC,               fontsize=7.5, va='top', family='monospace')
    ax1_metrics.text(_x, 0.50, f'x{weight:.0%}',      color=_stripe_colors[i], fontsize=9,   va='top', fontweight='bold', family='monospace')
    ax1_metrics.text(_x, 0.14, f'{score_str}  {tag}', color=PRIMARY,           fontsize=7,   va='top', family='monospace', alpha=0.72)
    _x += 0.20

fig1.text(0.99, 0.005, 'magic_model · buffet clearers', ha='right', va='bottom',
          color='#333', fontsize=7)

print('Saving charts:')
_save(fig1, '01_today_heatmap.png', also_root_as='magic_model_today.png')


# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 — 7-day × 24-hour heatmap
# ─────────────────────────────────────────────────────────────────────────────
_days = [now + timedelta(days=i) for i in range(7)]
_week_raw = np.array([_day_scores(d) for d in _days])   # (7, 24)
# Normalise globally so colours are comparable across days
_global_max = _week_raw.max()
_week_norm  = _week_raw / _global_max if _global_max > 0 else _week_raw

# Mask today's past hours as NaN (shown dimmed)
_week_plot = _week_norm.copy().astype(float)
for _c in range(today_hour):
    _week_plot[0, _c] = np.nan

_cmap_nan = _CMAP.copy()
_cmap_nan.set_bad(color=DIM)

_row_labels = [f'{DOW_SHORT[d.weekday()]}  {d.day}/{d.month}' for d in _days]

fig2, ax2 = plt.subplots(figsize=(17, 5))
fig2.patch.set_facecolor(BG)
ax2.set_facecolor(BG)

im2 = ax2.imshow(_week_plot, cmap=_cmap_nan, vmin=0, vmax=1,
                  aspect='auto', interpolation='nearest')

# Cell text
for r in range(7):
    for c in range(24):
        if r == 0 and c < today_hour:
            continue
        s = _week_norm[r, c]
        tc = 'black' if s > 0.60 else PRIMARY
        ax2.text(c, r, f'{s:.0%}', ha='center', va='center',
                 fontsize=6.5, color=tc, fontweight='bold')

# Highlight today's row
ax2.add_patch(plt.Rectangle((-0.5, -0.5), 24, 1,
                              facecolor='none', edgecolor=GOLD, linewidth=2.0, zorder=5))
# NOW column marker
if today_hour < 24:
    ax2.axvline(today_hour - 0.5, color=GOLD, linewidth=1.5, linestyle='--', alpha=0.6, zorder=4)
    ax2.text(today_hour, -0.85, 'NOW', ha='center', va='top', color=GOLD,
             fontsize=7.5, fontweight='bold')

ax2.set_xticks(range(24))
ax2.set_xticklabels([f'{h:02d}:00' for h in range(24)],
                     rotation=45, ha='right', fontsize=8, color=SEC)
ax2.set_yticks(range(7))
ax2.set_yticklabels(_row_labels, fontsize=9, color=PRIMARY)
ax2.tick_params(length=0)

# Semester badges per row
for r, d in enumerate(_days):
    _, _sl, _st = _semester_info(d.date())
    _sc = {'teaching': GREEN, 'exams': GOLD, 'break': RED}[_st]
    _short = _sl.split('  ')[0]
    ax2.text(24.2, r, _short, va='center', fontsize=7, color=_sc, fontweight='bold')

ax2.set_xlim(-0.5, 24.5)
for spine in ax2.spines.values():
    spine.set_edgecolor('#333')
ax2.set_title('7-day food probability outlook  (globally normalised)',
              color=PRIMARY, fontsize=13, pad=12, loc='left', fontweight='bold')

fig2.tight_layout()
_save(fig2, '02_week_heatmap.png')


# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 — Context breakdown: what factors drive today's score
# ─────────────────────────────────────────────────────────────────────────────
fig3 = plt.figure(figsize=(11, 4.5))
fig3.patch.set_facecolor(BG)
gs3 = gridspec.GridSpec(1, 2, figure=fig3, width_ratios=[3, 2], wspace=0.35)
ax3l = fig3.add_subplot(gs3[0])   # contribution bars
ax3r = fig3.add_subplot(gs3[1])   # overall score gauge
for _ax in (ax3l, ax3r):
    _ax.set_facecolor(BG)

# Left: weighted contribution bars
_factor_scores = [
    ('Hour of day',  W_HOUR,     None,      'varies per hour', GREEN,    [GREEN, '#A1C9F4']),
    ('Day of week',  W_DOW,      ctx_dow,   DOW_NAMES[today_dow],        '#A1C9F4', None),
    ('Semester',     W_SEMESTER, ctx_sem,   sem_label,          sem_color, None),
    ('Month',        W_MONTH,    ctx_month, MONTH_NAMES[today_month],    '#FFB482', None),
    ('Week of year', W_WEEK,     ctx_week,  f'Week {today_week}',        '#D0BBFF', None),
]
_factor_colors = [GREEN, '#A1C9F4', sem_color, '#FFB482', '#D0BBFF']

_ys = list(range(len(_factor_scores)))[::-1]  # top-to-bottom
ax3l.set_xlim(-0.02, 0.55)
ax3l.set_ylim(-0.5, len(_factor_scores) - 0.5)
ax3l.set_facecolor(BG)

for i, (name, weight, score, context, *_) in enumerate(_factor_scores):
    y   = _ys[i]
    fc  = _factor_colors[i]
    # Max weight bar (ghost)
    ax3l.barh(y, weight, height=0.52, color=fc, alpha=0.18, left=0, zorder=2)
    # Actual contribution = weight × score (use midpoint for "varies")
    contribution = weight * (score if score is not None else scores_norm.mean())
    ax3l.barh(y, contribution, height=0.52, color=fc, alpha=0.85, left=0, zorder=3)
    # Labels
    score_str = f'{score:.0%}' if score is not None else f'avg {scores_norm.mean():.0%}'
    ax3l.text(-0.015, y, f'x{weight:.0%}', va='center', ha='right',
              color=fc, fontsize=9, fontweight='bold')
    ax3l.text(weight + 0.012, y + 0.15, name,
              va='center', color=PRIMARY, fontsize=9)
    ax3l.text(weight + 0.012, y - 0.18, f'{context}  ({score_str})',
              va='center', color=SEC, fontsize=7.5)

ax3l.axis('off')
ax3l.set_title('Metric contributions today', color=PRIMARY, fontsize=12,
               pad=10, loc='left', fontweight='bold')

# Right: overall likelihood gauge (today's average across remaining hours)
_remaining = scores_norm[today_hour:] if today_hour < 24 else scores_norm
_avg_remaining = float(_remaining.mean())
_peak_remaining = float(_remaining.max())

ax3r.set_xlim(0, 1); ax3r.set_ylim(0, 1); ax3r.axis('off')
# Big number
_gauge_color = _CMAP(_avg_remaining)
ax3r.text(0.5, 0.68, f'{_avg_remaining:.0%}', ha='center', va='center',
          fontsize=44, fontweight='bold', color=_gauge_color,
          transform=ax3r.transAxes)
ax3r.text(0.5, 0.44, 'avg likelihood', ha='center', va='center',
          fontsize=9, color=SEC, transform=ax3r.transAxes)
ax3r.text(0.5, 0.30, f'remaining hours today', ha='center', va='center',
          fontsize=8, color=SEC, transform=ax3r.transAxes)
ax3r.text(0.5, 0.14, f'peak: {_peak_remaining:.0%}  at {best_hour:02d}:00' if best_hour else '',
          ha='center', va='center', fontsize=8.5, color=PRIMARY, fontweight='bold',
          transform=ax3r.transAxes)
ax3r.text(0.5, 0.88, sem_label.split('  ')[0], ha='center', va='center',
          fontsize=9, color=sem_color, fontweight='bold', transform=ax3r.transAxes,
          bbox=dict(boxstyle='round,pad=0.3', facecolor='#252528', edgecolor=sem_color))

_save(fig3, '03_context_breakdown.png')


# ─────────────────────────────────────────────────────────────────────────────
# CHART 4 — Historical pattern: today's day-of-week vs all days
# ─────────────────────────────────────────────────────────────────────────────
df_dow = df[df['dow'] == today_dow]
p_hour_dow = _normed(df_dow['hour'], 24)  # this-day-of-week empirical dist

fig4, ax4 = plt.subplots(figsize=(15, 4.2))
fig4.patch.set_facecolor(BG)
ax4.set_facecolor(BG)

_x = np.arange(24)
_bar_w = 0.38
_bars_all = ax4.bar(_x - _bar_w/2, p_hour, width=_bar_w, color='#A1C9F4',
                     alpha=0.55, label='All days')
_bars_dow = ax4.bar(_x + _bar_w/2, p_hour_dow, width=_bar_w,
                     color=GOLD, alpha=0.85, label=f'{DOW_NAMES[today_dow]}s only',
                     edgecolor='none')

# Highlight current and remaining hours
for h in range(today_hour, 24):
    ax4.axvspan(h - _bar_w, h + _bar_w, color=PRIMARY, alpha=0.04, zorder=0)
if today_hour < 24:
    ax4.axvline(today_hour - 0.5, color=GOLD, linewidth=1.2, linestyle='--', alpha=0.5)
    ax4.text(today_hour, ax4.get_ylim()[1] if p_hour.max() > 0 else 1, 'now',
             ha='center', va='bottom', color=GOLD, fontsize=8)

ax4.set_xticks(_x)
ax4.set_xticklabels([f'{h:02d}:00' for h in range(24)],
                     rotation=45, ha='right', fontsize=8, color=SEC)
ax4.set_ylabel('Relative frequency', color=SEC, fontsize=10)
ax4.tick_params(length=0)
ax4.yaxis.grid(True, linestyle='--', alpha=0.12, color='#666')
ax4.set_axisbelow(True)
for spine in ax4.spines.values():
    spine.set_edgecolor('#2a2a2e')

_n_dow = len(df_dow)
_n_all = len(df)
_legend = ax4.legend(facecolor='#252528', edgecolor='#444',
                      labelcolor=PRIMARY, fontsize=9, loc='upper left')
ax4.set_title(
    f'Historical food-post frequency by hour  —  '
    f'{DOW_NAMES[today_dow]}s ({_n_dow} posts) vs all days ({_n_all} posts)',
    color=PRIMARY, fontsize=12, pad=12, loc='left', fontweight='bold'
)
ax4.text(0.99, 1.02, 'normalised to peak = 1.0', transform=ax4.transAxes,
         ha='right', va='bottom', color=SEC, fontsize=8)

fig4.tight_layout()
_save(fig4, '04_historical_pattern.png')


def _write_magic_json_specs() -> None:
    """ECharts companion JSON under out/data/magic_model/ (when BUFFET_GRAPH_ROOT is set)."""
    if not os.environ.get("BUFFET_GRAPH_ROOT", "").strip():
        return
    from chart_json import write_chart_spec

    hour_labels = [f"{h:02d}:00" for h in range(24)]
    hour_vals = [float(scores_norm[h]) for h in range(24)]
    _best_lbl = (
        GREEN
        if best_hour is not None and float(scores_norm[best_hour]) >= 0.65
        else GOLD
    )
    write_chart_spec(
        "magic_model",
        "01_today_heatmap.png",
        {
            "chart": "magicStrip",
            "title": "Will there be food?",
            "subtitle": (
                f"{DOW_NAMES[today_dow]} {now.day} {MONTH_NAMES[today_month]} {now.year}"
            ),
            "semesterBadge": {
                "text": sem_label.split("  ")[0],
                "borderColor": sem_color,
            },
            "scores": hour_vals,
            "currentHour": today_hour,
            "bestNextHour": best_hour,
            "bestNextLabelColor": _best_lbl,
            "metrics": [
                {
                    "name": name,
                    "weight": float(weight),
                    "scoreText": f"{score:.0%}" if score is not None else "--",
                    "tag": str(tag),
                    "accentColor": _stripe_colors[i],
                }
                for i, (name, weight, score, tag) in enumerate(_metrics)
            ],
        },
    )

    week_mat = _week_norm.astype(float).copy()
    for _c in range(today_hour):
        week_mat[0, _c] = week_mat[0, _c] * 0.12
    write_chart_spec(
        "magic_model",
        "02_week_heatmap.png",
        {
            "chart": "heatmap",
            "title": "7-day food probability outlook",
            "subtitle": "Globally normalised · dimmed cells = earlier today (already passed)",
            "yCategories": _row_labels,
            "xCategories": hour_labels,
            "data": week_mat.tolist(),
        },
    )

    _avg_r = float(scores_norm[today_hour:].mean()) if today_hour < 24 else float(scores_norm.mean())
    _peak_r = float(scores_norm[today_hour:].max()) if today_hour < 24 else float(scores_norm.max())
    _contrib_cats: list[str] = []
    _contrib_vals: list[float] = []
    for name, weight, score, context, *_ in _factor_scores:
        sc = score if score is not None else float(scores_norm.mean())
        _contrib_cats.append(f"{name} — {context}")
        _contrib_vals.append(round(float(weight * sc), 5))
    _gauge_msg = (
        f"Avg likelihood (rest of today): {_avg_r:.0%}\n"
        f"Peak remaining: {_peak_r:.0%}"
        + (f" at {best_hour:02d}:00" if best_hour is not None else "")
        + f"\n{sem_label.split('  ')[0]}"
    )
    write_chart_spec(
        "magic_model",
        "03_context_breakdown.png",
        {
            "chart": "composite",
            "title": "What drives today's score",
            "subtitle": "Weighted contributions + snapshot for hours still ahead",
            "panels": [
                {
                    "chart": "barh",
                    "title": "Metric contributions (weight × context)",
                    "reverseY": True,
                    "categories": _contrib_cats,
                    "values": _contrib_vals,
                },
                {
                    "chart": "message",
                    "title": "Rest of today",
                    "message": _gauge_msg,
                },
            ],
        },
    )

    write_chart_spec(
        "magic_model",
        "04_historical_pattern.png",
        {
            "chart": "barGroup",
            "title": "Historical food-post frequency by hour",
            "subtitle": (
                f"{DOW_NAMES[today_dow]}s ({len(df_dow):,} posts) vs all days ({len(df):,} posts) "
                "· normalised to peak = 1"
            ),
            "categories": hour_labels,
            "rotateX": 45,
            "series": [
                {"name": "All days", "values": p_hour.tolist(), "color": "#7eb8e8"},
                {
                    "name": f"{DOW_NAMES[today_dow]}s",
                    "values": p_hour_dow.tolist(),
                    "color": "#c4921c",
                },
            ],
        },
    )


_write_magic_json_specs()

print(f"\nAll charts saved under {DOCS_DIR}")
if not _export_root:
    print("Root copy: magic_model_today.png")
