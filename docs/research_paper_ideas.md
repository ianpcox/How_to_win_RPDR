# Research paper ideas from How to Win RPDR

Based on the current features (performance: wins, highs, lows, lipsyncs; contestant: age; optional: Instagram followers) and findings (wins and lipsyncs dominate; age negligible; followers correlate with finale when available), below are concrete paper directions that could be proposed.

---

## 1. Popularity vs merit in reality competition

**Title (draft):** *Does pre-show visibility predict advancement? Evidence from Instagram and placement on RuPaul's Drag Race.*

**Question:** After controlling for in-show performance (main-challenge wins, highs, lows, lipsyncs), does pre-show social following (Instagram) predict making the finale or final rank?

**Data we have:** Contestant-season table with `made_finale`, `n_wins`, `n_highs`, `n_lows`, `n_lipsyncs`, `followers_june2017`, `followers_week23` (partial coverage).  
**Methods:** Logistic regression (made_finale ~ wins + highs + lows + lipsyncs + log(followers)); report coefficient on followers and incremental fit.  
**Angle:** Behavioral / media: "merit" (judged performance) vs "popularity" (audience/social capital).  
**Outlets:** Media and communication; entertainment industry / strategic management; applied economics of culture.

**Gap:** Broader follower coverage (e.g. at time of season airing) would strengthen; document limitation.

---

## 2. Revealed preferences of judges

**Title (draft):** *What do reality competition judges consistently reward? Revealed preferences from RuPaul's Drag Race outcomes.*

**Question:** Which performance profiles (e.g. "consistent highs," "few wins but no bottoms," "one big win then safe") are associated with advancement? Can we describe judge behavior as a stable function of WIN/HIGH/SAFE/LOW/BTM history?

**Data we have:** Episode-contestant outcomes; contestant-season aggregates (total_top, total_bottom, wins_per_episode, etc.).  
**Methods:** Describe outcome distributions by trajectory type; multinomial or ordinal model of placement given cumulative performance; or simple rules (e.g. "≥2 wins and ≤1 lipsync → high probability finale").  
**Angle:** Judgment and decision-making; expert evaluation under repeated observation.  
**Outlets:** Judgment and Decision Making; organizational behavior; media studies.

**Gap:** Challenge-type (Snatch Game, ball, etc.) would allow "reward for specific skills"; could be added from episode-level metadata if available.

---

## 3. Recency and momentum in sequential elimination

**Title (draft):** *Does last week predict this week? Recency and momentum in an elimination competition.*

**Question:** Does the previous episode’s outcome (WIN, HIGH, SAFE, LOW, BTM) predict the current episode’s outcome or elimination risk? Is there "momentum" (win → more likely win next) or "bounce back" (low → more likely safe next)?

**Data we have:** Merged episode-contestant rows with `outcome` and `eliminated` by (season, contestant, episode).  
**Methods:** Transition matrix (outcome_t → outcome_t+1); logistic regression of elimination or "bottom two" on lagged outcome and cumulative wins/lipsyncs.  
**Angle:** Behavioral / psychology of competition; sequential decision-making.  
**Outlets:** Psychology of Sport; judgment and decision-making; applied statistics.

**Gap:** None for basic transitions; causal interpretation (production vs contestant effort) would need careful framing.

---

## 4. Forecasting success from early-season performance

**Title (draft):** *How early can we predict the finale? Forecasting success from first-k episodes of RuPaul's Drag Race.*

**Question:** Using only information available after the first 2–4 episodes (cumulative wins, highs, lows, lipsyncs; contestant age; optional followers), how well can we predict who makes the finale or wins? How does accuracy improve with more episodes?

**Data we have:** Episode-level and contestant-season aggregates; we can build "features at episode k" by truncating episode-contestant history.  
**Methods:** Train logistic regression (or simple classifier) on "features up to episode k" → made_finale; report accuracy, AUC, or rank correlation; compare to baselines (e.g. "first-episode win," majority class). Leave-one-season-out or hold out later seasons for validation.  
**Angle:** Forecasting; applied ML; fan engagement / prediction markets.  
**Outlets:** Applied ML / forecasting workshops; entertainment analytics; sports analytics–adjacent.

**Gap:** None for core analysis; adding challenge-type or narrative features could extend.

---

## 5. Demographics and advancement (observational)

**Title (draft):** *Observational correlates of advancement: age, performance, and placement on RuPaul's Drag Race.*

**Question:** In our data, does age (or, if added: body size, race/ethnicity, hometown region) predict placement after controlling for performance? We already find age has negligible correlation; the paper would formalize this and add any expanded demographics with clear caveats.

**Data we have:** Age; performance features; made_finale. Optional: plus-size, race/ethnicity, region from DATA_EXPANSION_SOURCES if coded.  
**Methods:** Regression of placement or made_finale on performance + demographics; report coefficients and note limitations (observational; no causal claim; possible selection and measurement issues).  
**Angle:** Inequality / representation; descriptive evidence for public discussion.  
**Outlets:** Sociology of culture; gender/media studies; short report or note.

**Gap:** Plus-size and race/ethnicity require careful, documented coding and ethical framing; age-only paper is feasible now.

---

## 6. What matters most? Feature importance and interpretability

**Title (draft):** *What predicts making the finale? A feature-importance view of RuPaul's Drag Race.*

**Question:** Which measurable factors (wins, highs, lows, lipsyncs, age, followers) are most associated with making the finale? How robust is the ranking to different metrics (correlation, logistic coefficients, simple rules)?

**Data we have:** Full contestant-season table with engineered features; correlation-based importance already computed.  
**Methods:** Present correlation ranking (as in current pipeline); add logistic regression and compare standardized coefficients or marginal effects; optionally compare to a simple rule (e.g. "≥2 wins and ≤2 lipsyncs"). Discuss interpretability and redundancy (e.g. n_wins vs wins_per_episode).  
**Angle:** Applied data science; interpretable prediction; reproducible analysis.  
**Outlets:** Data science / analytics blog or short paper; reproducibility-focused venue; teaching case study.

**Gap:** None; this is the most directly aligned with the current pipeline.

---

## Summary

| Idea | Main feature(s) | Data readiness | Best fit |
|------|-----------------|----------------|----------|
| 1. Popularity vs merit | Instagram, performance | Partial (followers for subset) | Media / behavioral |
| 2. Revealed preferences | WIN/HIGH/LOW/BTM trajectories | Ready | Judgment / media |
| 3. Recency / momentum | Episode sequence | Ready | Psychology / stats |
| 4. Early-season forecasting | Performance by episode k | Ready | ML / forecasting |
| 5. Demographics | Age; optional plus-size/race | Age ready; others need coding | Sociology / descriptive |
| 6. Feature importance | All engineered features | Ready | Data science / teaching |

Recommendation: **4** (forecasting) or **6** (feature importance) are the quickest to turn into a short paper or report with the current codebase. **1** (popularity vs merit) is a strong behavioral/media angle if you emphasize the followers analysis and its limitations. **2** and **3** need a bit more modeling but use data we already have.
