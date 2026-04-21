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

---

After you run the pipeline, `out/manifest.json` lists every PNG path under `out/` for that run, and `docs/readme/` is refreshed to match.
