# Buffet Clearers Overengineered

![Hour vs day of week heatmap](docs/readme/food_patterns/03_hour_vs_day_of_week_heatmap.png)

The struggle is real. So is the data.

**This repo:**  
- Reads Telegram group food raid data  
- Overanalyzes it with Python, pandas, and unnecessarily pretty graphs  
- Tries to predict when and where food will appear, for science (and snacks)  
- Renders a gallery of charts about snacks, ice cream, and desperate students  
- Useful for data nerds and hungry undergrads



## Requirements

- Python 3.10+ recommended  
- Dependencies are listed in `requirements.txt` (pandas, numpy, matplotlib, boto3, scikit-learn).

## Data

The loader picks a chat export in this order:

1. `BUFFET_CHAT_EXPORT` — path to a JSON export file, if set  
2. `data/chat_export.json` — if present  
3. `data/result.json` — if present  
4. `data/chat_export.sample.json` — bundled sample  
5. Otherwise it tries S3 via a local metadata API (see `src/load_inspect.py`).

For a normal local run, place your export as `data/result.json` or `data/chat_export.json`, or set `BUFFET_CHAT_EXPORT`.

## How to run

From the project root:

```bash
python -m pip install -r requirements.txt
python run_graphs.py
```

Or use the wrappers (install deps + run the pipeline):

- **Windows:** `render_graphs.cmd`
- **macOS / Linux:** `chmod +x render_graphs.sh && ./render_graphs.sh`

On Windows, if you see encoding issues in the console, the scripts set `PYTHONIOENCODING=utf-8`; `run_graphs.py` also reconfigures stdout/stderr to UTF-8 when possible.

Outputs are written under `out/`, grouped by category. A manifest of generated PNGs is saved as `out/manifest.json`.

## Output gallery

### Food patterns

![Food alerts by day of week](docs/readme/food_patterns/01_food_alerts_by_day_of_week.png)

![Food alerts week of year heatmap](docs/readme/food_patterns/02_food_alerts_week_of_year_heatmap.png)

![Hour vs day of week heatmap](docs/readme/food_patterns/03_hour_vs_day_of_week_heatmap.png)

![Monthly food alert trend](docs/readme/food_patterns/04_monthly_food_alert_trend.png)

![Top food alert senders](docs/readme/food_patterns/05_top_food_alert_senders.png)

### Weekly alerts

![Food alerts by week, colored by month](docs/readme/weekly_alerts/food_alerts_by_week_year_colored_by_month.png)

### Prediction model

![Confusion matrix (classifier)](docs/readme/prediction_model/confusion_matrix_a.png)

![Feature importance — classifier](docs/readme/prediction_model/feat_importance_clf.png)

![Feature importance — location](docs/readme/prediction_model/feat_importance_loc.png)

![Feature importance — regression](docs/readme/prediction_model/feat_importance_reg.png)

![Predicted vs actual hour](docs/readme/prediction_model/predicted_vs_actual_hour.png)

![Probability by hour](docs/readme/prediction_model/prob_by_hour.png)

### Clustering

![K selection](docs/readme/clustering/01_k_selection.png)

Explanation: This chart compares silhouette scores for different `K` values. The script now prefers the smallest `K` that is close to the best score, so it does not split one real pattern into two nearly identical clusters.

Conclusion: The clustering now chooses a simpler and more readable solution, which avoids the old problem where two clusters looked almost the same.

![Cluster summary table](docs/readme/clustering/02_cluster_summary_table.png)

Explanation: This table gives the main result directly: cluster names, share of posts, peak hours, strongest days, weekend share, and strongest months.

Conclusion: The output is now easier to interpret because the clusters are described as real timing patterns instead of just `Cluster 0`, `Cluster 1`, and `Cluster 2`.

![Cluster hour profiles](docs/readme/clustering/03_hour_profiles.png)

Explanation: This line chart shows the hourly shape of each cluster as a percentage of that cluster.

Conclusion: One cluster is clearly lunch-centered, while the others are evening-centered. This is a more meaningful split than the previous version.

![Cluster day profiles](docs/readme/clustering/04_day_profiles.png)

Explanation: This grouped bar chart compares which days of the week each cluster is strongest on.

Conclusion: The clustering is now intentionally simplified into a lunch-centered pattern and one combined evening pattern.

![Cluster heatmaps](docs/readme/clustering/05_hour_day_heatmaps.png)

Explanation: These small heatmaps show the full shape of each cluster across both hour and day of week.

Conclusion: The two cluster shapes are now visually distinct: lunch / early afternoon and evening.

![Cluster month profiles](docs/readme/clustering/06_month_profiles.png)

Explanation: This chart compares the monthly makeup of each cluster. Month is now used only for explanation, not to create the clusters.

Conclusion: Seasonal differences still exist, but they are treated as explanation instead of forcing the model to produce duplicate-looking clusters.

---

After you run the pipeline, `out/manifest.json` lists every PNG path under `out/` for that run, and `docs/readme/` is refreshed to match.
