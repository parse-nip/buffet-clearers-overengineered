
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from chart_json import write_chart_spec
from graph_output import save_export_or_interactive
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    mean_squared_error, mean_absolute_error, r2_score
)

# ── Zerve Design System ────────────────────────────────────────────────────────
BG      = '#1D1D20'
PRIMARY = '#fbfbff'
SEC     = '#909094'
COLORS  = ['#A1C9F4', '#FFB482', '#8DE5A1', '#FF9F9B', '#D0BBFF',
           '#1F77B4', '#9467BD', '#8C564B', '#E377C2', '#F7B6D2']
GOLD    = '#ffd400'
GREEN   = '#17b26a'
RED     = '#f04438'

plt.rcParams.update({
    'figure.facecolor': BG, 'axes.facecolor': BG,
    'text.color': PRIMARY, 'axes.labelcolor': PRIMARY,
    'xtick.color': PRIMARY, 'ytick.color': PRIMARY,
    'axes.edgecolor': '#444', 'grid.color': '#333',
    'font.family': 'sans-serif',
})


def _stratify_if_viable(y: pd.Series, *, test_size: float = 0.2):
    """Use stratify only when sklearn can place at least one sample per class in test."""
    y = pd.Series(y)
    if y.nunique() <= 1:
        return None
    if (y.value_counts() < 2).any():
        return None
    n_test = max(1, int(np.ceil(len(y) * test_size)))
    if n_test < y.nunique():
        return None
    return y


def _plot_feature_importance(importances, color, title, outfile,
                              xlabel='Feature Importance'):
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    bars = ax.barh(importances.index, importances.values, color=color, edgecolor='none')
    bars[-1].set_color(GOLD)
    ax.set_xlabel(xlabel, color=PRIMARY, fontsize=10)
    ax.set_title(title, color=PRIMARY, fontsize=13, pad=12)
    ax.tick_params(colors=PRIMARY, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor('#444')
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)
    plt.tight_layout()
    save_export_or_interactive(fig, "prediction_model", outfile, facecolor=BG)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  FEATURE ENGINEERING FOR MODEL
# ─────────────────────────────────────────────────────────────────────────────
_df = food_df.copy()

# Encode top senders (top-30 → own column; rest → 'Other')
_top_senders = _df['sender'].value_counts().head(30).index
_df['sender_encoded'] = _df['sender'].where(_df['sender'].isin(_top_senders), 'Other')
_sender_le = LabelEncoder()
_df['sender_enc'] = _sender_le.fit_transform(_df['sender_encoded'])

# Encode extracted location (top-20 → own column; rest → 'Other/None')
_df['location_clean'] = _df['location_extracted'].fillna('Unknown')
_top_locs = _df['location_clean'].value_counts().head(20).index
_df['location_clean'] = _df['location_clean'].where(_df['location_clean'].isin(_top_locs), 'Other')
_loc_le = LabelEncoder()
_df['location_enc'] = _loc_le.fit_transform(_df['location_clean'])

# Boolean → int
_bool_cols = ['has_photo', 'has_location', 'is_reply', 'is_edited',
              'is_forwarded', 'has_at_location', 'is_weekend']
for _c in _bool_cols:
    _df[_c] = _df[_c].astype(int)

# Shared feature set (no leakage, no target itself)
MODEL_FEATURES = [
    'hour', 'day_of_week_n', 'month', 'is_weekend',
    'has_photo', 'has_at_location', 'text_length',
    'reaction_count', 'is_reply', 'is_edited', 'is_forwarded',
    'sender_enc',
]

# ─────────────────────────────────────────────────────────────────────────────
# 2.  MODEL A — Classify: Is this a food post? (WHEN food appears)
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 65)
print("MODEL A — Is this a food-alert post?  (binary classification)")
print("=" * 65)

X_a = _df[MODEL_FEATURES].fillna(0)
y_a = _df['is_food_post'].astype(int)

_strat_a = _stratify_if_viable(y_a)
X_a_train, X_a_test, y_a_train, y_a_test = train_test_split(
    X_a, y_a, test_size=0.20, random_state=42, stratify=_strat_a
)

clf = GradientBoostingClassifier(
    n_estimators=200, max_depth=5, learning_rate=0.08,
    subsample=0.8, random_state=42
)
clf.fit(X_a_train, y_a_train)
y_a_pred = clf.predict(X_a_test)
y_a_prob = clf.predict_proba(X_a_test)[:, 1]

acc_a = accuracy_score(y_a_test, y_a_pred)
cv_a  = cross_val_score(clf, X_a, y_a, cv=5, scoring='accuracy').mean()

print(f"\n  Accuracy (test set)  : {acc_a:.4f}")
print(f"  Accuracy (5-fold CV) : {cv_a:.4f}")
print(f"\n  Classification Report:\n")
print(classification_report(y_a_test, y_a_pred,
                             target_names=['Not Food Post', 'Food Post']))

