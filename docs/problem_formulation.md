# Problem Formulation – How to Win RPDR

## Research / business question

**What contestant or season factors predict success on RuPaul's Drag Race?** Success is defined as (a) reaching the finale, or (b) winning the season. The project addresses both **exploratory analysis** (what the data shows about placement, wins, and eliminations) and **predictive modeling** (e.g. predicting top-3 or winner from early-season or contestant-level features).

Secondary questions (examples): Do first-episode or early-episode outcomes predict season outcome? Does Snatch Game (or other challenge-type) performance correlate with making the finale? Do judges’ choices reveal consistent preferences (e.g. for certain challenge types or contestant profiles)? Does pre-show visibility (e.g. Instagram followers) correlate with advancement after controlling for in-show performance?

**Research angle:** We are *not* replicating the survival-analysis design (e.g. Hanna 2013, Cox time-to-elimination). Instead we are open to (a) **behavioral / decision-making**: e.g. revealed preferences of judges, recency/primacy effects, or the role of popularity vs merit; (b) **interpretable prediction**: classification or regression for finale/winner from contestant and episode-level features; or (c) **straightforward EDA**: what correlates with winning, with clear documentation and simple models. See docs/report.md for alternative directions.

## Primary success metric and threshold

- **EDA:** Reproducible summary statistics and visualizations (by season, placement, age, etc.); clear documentation of data source and limitations.
- **Prediction (if pursued):** Classification accuracy or rank correlation for predicting finale placement or winner; baseline = majority class or simple rule (e.g. "first-episode win"). Target: interpretable model that beats baseline.
- **Reproducibility:** Single entry point (`run.py`) that loads data, runs EDA and/or model, and reports metrics.

## Stakeholders and decisions

- **Audience:** Fans, content creators, and portfolio reviewers. Output informs narrative analyses ("what predicts winning") and demonstrates data science workflow (formulation, data, pipeline, reporting).
- **Decisions:** No business decision; project is for portfolio and curiosity-driven analysis. Ethics: use only public, fan-sourced or official-published data; no private or defamatory use.
