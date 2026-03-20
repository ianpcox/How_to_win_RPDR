# Chasing More Data: Years Doing Drag, Social Media, Race/Ethnicity

We want **years doing drag**, **social media following** (e.g. Plastique Tiara’s massive following), **race and ethnicity**, and other rich contestant attributes. Below are the sources we’ve identified and how to use them.

---

**Age** is already in our pipeline (dragracer/csvbase, at time of filming). It can also be found in the Wikipedia contestant tables: [List of Drag Race contestants](https://en.wikipedia.org/wiki/List_of_Drag_Race_contestants) (franchise) and [List of RuPaul's Drag Race contestants](https://en.wikipedia.org/wiki/List_of_RuPaul%27s_Drag_Race_contestants) (US). Those tables include Age, Hometown, and Outcome and are useful for cross-checking or backfilling.

## 1. Years doing drag (experience)

- **Not in** csvbase, Rdatasets dragracer, or tashapiro contestant CSV.
- **Where it appears:** Individual contestant pages on the **RuPaul’s Drag Race Fandom Wiki** often state “Started drag in 20XX” or “Years active.” Same for some Wikipedia contestant articles.
- **How to get it:**
  - **Scrape:** Fandom wiki contestant list → per-queen page → parse infobox or first paragraph for “started drag” / “years active.” (Respect robots.txt and rate limits.)
  - **Manual:** Build a small CSV `contestant_years_drag.csv` with columns `contestant`, `year_started_drag` (or `years_doing_drag_at_filming`) and merge by contestant name.
- **Use:** Compute `years_doing_drag = season_filming_year - year_started_drag` (or use as-is if you have “years at filming”). Good predictor for experience vs. outcome.

---

## 2. Social media following (Instagram, Twitter, etc.)

- **Not in** dragracer or tashapiro contestant.csv.
- **Structured sources:**
  - **RuPaul-Predict-a-Looza (Data for Progress):**  
    - **all_contestants:** Instagram handle, Twitter handle (and age, hometown).  
    - **all_social_media:** Follower counts / social metrics for seasons 4–10 and season 11 (with some gaps).  
    - **URL:** [Data Tables – Google Sheets](https://docs.google.com/spreadsheets/d/1Sotvl3o7J_ckKUg5sRiZTqNQn3hPqhepBSeOpMTK15Q/edit). Export per sheet as CSV (File → Download → CSV). Sheet names: e.g. `all_contestants`, `all_social_media`.  
    - **Note:** Direct CSV export by URL may require the sheet to be “Anyone with link” and can return 500 in some environments; manual download is reliable.
  - **Instagram followers – fan-maintained Google Sheets:**
    - Historical (e.g. June 2017): [RPDR Contestant Instagram Followers](https://docs.google.com/spreadsheets/d/1LP4NikaaS3wjGuG4RzeegWNvLAAkMm--34V7ufLtmbY/edit).  
    - Current rankings: [Most followed Queens on Instagram](https://docs.google.com/spreadsheets/d/1ot8NdinlKs7NC7ERXBRiSkwJNAn7oWTyB3y1Rtnn2MM/edit).  
    - Export as CSV and add to the repo (e.g. `data/instagram_followers.csv`) with columns such as `contestant`, `season`, `instagram_handle`, `followers`, `as_of_date`.
- **Live/current counts:** Use Instagram (or Twitter) API / scraping with their terms of service in mind; or use a third-party “influencer” dataset that includes RPDR queens. Not included in this repo by default.
- **Use:** Merge by contestant (and season if needed). Strong candidate for “pre-existing fame” or “fan base” as a predictor of placement or win (e.g. Plastique Tiara’s large following).

---

## 3. Race and ethnicity

- **Not in** dragracer, csvbase, or tashapiro contestant CSV as explicit columns.  
- **Partial proxy in tashapiro:** `contestant.csv` has **real_name**, **hometown**, **location** (e.g. “Ho Chi Minh City, Vietnam” for Plastique Tiara). You can use birthplace/hometown as a **geographic/cultural proxy** (e.g. Vietnam, Puerto Rico, UK), but that is **not** the same as self-identified race or ethnicity.
- **Where it might appear:**  
  - **Fandom wiki:** Some contestant pages mention ethnicity or background in the bio.  
  - **Wikipedia:** Some contestant articles mention ethnicity in the text; the main list table does not have a race/ethnicity column.  
  - **No canonical dataset** of self-identified race/ethnicity for all RPDR US contestants is known to us.
- **How to get it:**
  - **Manual coding:** Create `contestant_demographics.csv` with `contestant`, `race_or_ethnicity` (or multiple columns if you distinguish), using wiki/Wikipedia/articles. Document coding rules and any missing data.
  - **Scrape:** Parse Fandom/Wikipedia bios for keywords (high risk of inconsistency and missing data; prefer manual for small cohorts).
- **Ethics:** Treat as sensitive. Use for descriptive or equity-oriented analysis only; document source and coding; avoid reductive categories.

---

## 4. tashapiro/drag-race (contestant table) – already integrated

- **URL:** [contestant.csv](https://raw.githubusercontent.com/tashapiro/drag-race/main/data/contestant.csv) (US + other franchises; filter `original_season_id` for US main series if needed).
- **Fields:** `id`, `name` (drag name), `original_season_id`, `real_name`, `dob`, `gender`, `hometown`, `location`.
- **Gives us:** **real_name**, **gender**, **location** (current), **hometown** (sometimes more specific than dragracer). Useful for name matching and for inferring geographic/cultural context (e.g. birthplace as rough proxy for ethnicity, with caveats above).
- **Integration:** The pipeline can load this and merge by contestant **name** into the canonical contestant table so that merged episode-contestant rows gain `real_name`, `gender`, `location`, `tashapiro_hometown`.

---

## 5. Summary: what we have vs. what we chase

| Variable              | In current pipeline | How to get it |
|-----------------------|---------------------|----------------|
| Age, DOB, hometown   | Yes (dragracer)     | —              |
| Main/mini outcomes   | Yes (contep)        | —              |
| real_name, gender, location | Optional (tashapiro) | Load `contestant.csv`; merge by name. |
| Years doing drag     | No                  | Fandom wiki scrape or manual CSV. |
| Social media (handles, followers) | No | Predict-a-Looza or Instagram sheets → CSV; merge by contestant. |
| Race/ethnicity       | No                  | Manual coding or wiki/Wikipedia scrape; document and treat as sensitive. |

---

## 6. File layout for expanded data (optional)

- `data/contestant_years_drag.csv` – columns: `contestant`, `year_started_drag` (or `years_doing_drag_at_filming`).
- `data/instagram_followers.csv` – columns: `contestant`, `season` (optional), `instagram_handle`, `followers`, `as_of_date`.
- `data/contestant_demographics.csv` – columns: `contestant`, `race_or_ethnicity` (or your chosen schema); document coding.
- Load these in `data_loader.py` (or a separate `load_expanded_contestant_data()`), merge by `contestant` (and `season` where needed), and attach to the merged episode-contestant table for analysis and modeling.
