"""
Build contestant-season analysis table and run simple analyses.
One row per (season, contestant) with: age, made_finale, winner, n_wins, n_highs, n_lows, n_lipsyncs, n_episodes, Instagram (if present).
Feature engineering: rates, totals, season_num, log followers; importance via correlation with made_finale.
"""
from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from pathlib import Path

from data_loader import DATA_DIR_DEFAULT, _key


def build_contestant_season_table(merged: list[dict]) -> list[dict]:
    """
    From merged episode-contestant rows, build one row per (season, contestant) with:
    season, contestant, age, made_finale, winner, n_wins, n_highs, n_lows, n_lipsyncs, n_episodes,
    followers_week23, followers_june2017 (if present).
    """
    # Aggregate by (season, contestant)
    agg: dict[tuple[str, str], dict] = defaultdict(lambda: {
        "n_wins": 0, "n_highs": 0, "n_lows": 0, "n_lipsyncs": 0, "n_episodes": 0,
        "eliminated": 0, "outcomes": [],
    })
    for row in merged:
        s = (row.get("season") or "").strip()
        c = (row.get("contestant") or "").strip()
        if not s or not c:
            continue
        k = (s, c)
        o = agg[k]
        o["n_episodes"] += 1
        out = (row.get("outcome") or "").strip()
        if out == "WIN":
            o["n_wins"] += 1
        elif out == "HIGH":
            o["n_highs"] += 1
        elif out == "LOW":
            o["n_lows"] += 1
        elif out == "BTM":
            o["n_lipsyncs"] += 1
        if (row.get("eliminated") or "").strip() == "1":
            o["eliminated"] = 1
        if out:
            o["outcomes"].append(out)

        # Carry contestant-level fields from any row (same for all episodes)
        if "age" not in o:
            o["age"] = (row.get("age") or row.get("contestant_age") or "").strip()
        if "hometown" not in o:
            o["hometown"] = (row.get("hometown") or row.get("contestant_hometown") or "").strip()
        if "location" not in o:
            o["location"] = (row.get("location") or row.get("contestant_location") or "").strip()
        if "followers_week23" not in o and (row.get("followers_week23") or row.get("contestant_followers_week23")) is not None:
            o["followers_week23"] = row.get("followers_week23") or row.get("contestant_followers_week23")
        if "followers_june2017" not in o and (row.get("followers_june2017") or row.get("contestant_followers_june2017")) is not None:
            o["followers_june2017"] = row.get("followers_june2017") or row.get("contestant_followers_june2017")

    out_rows = []
    for (s, c), o in sorted(agg.items()):
        outcomes = o["outcomes"]
        made_finale = (
            "Winner" in outcomes or "Runner-up" in outcomes or "Eliminated" in outcomes
            or o["eliminated"] == 0
        )
        winner = 1 if "Winner" in outcomes else 0
        row = {
            "season": s,
            "contestant": c,
            "age": o.get("age", ""),
            "hometown": o.get("hometown", ""),
            "location": o.get("location", ""),
            "made_finale": 1 if made_finale else 0,
            "winner": winner,
            "n_wins": o["n_wins"],
            "n_highs": o["n_highs"],
            "n_lows": o["n_lows"],
            "n_lipsyncs": o["n_lipsyncs"],
            "n_episodes": o["n_episodes"],
        }
        if o.get("followers_week23") is not None:
            row["followers_week23"] = o["followers_week23"]
        if o.get("followers_june2017") is not None:
            row["followers_june2017"] = o["followers_june2017"]
        out_rows.append(row)
    return out_rows


def _to_float(x, default: float | None = None) -> float | None:
    """Convert age or other numeric field to float; return default on failure."""
    if x is None or x == "":
        return default
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).strip())
    except (ValueError, TypeError):
        return default


