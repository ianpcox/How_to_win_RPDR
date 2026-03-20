# Data Sheet – How to Win RPDR

## Data sources (two sources, reconciled in pipeline)

The pipeline fetches **contestant-level** data from two sources and **episode-contestant outcomes** from one; it reconciles the contestant tables and merges with episode data.

### Source 1: Contestant-level – csvbase

- **URL:** [csvbase – rpdr-contestants](https://csvbase.com/rmirror/rpdr-contestants) → `https://csvbase.com/rmirror/rpdr-contestants.csv`
- **Fields:** `season`, `contestant`, `age`, `dob`, `hometown`. 184 rows.
- **Attribution:** Public table data; not affiliated with the show. Education/analysis only.

### Source 2: Contestant-level + episode-level – Rdatasets (dragracer)

- **URLs (GitHub raw):**
  - Contestants: `https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/dragracer/rpdr_contestants.csv`
  - Episode-contestant: `https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/dragracer/rpdr_contep.csv`
- **Origin:** R package [dragracer](https://cran.r-project.org/web/packages/dragracer/) (CRAN); Rdatasets provides CSV mirrors.
- **rpdr_contestants:** `rownames`, `season`, `contestant`, `age`, `dob`, `hometown`. 184 rows.
- **rpdr_contep:** `season`, `rank`, `missc`, `contestant`, `episode`, `outcome`, `eliminated`, `participant`, `minichalw`, `finale`, `penultimate`. One row per contestant per episode; `outcome` = WIN, HIGH, SAFE, LOW, BTM, etc.; `eliminated` = 0/1.

### Reconciliation (contestant-level)

- **Match key:** `(season, contestant)`.
- **Result:** All 184 contestants match between csvbase and Rdatasets (same seasons and names). No rows only-in-one-source; age/dob/hometown can be compared if needed.
- **Canonical contestant table:** Pipeline uses Rdatasets contestants as canonical (same source as episode data) and merges contep into it for one joined episode-contestant table with contestant attributes.

### Source 3 (optional): tashapiro/drag-race contestant

- **URL:** [contestant.csv](https://raw.githubusercontent.com/tashapiro/drag-race/main/data/contestant.csv) (US and other franchises; pipeline filters to US main series F10*).
- **Fields:** `name` (drag name), `real_name`, `dob`, `gender`, `hometown`, `location`. No explicit race/ethnicity or years doing drag.
- **Use:** Merged by contestant name into the canonical contestant table so that episode-contestant rows can include **real_name**, **gender**, **location**, **tashapiro_hometown** (useful for geographic/cultural context; birthplace can be a rough proxy for ethnicity only if documented and used carefully).

### Optional / reference

- **Wikipedia contestant tables:** [List of Drag Race contestants](https://en.wikipedia.org/wiki/List_of_Drag_Race_contestants) (franchise-wide) and [List of RuPaul's Drag Race contestants](https://en.wikipedia.org/wiki/List_of_RuPaul%27s_Drag_Race_contestants) (US main series) include **Age**, **Hometown**, and **Outcome** in their tables. Age is stated *at time of filming*. Use as a reference to cross-check or backfill age (and hometown/outcome) if needed; the pipeline currently uses age from dragracer/csvbase.
- **RuPaulsDataRace/Rupository (GitHub):** [RPDR_raw.txt](https://github.com/RuPaulsDataRace/Rupository/blob/master/RPDR_raw.txt) has episode outcomes by row but no contestant names; useful for outcome coding (e.g. BTM2 vs BTM) and narrative validation. Pipeline does not ingest it; outcome codes in contep may differ (e.g. BTM vs BTM2).

### Local staged data (data/ folder)

Three files are housed in **data/** and loaded into the pipeline when present:

1. **Most followed Queens on Instagram - Week 23.csv** – RPDR block: Rank, Queen, Followers, Season. Parsed to (contestant, followers_week23, season). Merged by **contestant name** into the central contestant table (followers_week23 attached to every (season, contestant) match for that queen).
2. **RPDR Contestant Instagram Followers as of June 2017 - Sheet1.csv** – Wide grid: SEASON 1–9 columns with (contestant, followers) pairs. Unpivoted to (season, contestant, followers_june2017). Merged by **(season, contestant)**; season normalized to S01–S09.
3. **RuPaul-Predict-A-Looza — Data Tables - table_metadata.csv** – Schema reference only (all_episodes, all_contestants, all_rankings, all_social_media, survey_*). Not merged; describes Predict-a-Looza tables for when actual data tables are added.

**Staging:** Parsed Instagram tables are written to **data/staged/** as `instagram_week23.csv` and `instagram_june2017.csv` (normalized columns, no Dragula rows). The central DB is the existing reconciled contestant + episode–contestant dataset with **followers_week23** and **followers_june2017** added at contestant level and carried through to the merged episode–contestant table.

### Expanded data (years doing drag, social media, race/ethnicity)

- **Years doing drag:** Not in any of the above. Sourced from Fandom wiki (“started drag in …”) or manual CSV. See [DATA_EXPANSION_SOURCES.md](./DATA_EXPANSION_SOURCES.md).
- **Social media (Instagram/Twitter followers):** Staged from **data/** (Week 23 and June 2017 Instagram CSVs) and merged into the central DB. RuPaul-Predict-a-Looza (all_contestants, all_social_media) can be added when tables are exported; schema in table_metadata. See DATA_EXPANSION_SOURCES.md.
- **Race and ethnicity:** Not in structured datasets. Possible from manual coding or Fandom/Wikipedia; document coding and treat as sensitive. See DATA_EXPANSION_SOURCES.md.

## Splits

- **Temporal:** By season. For prediction, use earlier seasons as train and later seasons as test (or leave-one-season-out).
- **Train/val/test:** e.g. seasons 1–12 train, 13 val, 14 test; or single holdout season.

## Mini-challenge and main-challenge (maxi) wins

- **Main-challenge (maxi) outcome:** In **rpdr_contep**, the `outcome` column is the **main challenge** result: WIN, HIGH, SAFE, LOW, BTM (and special codes below). So we **do have** main-challenge wins and placements (WIN = maxi win).
- **Mini-challenge:** **rpdr_contep** has a **minichalw** column (0/1) indicating whether the queen won the mini-challenge that episode. The dragracer package notes this is a *work in progress* and suggests using **rpdr_ep** for richer mini-challenge data if needed. **rpdr_ep** (episode-level, not yet in our pipeline) has `minic`, `minicw1`, `minicw2`, … for mini-challenge description and winner(s). So we **do have** mini-challenge wins in the current data (minichalw); for multiple mini winners or episode-level analysis, adding rpdr_ep is the next step.

## Ties and no-elimination episodes

- **Definition:** A **no-elimination episode** is one where no one is eliminated that episode (e.g. double save, or non-elimination format). In the data, that corresponds to **zero** rows with `eliminated == 1` for that (season, episode). A **double elimination** is two rows with `eliminated == 1` for the same (season, episode). A **double save** (no one goes home) is coded as outcome **SAVE** (1 row in our run) and no one has `eliminated == 1` that episode.
- **Handling in analysis:**
  - **No-elimination:** When counting “eliminations” or “LSFYL survival,” exclude that episode from the denominator for “episodes where someone was eliminated,” or flag the episode and treat it as censored for time-to-elimination. Do **not** treat SAVE/RTRN as an elimination.
  - **Double elimination:** Count as two eliminations; both contestants have `eliminated == 1`. Episode-level summaries should count 2 for that episode.
  - **Ties:** Outcome codes **TOP2**, **TOP 4** indicate shared placement (e.g. top 2 lip-sync for the win). **WIN** is usually one per episode; if a season had a tie for win, the dataset might code it as two WINs or as TOP2—check by (season, episode). For modeling, pre-specify: e.g. “TOP2 counts as WIN for both” or “separate category.”
- **Special outcome codes (contep):** RTRN = return; OUT = out (e.g. quit/injury); DISQ = disqualified; WDR = withdraw; SAVE = double save; STAY = stayed (no elimination); Guest, Miss C, Runner-up, Winner, Eliminated = finale/guest. Use these to filter or to define “in competition” vs “already out/guest” when building episode-level features.

## Public opinion and viewer support

- **Not in the current data.** The dragracer and csvbase sources do **not** include fan votes, social sentiment, or viewer support scores. To study public opinion or “fan favorite” effects you would need to bring in **external data** (e.g. social mentions, Reddit/forum polls, post-season fan surveys) and merge by season/contestant. Document as a **limitation** for “what predicts winning” if the show’s outcome is partly influenced by fan or production choices not in our dataset.

## Drama, pit stop, and narrative events

- **Not in the data.** Incidents like the “Sugar Daddy” fight (Mimi Imfurst vs Shangela) or other pit-stop/Untucked drama are **qualitative narrative** and are not coded in rpdr_contep or rpdr_ep. The dataset has no variable for “drama,” “conflict,” or story-arc intensity. Analyzing such effects would require either (1) **manual coding** (e.g. episode-level “high drama” 0/1 from recaps or transcripts) or (2) **text/sentiment** from episode summaries or fan wikis, then merged by (season, episode). Document as **out of scope** for the current pipeline and as a possible extension.

## Limitations

- Demographics: age and hometown only.
- Fan-maintained; may lag newest seasons. US main series only unless noted.
- Episode outcomes in contep include special codes (Guest, Runner-up, DISQ, etc.); filter to WIN/HIGH/SAFE/LOW/BTM for core challenge outcomes.
- No public opinion, viewer support, or drama/pit-stop variables; add external or hand-coded data if needed.