# ─────────────────────────────────────────────────────────────────────────────
# 3.  MODEL B — Predict hour of day food posts arrive (regression, food posts only)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("MODEL B — Predict HOUR food posts appear  (regression)")
print("=" * 65)

_food_only = _df[_df['is_food_post'] == 1].copy()
REG_FEATURES = ['day_of_week_n', 'month', 'is_weekend',
                'has_photo', 'has_at_location', 'text_length',
                'reaction_count', 'is_reply', 'sender_enc']

X_b = _food_only[REG_FEATURES].fillna(0)
y_b = _food_only['hour']

X_b_train, X_b_test, y_b_train, y_b_test = train_test_split(
    X_b, y_b, test_size=0.20, random_state=42
)

reg = GradientBoostingRegressor(
    n_estimators=200, max_depth=4, learning_rate=0.08,
    subsample=0.8, random_state=42
)
reg.fit(X_b_train, y_b_train)
y_b_pred = reg.predict(X_b_test)

rmse_b = np.sqrt(mean_squared_error(y_b_test, y_b_pred))
mae_b  = mean_absolute_error(y_b_test, y_b_pred)
r2_b   = r2_score(y_b_test, y_b_pred)

print(f"\n  RMSE (test set)      : {rmse_b:.3f} hours")
print(f"  MAE  (test set)      : {mae_b:.3f} hours")
print(f"  R²   (test set)      : {r2_b:.4f}")

# ─────────────────────────────────────────────────────────────────────────────
# 4.  MODEL C — Classify location of food post (top locations)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("MODEL C — Predict WHERE food appears  (multi-class classification)")
print("=" * 65)

_loc_df = _food_only[_food_only['location_extracted'].notna()].copy()
_loc_df['loc_label_raw'] = _loc_df['location_extracted'].str.split(';').str[0].str.strip()

# Keep top-8 most common first-extracted locations
_top8 = _loc_df['loc_label_raw'].value_counts().head(8).index.tolist()
_loc_df = _loc_df[_loc_df['loc_label_raw'].isin(_top8)].copy()

_loc_enc = LabelEncoder()
_loc_df['loc_label'] = _loc_enc.fit_transform(_loc_df['loc_label_raw'])

LOC_FEATURES = ['hour', 'day_of_week_n', 'month', 'is_weekend',
                'has_photo', 'text_length', 'reaction_count',
                'is_reply', 'sender_enc']

X_c = _loc_df[LOC_FEATURES].fillna(0)
y_c = _loc_df['loc_label']

_strat_c = _stratify_if_viable(y_c)
X_c_train, X_c_test, y_c_train, y_c_test = train_test_split(
    X_c, y_c, test_size=0.20, random_state=42, stratify=_strat_c
)

clf_loc = GradientBoostingClassifier(
    n_estimators=200, max_depth=4, learning_rate=0.08,
    subsample=0.8, random_state=42
)
clf_loc.fit(X_c_train, y_c_train)
y_c_pred = clf_loc.predict(X_c_test)
acc_c = accuracy_score(y_c_test, y_c_pred)
cv_c  = cross_val_score(clf_loc, X_c, y_c, cv=5, scoring='accuracy').mean()

print(f"\n  Classes              : {list(_loc_enc.classes_)}")
print(f"  Sample size          : {len(_loc_df):,} food posts with parsed location")
print(f"  Accuracy (test set)  : {acc_c:.4f}")
print(f"  Accuracy (5-fold CV) : {cv_c:.4f}")
print(f"\n  Classification Report:\n")
print(classification_report(y_c_test, y_c_pred,
                             target_names=list(_loc_enc.classes_)))

# ─────────────────────────────────────────────────────────────────────────────
# 5.  VISUALISATIONS
# ─────────────────────────────────────────────────────────────────────────────

fi_a = pd.Series(clf.feature_importances_, index=MODEL_FEATURES).sort_values()
fi_b = pd.Series(reg.feature_importances_, index=REG_FEATURES).sort_values()
fi_c = pd.Series(clf_loc.feature_importances_, index=LOC_FEATURES).sort_values()