def engineer_features(table: list[dict]) -> list[dict]:
    """
    Add derived features for importance analysis. Modifies rows in place and returns table.
    - season_num: 1 for S01, 2 for S02, etc.
    - *_per_episode: n_wins / n_episodes (and n_highs, n_lows, n_lipsyncs); 0 if n_episodes==0.
    - total_top: n_wins + n_highs; total_bottom: n_lows + n_lipsyncs.
    - had_any_win, had_any_lipsync: 1 if count > 0 else 0.
    - log_followers_*: log(1 + x) when followers present.
    """
    for r in table:
        s = (r.get("season") or "").strip()
        m = re.match(r"S?(\d+)$", s, re.IGNORECASE) if s else None
        r["season_num"] = int(m.group(1)) if m else None

        n_ep = r.get("n_episodes") or 0
        if not isinstance(n_ep, (int, float)):
            n_ep = _to_float(n_ep, 0) or 0
        n_ep = max(1, int(n_ep))  # avoid div by zero

        for key in ("n_wins", "n_highs", "n_lows", "n_lipsyncs"):
            val = r.get(key, 0)
            if not isinstance(val, (int, float)):
                val = _to_float(val, 0) or 0
            r[key] = int(val)
            # e.g. n_wins -> wins_per_episode
            short = key.replace("n_", "", 1) if key.startswith("n_") else key
            r[f"{short}_per_episode"] = round(val / n_ep, 4) if n_ep else 0.0

        r["total_top"] = r["n_wins"] + r["n_highs"]
        r["total_bottom"] = r["n_lows"] + r["n_lipsyncs"]
        r["had_any_win"] = 1 if r["n_wins"] > 0 else 0
        r["had_any_lipsync"] = 1 if r["n_lipsyncs"] > 0 else 0

        age = _to_float(r.get("age"))
        r["age_num"] = age if age is not None else None

        for fkey, logkey in (("followers_week23", "log_followers_week23"), ("followers_june2017", "log_followers_june2017")):
            val = r.get(fkey)
            if val is not None and isinstance(val, (int, float)) and val >= 0:
                r[logkey] = round(math.log1p(val), 4)
            elif val is not None:
                v = _to_float(val)
                if v is not None and v >= 0:
                    r[logkey] = round(math.log1p(v), 4)

        # Geographic: parse hometown "City, State" or "City, Country"
        ht = (r.get("hometown") or r.get("location") or "").strip()
        if ht and "," in ht:
            state_or_country = ht.rsplit(",", 1)[-1].strip()
        else:
            state_or_country = ""
        r["state_or_country"] = state_or_country
        state_norm = state_or_country.lower() if state_or_country else ""
        r["is_Puerto_Rico"] = 1 if "puerto rico" in state_norm else 0
        r["is_California"] = 1 if state_norm == "california" else 0
        r["is_New_York"] = 1 if "new york" in state_norm else 0
        r["is_Florida"] = 1 if state_norm == "florida" else 0
        r["is_Texas"] = 1 if state_norm == "texas" else 0
        r["is_Georgia"] = 1 if state_norm == "georgia" else 0
        r["is_Illinois"] = 1 if state_norm == "illinois" else 0
        # International: state/country not in US states + Puerto Rico
        _us_pr = frozenset((
            "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
            "delaware", "florida", "georgia", "hawaii", "illinois", "indiana", "iowa", "kansas",
            "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota",
            "mississippi", "missouri", "montana", "nevada", "new hampshire", "new jersey",
            "new mexico", "new york", "north carolina", "north dakota", "ohio", "oklahoma",
            "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota",
            "tennessee", "texas", "utah", "vermont", "virginia", "washington", "west virginia",
            "wisconsin", "wyoming", "district of columbia", "puerto rico"
        ))
        r["is_international"] = 1 if (state_norm and state_norm not in _us_pr) else 0

    return table


# Features to use for importance (numeric only; target excluded)
IMPORTANCE_FEATURES = [
    "age_num", "season_num",
    "n_wins", "n_highs", "n_lows", "n_lipsyncs", "n_episodes",
    "wins_per_episode", "highs_per_episode", "lows_per_episode", "lipsyncs_per_episode",
    "total_top", "total_bottom", "had_any_win", "had_any_lipsync",
    "followers_week23", "followers_june2017", "log_followers_week23", "log_followers_june2017",
    "is_Puerto_Rico", "is_California", "is_New_York", "is_Florida", "is_Texas",
    "is_Georgia", "is_Illinois", "is_international",
]


def _pearson_r(x: list[float], y: list[float]) -> float | None:
    """Pearson correlation; drop pairs where either is None; return None if n < 2 or variance 0."""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 2:
        return None
    sum_x = sum(a for a, _ in pairs)
    sum_y = sum(b for _, b in pairs)
    sum_xx = sum(a * a for a, _ in pairs)
    sum_yy = sum(b * b for _, b in pairs)
    sum_xy = sum(a * b for a, b in pairs)
    num = n * sum_xy - sum_x * sum_y
    den = math.sqrt(max(0, (n * sum_xx - sum_x * sum_x) * (n * sum_yy - sum_y * sum_y)))
    if den == 0:
        return None
    return num / den


