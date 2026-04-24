
import pandas as pd
import matplotlib.pyplot as plt

from graph_output import save_and_close_if_exporting

# ── Design tokens (Zerve dark theme) ──────────────────────────────────────────
VIZ_BG      = "#1D1D20"
VIZ_TEXT    = "#fbfbff"
VIZ_SEC     = "#909094"
VIZ_COLORS  = ["#A1C9F4","#FFB482","#8DE5A1","#FF9F9B","#D0BBFF",
                "#1F77B4","#9467BD","#8C564B","#C49C94","#E377C2"]
VIZ_GOLD    = "#ffd400"
VIZ_GREEN   = "#17b26a"

# Filter only food posts
food_posts = food_df[food_df["is_food_post"] == True].copy()

# Ensure datetime is parsed
food_posts["datetime"] = pd.to_datetime(food_posts["datetime"])
food_posts["week_of_year"] = food_posts["datetime"].dt.isocalendar().week.astype(int)
food_posts["year"] = food_posts["datetime"].dt.year

print(f"Total food posts: {len(food_posts)}")
print(f"Date range: {food_posts['datetime'].min().date()} → {food_posts['datetime'].max().date()}")

# ─── Helper: style axes ────────────────────────────────────────────────────────
def style_ax(ax, title, xlabel="", ylabel=""):
    ax.set_facecolor(VIZ_BG)
    ax.set_title(title, color=VIZ_TEXT, fontsize=14, fontweight="bold", pad=14)
    ax.set_xlabel(xlabel, color=VIZ_SEC, fontsize=11)
    ax.set_ylabel(ylabel, color=VIZ_SEC, fontsize=11)
    ax.tick_params(colors=VIZ_SEC, labelsize=9)
    for sp in ax.spines.values():
        sp.set_edgecolor("#3a3a3d")
    return ax


# ══════════════════════════════════════════════════════════════════════════════
# 1. Bar chart – Food alerts by day of week
# ══════════════════════════════════════════════════════════════════════════════
day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
dow_counts = food_posts["day_of_week"].value_counts().reindex(day_order, fill_value=0)

chart_dow = plt.figure(figsize=(9, 5), facecolor=VIZ_BG)
ax = chart_dow.add_subplot(111)

bars_dow = ax.bar(dow_counts.index, dow_counts.values,
                  color=[VIZ_COLORS[i % len(VIZ_COLORS)] for i in range(7)],
                  width=0.65, zorder=3)

for bar in bars_dow:
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, h + 1, str(int(h)),
            ha="center", va="bottom", color=VIZ_TEXT, fontsize=9)

ax.set_ylim(0, dow_counts.max() * 1.15)
ax.yaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
style_ax(ax, "🍕 Food Alerts by Day of Week", "Day", "Number of Alerts")
ax.tick_params(axis="x", rotation=20, labelsize=10)
chart_dow.tight_layout()
save_and_close_if_exporting(
    chart_dow, "food_patterns", "01_food_alerts_by_day_of_week.png", facecolor=VIZ_BG
)
print("Chart 1 done: Food alerts by day of week")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Heatmap – Food alerts by week of year (year × week grid)
# ══════════════════════════════════════════════════════════════════════════════
week_pivot = (food_posts.groupby(["year","week_of_year"])
              .size()
              .unstack(fill_value=0))

chart_weekly_hm = plt.figure(figsize=(14, 4), facecolor=VIZ_BG)
ax2 = chart_weekly_hm.add_subplot(111)
ax2.set_facecolor(VIZ_BG)

cmap_blue = plt.cm.YlOrRd
im2 = ax2.imshow(week_pivot.values, aspect="auto", cmap=cmap_blue,
                 interpolation="nearest")

ax2.set_yticks(range(len(week_pivot.index)))
ax2.set_yticklabels(week_pivot.index.tolist(), color=VIZ_SEC, fontsize=10)

# Only label every 4th week on x-axis
x_labels = [str(w) if w % 4 == 0 else "" for w in week_pivot.columns]
ax2.set_xticks(range(len(week_pivot.columns)))
ax2.set_xticklabels(x_labels, color=VIZ_SEC, fontsize=8, rotation=0)

cbar2 = chart_weekly_hm.colorbar(im2, ax=ax2, pad=0.01)
cbar2.ax.tick_params(colors=VIZ_SEC, labelsize=8)
cbar2.set_label("Alert Count", color=VIZ_SEC, fontsize=9)

ax2.set_title("📅 Food Alert Activity by Week of Year", color=VIZ_TEXT,
              fontsize=14, fontweight="bold", pad=12)
ax2.set_xlabel("Week of Year", color=VIZ_SEC, fontsize=11)
ax2.set_ylabel("Year", color=VIZ_SEC, fontsize=11)
for sp in ax2.spines.values():
    sp.set_edgecolor("#3a3a3d")