_plot_feature_importance(
    fi_a, COLORS[0],
    'Feature Importance — Model A: Food Post Classifier',
    'feat_importance_clf.png',
    xlabel='Feature Importance (mean decrease in impurity)',
)
write_chart_spec(
    "prediction_model",
    "feat_importance_clf.png",
    {
        "chart": "barh",
        "title": "Feature Importance — Model A: Food Post Classifier",
        "subtitle": "Mean decrease in impurity (gradient boosting)",
        "highlight": "last",
        "categories": [str(x) for x in fi_a.index.tolist()],
        "values": [float(x) for x in fi_a.values.tolist()],
    },
)
_plot_feature_importance(
    fi_b, COLORS[1],
    'Feature Importance — Model B: Hour Prediction (Regression)',
    'feat_importance_reg.png',
)
write_chart_spec(
    "prediction_model",
    "feat_importance_reg.png",
    {
        "chart": "barh",
        "title": "Feature Importance — Model B: Hour Prediction (Regression)",
        "subtitle": "Food posts only",
        "highlight": "last",
        "categories": [str(x) for x in fi_b.index.tolist()],
        "values": [float(x) for x in fi_b.values.tolist()],
    },
)
_plot_feature_importance(
    fi_c, COLORS[2],
    'Feature Importance — Model C: Location Predictor',
    'feat_importance_loc.png',
)
write_chart_spec(
    "prediction_model",
    "feat_importance_loc.png",
    {
        "chart": "barh",
        "title": "Feature Importance — Model C: Location Predictor",
        "subtitle": "Food posts with parsed location",
        "highlight": "last",
        "categories": [str(x) for x in fi_c.index.tolist()],
        "values": [float(x) for x in fi_c.values.tolist()],
    },
)

# --- Fig 4: Confusion Matrix – Model A ----------------------------------------
_cm = confusion_matrix(y_a_test, y_a_pred)
fig4, ax4 = plt.subplots(figsize=(6, 5))
fig4.patch.set_facecolor(BG)
ax4.set_facecolor(BG)
im = ax4.imshow(_cm, cmap='Blues', aspect='auto')
ax4.set_xticks([0, 1]); ax4.set_yticks([0, 1])
ax4.set_xticklabels(['Not Food Post', 'Food Post'], color=PRIMARY, fontsize=10)
ax4.set_yticklabels(['Not Food Post', 'Food Post'], color=PRIMARY, fontsize=10)
ax4.set_xlabel('Predicted', color=PRIMARY, fontsize=11)
ax4.set_ylabel('Actual', color=PRIMARY, fontsize=11)
ax4.set_title(f'Confusion Matrix — Model A\nAccuracy: {acc_a:.1%}  |  CV: {cv_a:.1%}', color=PRIMARY, fontsize=13, pad=12)
for _i in range(2):
    for _j in range(2):
        ax4.text(_j, _i, str(_cm[_i, _j]), ha='center', va='center',
                 color=PRIMARY, fontsize=14, fontweight='bold')
for spine in ax4.spines.values():
    spine.set_edgecolor('#444')
plt.tight_layout()
save_export_or_interactive(fig4, "prediction_model", "confusion_matrix_a.png", facecolor=BG)
write_chart_spec(
    "prediction_model",
    "confusion_matrix_a.png",
    {
        "chart": "confusion",
        "title": f"Confusion Matrix — Model A  (test acc: {acc_a:.1%}, 5-fold CV: {cv_a:.1%})",
        "rowLabels": ["Not Food Post", "Food Post"],
        "colLabels": ["Not Food Post", "Food Post"],
        "matrix": [[int(_cm[i, j]) for j in range(2)] for i in range(2)],
    },
)

# --- Fig 5: Predicted vs Actual Hour – Model B --------------------------------
fig5, ax5 = plt.subplots(figsize=(8, 6))
fig5.patch.set_facecolor(BG)
ax5.set_facecolor(BG)
ax5.scatter(y_b_test, y_b_pred, alpha=0.25, color=COLORS[1], s=15, label='Predictions')
ax5.plot([0, 23], [0, 23], color=GOLD, linewidth=1.5, linestyle='--', label='Perfect fit')
ax5.set_xlabel('Actual Hour', color=PRIMARY, fontsize=11)
ax5.set_ylabel('Predicted Hour', color=PRIMARY, fontsize=11)
ax5.set_title(
    f'Predicted vs Actual Hour of Food Post\nRMSE: {rmse_b:.2f}h  |  MAE: {mae_b:.2f}h  |  R²: {r2_b:.3f}',
    color=PRIMARY, fontsize=13, pad=12
)
_legend = ax5.legend(facecolor='#2a2a2e', edgecolor='#555', labelcolor=PRIMARY, fontsize=10)
ax5.tick_params(colors=PRIMARY)
for spine in ax5.spines.values():
    spine.set_edgecolor('#444')
ax5.xaxis.grid(True, linestyle='--', alpha=0.25)
ax5.yaxis.grid(True, linestyle='--', alpha=0.25)
ax5.set_axisbelow(True)
plt.tight_layout()
save_export_or_interactive(fig5, "prediction_model", "predicted_vs_actual_hour.png", facecolor=BG)
write_chart_spec(
    "prediction_model",
    "predicted_vs_actual_hour.png",
    {
        "chart": "scatter",
        "title": f"Predicted vs Actual Hour of Food Post  (RMSE: {rmse_b:.2f}h, MAE: {mae_b:.2f}h, R²: {r2_b:.3f})",
        "x": [float(x) for x in y_b_test.tolist()],
        "y": [float(x) for x in y_b_pred.tolist()],
        "xName": "Actual hour",
        "yName": "Predicted hour",
    },
)