def feature_importance_correlation(
    table: list[dict], target: str = "made_finale", features: list[str] | None = None
) -> list[tuple[str, float, int]]:
    """
    For each numeric feature, compute Pearson correlation with target. Return list of
    (feature_name, correlation, n_used) sorted by absolute correlation descending.
    Rows with missing target or feature are dropped for that feature.
    """
    features = features or IMPORTANCE_FEATURES
    y_raw = [r.get(target) for r in table]
    y = []
    for v in y_raw:
        if v is None:
            y.append(None)
        elif isinstance(v, (int, float)):
            y.append(float(v))
        else:
            y.append(_to_float(v))
    if not y or all(v is None for v in y):
        return []

    result = []
    for feat in features:
        x = []
        for r in table:
            v = r.get(feat)
            if v is None:
                x.append(None)
            elif isinstance(v, (int, float)):
                x.append(float(v))
            else:
                x.append(_to_float(v))
        pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
        if len(pairs) < 2:
            result.append((feat, 0.0, len(pairs)))
            continue
        x_vals = [a for a, _ in pairs]
        y_vals = [b for _, b in pairs]
        r_val = _pearson_r(x_vals, y_vals)
        if r_val is None:
            r_val = 0.0
        result.append((feat, r_val, len(pairs)))
    result.sort(key=lambda t: -abs(t[1]))
    return result


def write_contestant_season_csv(table: list[dict], path: Path) -> None:
    """Write contestant-season table to CSV; include optional columns if present."""
    if not table:
        return
    all_keys = set()
    for r in table:
        all_keys.update(r.keys())
    fieldnames = ["season", "contestant", "age", "made_finale", "winner", "n_wins", "n_highs", "n_lows", "n_lipsyncs", "n_episodes"]
    for k in sorted(all_keys):
        if k not in fieldnames:
            fieldnames.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(table)


def run_simple_association(table: list[dict]) -> dict:
    """
    Stdlib-only: association between n_wins and made_finale (counts and simple rate).
    Returns dict with counts and finale rate by win bucket.
    """
    buckets = defaultdict(lambda: {"total": 0, "finale": 0})
    for r in table:
        w = r.get("n_wins", 0)
        if not isinstance(w, int):
            try:
                w = int(w)
            except (ValueError, TypeError):
                w = 0
        bucket = f"{w}_wins"
        buckets[bucket]["total"] += 1
        if r.get("made_finale"):
            buckets[bucket]["finale"] += 1
    result = {}
    for b in sorted(buckets.keys(), key=lambda x: int(x.split("_")[0])):
        t = buckets[b]["total"]
        f = buckets[b]["finale"]
        result[b] = {"n": t, "made_finale": f, "rate": round(f / t, 2) if t else 0}
    return result


def main(data: dict, data_dir: Path | None = None) -> list[dict]:
    """
    Build contestant-season table from load_all() result, write to data/staged, run simple association, return table.
    """
    merged = data.get("merged", [])
    if not merged:
        return []
    table = build_contestant_season_table(merged)
    table = engineer_features(table)

    data_dir = data_dir or data.get("data_dir") or DATA_DIR_DEFAULT
    staged = data_dir / "staged"
    staged.mkdir(parents=True, exist_ok=True)
    write_contestant_season_csv(table, staged / "contestant_season.csv")

    assoc = run_simple_association(table)
    print("\n--- Analysis: contestant-season table ---")
    print(f"  Rows (one per contestant per season): {len(table)}")
    print("  Made finale by main-challenge wins:")
    for bucket, v in assoc.items():
        print(f"    {bucket}: {v['made_finale']}/{v['n']} made finale ({v['rate']})")
    n_finale = sum(r.get("made_finale") for r in table)
    n_winners = sum(r.get("winner") for r in table)
    print(f"  Total: {n_finale} made finale, {n_winners} winners")

    importance = feature_importance_correlation(table, target="made_finale")
    print("\n--- Feature importance (correlation with made_finale) ---")
    print("  Ranked by |r| (higher = stronger association with making the finale):")
    for i, (feat, r_val, n) in enumerate(importance[:20], 1):
        print(f"    {i:2}. {feat:24} r = {r_val:+.3f}  (n = {n})")
    if importance:
        top_feat, top_r, _ = importance[0]
        print(f"  Top driver: {top_feat} (r = {top_r:+.3f})")

    # Finale rate by state/region (hometown)
    by_region = defaultdict(lambda: {"n": 0, "finale": 0})
    for r in table:
        reg = r.get("state_or_country") or "(missing)"
        by_region[reg]["n"] += 1
        if r.get("made_finale"):
            by_region[reg]["finale"] += 1
    print("\n--- Finale rate by state/country (hometown) ---")
    for reg in sorted(by_region.keys(), key=lambda x: (-by_region[x]["n"], x)):
        v = by_region[reg]
        if v["n"] < 2:
            continue
        rate = v["finale"] / v["n"]
        print(f"    {reg:28} {v['finale']}/{v['n']} made finale ({rate:.0%})")
    geo_imp = [(f, r, n) for f, r, n in importance if f.startswith("is_") or f == "age_num"]
    if geo_imp:
        strongest_geo = max(geo_imp, key=lambda t: abs(t[1]))
        print(f"  Strongest geographic/age feature: {strongest_geo[0]} (r = {strongest_geo[1]:+.3f})")

    return table
