# How to Win RuPaul's Drag Race: A Competitive Strategy Analysis

This repository transforms a basic data ingestion script into a **sophisticated competitive strategy analysis platform** for RuPaul's Drag Race (Seasons 1–14).

By analyzing 184 contestant-season records, this project uses machine learning and statistical modeling to uncover the mathematical blueprint for reaching the finale and winning the crown.

## Project Structure

* `rpdr_pipeline.py` — The core reproducible analytics pipeline. Handles feature engineering, K-Means clustering, Logistic Regression modeling, and generates 11 static charts plus an interactive dashboard.
* `docs/report.md` — A comprehensive paper-style report detailing the methodology, the "Lipsync Curse", and the performance archetypes.
* `docs/dashboard.html` — An **interactive Plotly executive dashboard** exploring the data.
* `docs/assets/` — 11 generated static charts supporting the report.
* `data/staged/` — The raw and staged datasets used for analysis.

## Key Findings

1. **The Mathematical Threshold:** Queens with 0 or 1 main challenge wins rarely make the finale. Securing 2 wins pushes the finale probability above 50%, and 3 wins historically guarantees a spot.
2. **The "Lipsync Curse" is Real:** Queens with 0 lip syncs have the highest finale rate. Hitting 2 lip syncs drops the finale probability to under 15%, and 3 lip syncs ("lip sync assassins") almost never make it.
3. **Performance Archetypes:** K-Means clustering identifies four distinct paths through the competition: *Challenge Dominators* (~95% finale rate), *Consistent Performers* (~60%), *Safe Players* (~10%), and *Bottom Feeders* (0%).
4. **Predictive Modeling:** A Logistic Regression model predicts finale appearances with an 87% ROC-AUC score, proving that despite reality TV producing, the tournament structure enforces a rigid mathematical reality.

Read the full analysis in [docs/report.md](docs/report.md) or open `docs/dashboard.html` in your browser to explore the data interactively.

## How to Run the Pipeline

Install the dependencies:
```bash
pip install pandas numpy matplotlib seaborn scikit-learn plotly
```

Run the pipeline:
```bash
python rpdr_pipeline.py
```
This will process the data, train the models, and regenerate all charts and the dashboard.
