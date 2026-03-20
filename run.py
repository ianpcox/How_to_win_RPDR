"""
Entry point for How to Win RPDR. Fetches data from csvbase + Rdatasets, reconciles,
merges episode-level outcomes, runs EDA, and outputs metrics. Optionally loads
staged local data from data/ (Instagram followers, Predict-a-Looza table_metadata).
"""
from pathlib import Path

from collections import Counter, defaultdict

from data_loader import DATA_DIR_DEFAULT, load_all

from analysis import main as run_analysis


def run_eda_contestants(contestants: list) -> dict:
    """Summary stats from contestant-level rows (need 'season', 'age')."""
    if not contestants:
        return {"n_contestants": 0, "n_seasons": 0}
    seasons = {r.get("season", "").strip() for r in contestants if r.get("season")}
    ages = []
    for r in contestants:
        a = r.get("age", "").strip()
        if a and str(a).isdigit():
            ages.append(int(a))
    return {
        "n_contestants": len(contestants),
        "n_seasons": len(seasons),
        "seasons": sorted(seasons),
        "age_min": min(ages) if ages else None,
        "age_max": max(ages) if ages else None,
        "age_mean": round(sum(ages) / len(ages), 1) if ages else None,
    }


def run_eda_episodes(merged: list) -> dict:
    """Outcome counts and episode coverage from merged episode-contestant data."""
    if not merged:
        return {"n_episode_contestant_rows": 0}
    outcomes = [r.get("outcome", "").strip() or "(blank)" for r in merged]
    outcome_counts = dict(Counter(outcomes))
    n_elim = sum(1 for r in merged if (r.get("eliminated") or "").strip() == "1")
    seasons = {r.get("season", "").strip() for r in merged if r.get("season")}
    # Episode-level: (season, episode) -> count of eliminated in that episode
    elim_per_ep = defaultdict(int)
    for r in merged:
        if (r.get("eliminated") or "").strip() == "1":
            key = (r.get("season", "").strip(), r.get("episode", "").strip())
            if key[0] and key[1]:
                elim_per_ep[key] += 1
    episodes_with_elim = [k for k, c in elim_per_ep.items() if c > 0]
    no_elim_episodes = len(set((r.get("season"), r.get("episode")) for r in merged if r.get("season") and r.get("episode"))) - len(set(episodes_with_elim))
    double_elim_episodes = sum(1 for c in elim_per_ep.values() if c >= 2)
    n_mini_wins = sum(1 for r in merged if (r.get("minichalw") or "").strip() == "1")
    return {
        "n_episode_contestant_rows": len(merged),
        "outcome_counts": outcome_counts,
        "n_eliminated_episodes": n_elim,
        "seasons_with_episodes": sorted(seasons),
        "n_episodes_no_elimination": no_elim_episodes,
        "n_episodes_double_elim": double_elim_episodes,
        "n_mini_challenge_wins": n_mini_wins,
    }


def main():
    print("=== How to Win RPDR ===\n")
    print("Fetching: csvbase, Rdatasets contestants + contep, tashapiro contestant (optional)...")
    data_dir = DATA_DIR_DEFAULT if (DATA_DIR_DEFAULT / "Most followed Queens on Instagram - Week 23.csv").exists() else None
    if data_dir:
        print("Loading local staged data from data/ (Instagram, table_metadata)...")
    data = load_all(data_dir=data_dir)

    rec = data["reconciliation"]
    print("\n--- Reconciliation (contestant-level: csvbase vs Rdatasets) ---")
    print(f"  csvbase:   {rec['csvbase_count']} contestants")
    print(f"  Rdatasets: {rec['rdatasets_count']} contestants")
    print(f"  matched (season+contestant in both): {len(rec['matched'])}")
    if rec["only_csvbase"]:
        print(f"  only in csvbase:   {len(rec['only_csvbase'])} e.g. {rec['only_csvbase'][:3]}")
    if rec["only_rdatasets"]:
        print(f"  only in Rdatasets: {len(rec['only_rdatasets'])} e.g. {rec['only_rdatasets'][:3]}")
    if rec["age_diffs"]:
        print(f"  age differences (same contestant): {len(rec['age_diffs'])} e.g. {rec['age_diffs'][:2]}")

    if data.get("tashapiro_by_name"):
        tb = data["tashapiro_by_name"]
        # How many Rdatasets contestants match tashapiro by name
        rnames = {(r.get("contestant") or "").strip() for r in data["rdatasets_contestants"]}
        matched = [n for n in rnames if n and n in tb]
        print(f"\n--- Expanded (tashapiro: real_name, gender, location) ---")
        print(f"  contestants matched: {len(matched)} / {len(rnames)}")
        if matched:
            ex = "Plastique Tiara" if "Plastique Tiara" in matched else matched[0]
            info = tb.get(ex, {})
            print(f"  example: {ex} -> real_name={info.get('real_name', '')}, location={info.get('location', '')}")

    if data.get("instagram_by_key"):
        ig = data["instagram_by_key"]
        n_with_ig = sum(1 for v in ig.values() if v.get("followers_week23") or v.get("followers_june2017"))
        print(f"\n--- Local data (data/): Instagram merged into central DB ---")
        print(f"  contestants with Instagram (week23 or June 2017): {n_with_ig} / {len(ig)}")
        if data.get("local_data", {}).get("table_metadata"):
            print(f"  table_metadata: {len(data['local_data']['table_metadata'])} schema rows (Predict-a-Looza reference)")
        staged = DATA_DIR_DEFAULT / "staged"
        if staged.exists():
            print(f"  staged CSVs: {list(staged.glob('*.csv'))}")

    contestants = data["rdatasets_contestants"]
    metrics_c = run_eda_contestants(contestants)
    print("\n--- EDA (contestants, Rdatasets canonical) ---")
    print(f"  n_contestants: {metrics_c['n_contestants']}")
    print(f"  n_seasons:      {metrics_c['n_seasons']}")
    if metrics_c.get("age_mean") is not None:
        print(f"  age (min/max/mean): {metrics_c['age_min']} / {metrics_c['age_max']} / {metrics_c['age_mean']}")
    print(f"  seasons:       {metrics_c.get('seasons', [])[:6]} ...")

    merged = data["merged"]
    metrics_e = run_eda_episodes(merged)
    print("\n--- EDA (episode-contestant, merged) ---")
    print(f"  n_episode_contestant_rows: {metrics_e['n_episode_contestant_rows']}")
    print(f"  outcome_counts: {metrics_e.get('outcome_counts', {})}")
    print(f"  n_eliminated_episodes: {metrics_e.get('n_eliminated_episodes', 0)}")
    print(f"  episodes (no elimination): {metrics_e.get('n_episodes_no_elimination', 'N/A')} (ties/double save)")
    print(f"  episodes (double elim): {metrics_e.get('n_episodes_double_elim', 'N/A')}")
    print(f"  mini-challenge wins (minichalw=1): {metrics_e.get('n_mini_challenge_wins', 'N/A')}")
    print(f"  seasons_with_episodes: {metrics_e.get('seasons_with_episodes', [])[:6]} ...")

    run_analysis(data, data_dir=data_dir)

    print("\nBaseline (prediction): use merged data for win/elimination features; see docs/report.md.")
    print("Ties/no-elim, mini/maxi: see docs/data_sheet.md.")
    print("Years doing drag, social media, race/ethnicity: see docs/DATA_EXPANSION_SOURCES.md.")


if __name__ == "__main__":
    main()