chart_weekly_hm.tight_layout()
save_and_close_if_exporting(
    chart_weekly_hm, "food_patterns", "02_food_alerts_week_of_year_heatmap.png", facecolor=VIZ_BG
)
print("Chart 2 done: Weekly heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Heatmap – Hour of day vs Day of week
# ══════════════════════════════════════════════════════════════════════════════
hour_day_pivot = (food_posts.groupby(["day_of_week","hour"])
                  .size()
                  .unstack(fill_value=0)
                  .reindex(day_order, fill_value=0))
hour_day_pivot = hour_day_pivot.reindex(columns=range(24), fill_value=0)

chart_hour_hm = plt.figure(figsize=(13, 5), facecolor=VIZ_BG)
ax3 = chart_hour_hm.add_subplot(111)
ax3.set_facecolor(VIZ_BG)

im3 = ax3.imshow(hour_day_pivot.values, aspect="auto", cmap="plasma",
                 interpolation="nearest")

ax3.set_yticks(range(7))
ax3.set_yticklabels(day_order, color=VIZ_SEC, fontsize=10)
ax3.set_xticks(range(24))
ax3.set_xticklabels([f"{h:02d}:00" for h in range(24)],
                    color=VIZ_SEC, fontsize=7.5, rotation=45, ha="right")

cbar3 = chart_hour_hm.colorbar(im3, ax=ax3, pad=0.01)
cbar3.ax.tick_params(colors=VIZ_SEC, labelsize=8)
cbar3.set_label("Alert Count", color=VIZ_SEC, fontsize=9)

ax3.set_title("⏰ Food Alert Heatmap: Hour of Day vs Day of Week",
              color=VIZ_TEXT, fontsize=14, fontweight="bold", pad=12)
ax3.set_xlabel("Hour of Day", color=VIZ_SEC, fontsize=11)
ax3.set_ylabel("Day of Week", color=VIZ_SEC, fontsize=11)
for sp in ax3.spines.values():
    sp.set_edgecolor("#3a3a3d")
chart_hour_hm.tight_layout()
save_and_close_if_exporting(
    chart_hour_hm, "food_patterns", "03_hour_vs_day_of_week_heatmap.png", facecolor=VIZ_BG
)
print("Chart 3 done: Hour vs day-of-week heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# 4. Monthly trend line chart
# ══════════════════════════════════════════════════════════════════════════════
food_posts["month_period"] = food_posts["datetime"].dt.to_period("M")
monthly = food_posts.groupby("month_period").size().reset_index(name="count")
monthly["label"] = monthly["month_period"].astype(str)

chart_monthly = plt.figure(figsize=(12, 5), facecolor=VIZ_BG)
ax4 = chart_monthly.add_subplot(111)

ax4.plot(range(len(monthly)), monthly["count"], color=VIZ_COLORS[0],
         linewidth=2.2, marker="o", markersize=5, zorder=3, label="Monthly alerts")

if len(monthly) >= 3:
    rolling_avg = monthly["count"].rolling(3, center=True).mean()
    ax4.plot(range(len(monthly)), rolling_avg, color=VIZ_GOLD,
             linewidth=1.8, linestyle="--", label="3-month avg", zorder=4)

ax4.fill_between(range(len(monthly)), monthly["count"],
                 alpha=0.15, color=VIZ_COLORS[0])

ax4.set_xticks(range(len(monthly)))
ax4.set_xticklabels(monthly["label"], rotation=45, ha="right",
                    color=VIZ_SEC, fontsize=8)
ax4.yaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
ax4.set_axisbelow(True)

legend = ax4.legend(framealpha=0.15, labelcolor=VIZ_TEXT,
                    facecolor="#2a2a2d", edgecolor="#3a3a3d", fontsize=9)
style_ax(ax4, "📈 Monthly Food Alert Trend", "Month", "Number of Alerts")
chart_monthly.tight_layout()
save_and_close_if_exporting(
    chart_monthly, "food_patterns", "04_monthly_food_alert_trend.png", facecolor=VIZ_BG
)
print("Chart 4 done: Monthly trend")


# ══════════════════════════════════════════════════════════════════════════════
# 5. Top senders bar chart
# ══════════════════════════════════════════════════════════════════════════════
top_n = 15
sender_counts = food_posts["sender"].value_counts().head(top_n)

chart_senders = plt.figure(figsize=(10, 6), facecolor=VIZ_BG)
ax5 = chart_senders.add_subplot(111)

colors_top = [VIZ_GOLD if i == 0 else VIZ_COLORS[i % len(VIZ_COLORS)]
              for i in range(len(sender_counts))]
bars_s = ax5.barh(sender_counts.index[::-1], sender_counts.values[::-1],
                  color=colors_top[::-1], height=0.65, zorder=3)

for bar in bars_s:
    w = bar.get_width()
    ax5.text(w + 0.3, bar.get_y() + bar.get_height() / 2, str(int(w)),
             va="center", ha="left", color=VIZ_TEXT, fontsize=9)

ax5.set_xlim(0, sender_counts.max() * 1.15)
ax5.xaxis.grid(True, color="#3a3a3d", linewidth=0.6, zorder=0)
ax5.set_axisbelow(True)
style_ax(ax5, f"👤 Top {top_n} Food Alert Senders", "Number of Food Posts", "Sender")
ax5.tick_params(axis="y", labelsize=9)
chart_senders.tight_layout()
save_and_close_if_exporting(
    chart_senders, "food_patterns", "05_top_food_alert_senders.png", facecolor=VIZ_BG
)
print("Chart 5 done: Top senders")

print("\n✅ All 5 visualizations rendered successfully.")