# --- Fig 6: Average prediction probability by hour (food post) ---------------
_test_df = X_a_test.copy()
_test_df['prob'] = y_a_prob
_test_df['actual'] = y_a_test.values
_hourly_prob = _test_df.groupby('hour')['prob'].mean().reindex(range(24), fill_value=np.nan)

fig6, ax6 = plt.subplots(figsize=(11, 5))
fig6.patch.set_facecolor(BG)
ax6.set_facecolor(BG)
_hours = _hourly_prob.index.tolist()
_probs = _hourly_prob.values

_bar_colors = [GREEN if p >= 0.6 else (GOLD if p >= 0.4 else COLORS[0]) for p in _probs]
ax6.bar(_hours, _probs, color=_bar_colors, edgecolor='none', width=0.75)
ax6.axhline(0.5, color=RED, linewidth=1.2, linestyle='--', label='Decision threshold (0.5)')
ax6.set_xticks(range(24))
ax6.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right', fontsize=8, color=PRIMARY)
ax6.set_ylabel('Avg. P(Food Post)', color=PRIMARY, fontsize=11)
ax6.set_xlabel('Hour of Day', color=PRIMARY, fontsize=11)
ax6.set_title('Model A — Predicted Probability of Food Post by Hour', color=PRIMARY, fontsize=13, pad=12)
_patches = [
    mpatches.Patch(color=GREEN, label='High ≥ 0.6'),
    mpatches.Patch(color=GOLD,  label='Medium 0.4–0.6'),
    mpatches.Patch(color=COLORS[0], label='Low < 0.4'),
    mpatches.Patch(color=RED,   label='Threshold (0.5)', linestyle='--'),
]
_legend6 = ax6.legend(handles=_patches, facecolor='#2a2a2e', edgecolor='#555',
                       labelcolor=PRIMARY, fontsize=9, loc='upper left')
ax6.tick_params(colors=PRIMARY)
for spine in ax6.spines.values():
    spine.set_edgecolor('#444')
ax6.yaxis.grid(True, linestyle='--', alpha=0.25)
ax6.set_axisbelow(True)
ax6.set_ylim(0, 1)
plt.tight_layout()
save_export_or_interactive(fig6, "prediction_model", "prob_by_hour.png", facecolor=BG)
write_chart_spec(
    "prediction_model",
    "prob_by_hour.png",
    {
        "chart": "probBar",
        "title": "Model A — Avg. predicted P(food post) on held-out set, by hour",
        "categories": [f"{h:02d}:00" for h in range(24)],
        "values": [None if (isinstance(p, float) and np.isnan(p)) else float(p) for p in _probs.tolist()],
        "threshold": 0.5,
    },
)

# ─────────────────────────────────────────────────────────────────────────────
# 6.  FINAL METRICS SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("FINAL MODEL SUMMARY")
print("=" * 65)
print(f"""
  MODEL A — Food Post Classifier (Gradient Boosting)
    • Algorithm       : GradientBoostingClassifier
    • Test Accuracy   : {acc_a:.4f}  ({acc_a*100:.1f}%)
    • 5-Fold CV Acc   : {cv_a:.4f}  ({cv_a*100:.1f}%)
    • Top Feature     : {MODEL_FEATURES[np.argmax(clf.feature_importances_)]}

  MODEL B — Hour of Post Regressor (Gradient Boosting)
    • Algorithm       : GradientBoostingRegressor
    • RMSE            : {rmse_b:.3f} hours
    • MAE             : {mae_b:.3f} hours
    • R²              : {r2_b:.4f}
    • Top Feature     : {REG_FEATURES[np.argmax(reg.feature_importances_)]}

  MODEL C — Location Predictor (Gradient Boosting)
    • Algorithm       : GradientBoostingClassifier
    • Classes         : {len(_loc_enc.classes_)} top locations
    • Test Accuracy   : {acc_c:.4f}  ({acc_c*100:.1f}%)
    • 5-Fold CV Acc   : {cv_c:.4f}  ({cv_c*100:.1f}%)
    • Top Feature     : {LOC_FEATURES[np.argmax(clf_loc.feature_importances_)]}
""")

# Store models for downstream use
model_food_clf    = clf         # Model A
model_hour_reg    = reg         # Model B
model_loc_clf     = clf_loc     # Model C
loc_label_encoder = _loc_enc
sender_encoder    = _sender_le
