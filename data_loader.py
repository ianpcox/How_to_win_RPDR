"""
Load and reconcile RPDR data from multiple sources.
- csvbase: contestant-level (season, contestant, age, dob, hometown).
- Rdatasets (GitHub): dragracer rpdr_contestants, rpdr_contep (episode-contestant outcomes).
- tashapiro/drag-race (optional): contestant real_name, gender, location, hometown.
- data/: local staged files (Instagram followers, Predict-a-Looza table_metadata).
"""
from __future__ import annotations

import csv
import io
import re
import urllib.request
from pathlib import Path
from typing import Any

# Local data folder and file names (staged under data/)
DATA_DIR_DEFAULT = Path(__file__).resolve().parent / "data"
INSTAGRAM_WEEK23_FILENAME = "Most followed Queens on Instagram - Week 23.csv"
INSTAGRAM_JUNE2017_FILENAME = "RPDR Contestant Instagram Followers as of June 2017 - Sheet1.csv"
PREDICTALOOZA_METADATA_FILENAME = "RuPaul-Predict-A-Looza — Data Tables - table_metadata.csv"
STAGED_DIR = "staged"

CSVBASE_CONTESTANTS = "https://csvbase.com/rmirror/rpdr-contestants.csv"
RDATASETS_BASE = "https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/dragracer"
RDATASETS_CONTESTANTS = f"{RDATASETS_BASE}/rpdr_contestants.csv"
RDATASETS_CONTEP = f"{RDATASETS_BASE}/rpdr_contep.csv"
TASHAPIRO_CONTESTANTS = "https://raw.githubusercontent.com/tashapiro/drag-race/main/data/contestant.csv"

# Known contestant name variants in local files -> canonical (Rdatasets) name
CONTESTANT_NAME_ALIASES: dict[str, str] = {
    "BobTDQ": "Bob the Drag Queen",
    "CLF": "Cynthia Lee Fontaine",
    "Dax ExclamationPOint": "Dax!",
    "Dax Exclamation Point": "Dax!",
    "Victoria Parker": 'Victoria "Porkchop" Parker',
    "Chi Chi Devayne": "Chi Chi DeVayne",
    "BenDelaCreme": "BenDeLaCreme",
    "Ivy WInters": "Ivy Winters",
    "Darienne LAke": "Darienne Lake",
    "Kameron MIchaels": "Kameron Michaels",
    "WIllam": "Willam",
    "Miss Fame ": "Miss Fame",
    "Nina Bo'Nina Brown": "Nina Bo'Nina Brown",
    "Trinity K Bonet": "Trinity K. Bonet",
    "Mrs Kasha Davis": "Mrs. Kasha Davis",
    "Shangela Laquifa Wadley": "Shangela",
    "Jade": "Jade Sotomayor",
    "Alaska Thunderfuck 5000": "Alaska",
}


def _normalize_season(s: str) -> str:
    """Map 'Season 1' / 'SEASON 1' / '1' -> S01 (Rdatasets format)."""
    s = (s or "").strip()
    if not s:
        return ""
    m = re.search(r"(?:season\s*)?(\d+)", s, re.IGNORECASE)
    if m:
        return "S" + m.group(1).zfill(2)
    return s


def _normalize_contestant(name: str) -> str:
    """Strip and apply known aliases for matching to Rdatasets contestant names."""
    name = (name or "").strip()
    if not name:
        return name
    return CONTESTANT_NAME_ALIASES.get(name, name)


def _parse_followers(s: str) -> int | None:
    """Parse follower count string to int: '977K' -> 977000, '1.1m' -> 1100000, '3,265' -> 3265."""
    s = (s or "").strip().replace(",", "").upper()
    if not s or s in ("NONE", "SAME", ""):
        return None
    m = re.match(r"^([\d.]+)\s*([KMB])?$", s)
    if not m:
        try:
            return int(float(s))
        except ValueError:
            return None
    num = float(m.group(1))
    suffix = (m.group(2) or "").strip()
    if suffix == "K":
        num *= 1000
    elif suffix == "M":
        num *= 1_000_000
    elif suffix == "B":
        num *= 1_000_000_000
    return int(num)


def _fetch_csv(url: str) -> list[dict[str, Any]]:
    with urllib.request.urlopen(url) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def fetch_csvbase_contestants() -> list[dict[str, Any]]:
    """Contestant-level from csvbase (mirror)."""
    rows = _fetch_csv(CSVBASE_CONTESTANTS)
    for r in rows:
        r["source"] = "csvbase"
    return rows


def fetch_rdatasets_contestants() -> list[dict[str, Any]]:
    """Contestant-level from R dragracer package (Rdatasets mirror)."""
    rows = _fetch_csv(RDATASETS_CONTESTANTS)
    for r in rows:
        r["source"] = "rdatasets"
    return rows


def fetch_rdatasets_contep() -> list[dict[str, Any]]:
    """Episode-contestant outcomes from R dragracer (Rdatasets mirror)."""
    return _fetch_csv(RDATASETS_CONTEP)


def fetch_tashapiro_contestants() -> list[dict[str, Any]]:
    """Contestant table from tashapiro/drag-race: real_name, gender, hometown, location (US + other franchises)."""
    return _fetch_csv(TASHAPIRO_CONTESTANTS)


def load_instagram_week23(path: Path) -> list[dict[str, Any]]:
    """
    Parse 'Most followed Queens on Instagram - Week 23' CSV (RPDR block only).
    Returns list of dicts with contestant, followers_week23 (int), and season if present.
    """
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    # Header row 0-2; RPDR data in cols 0-3 (Rank, Queen, Followers, Season), rows 3 until empty or Dragula
    for i, row in enumerate(rows):
        if i < 3:
            continue
        if len(row) < 2:
            continue
        queen = (row[1] or "").strip()
        if not queen or queen.lower().startswith("rank") or "Dragula" in str(row):
            continue
        followers = _parse_followers(row[2]) if len(row) > 2 else None
        season_raw = (row[3] or "").strip() if len(row) > 3 else ""
        season = _normalize_season(season_raw) if season_raw else ""
        queen = _normalize_contestant(queen)
        out.append({
            "contestant": queen,
            "followers_week23": followers,
            "season": season,
        })
    return out


def load_instagram_june2017(path: Path) -> list[dict[str, Any]]:
    """
    Parse 'RPDR Contestant Instagram Followers as of June 2017' wide CSV.
    Unpivot to one row per (season, contestant, followers_june2017). Seasons 1-9.
    """
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return out
    # Row 0: SEASON 1, Followers, SEASON 2, Followers, ... (9 pairs)
    header = rows[0]
    # Data rows 1-9 (contestants per column pair)
    for row_idx in range(1, min(10, len(rows))):
        row = rows[row_idx]
        for col in range(0, min(18, len(header)), 2):
            season_label = (header[col] or "").strip().upper()
            if not season_label.startswith("SEASON") or col + 1 >= len(row):
                continue
            season_num = re.search(r"(\d+)", season_label)
            season = "S" + season_num.group(1).zfill(2) if season_num else ""
            contestant = _normalize_contestant((row[col] or "").strip())
            if not contestant or contestant.upper().startswith("TOP") or contestant.upper().startswith("KEY") or contestant.upper().startswith("BOLD"):
                continue
            followers = _parse_followers(row[col + 1]) if col + 1 < len(row) else None
            if contestant in ("", "None", "Same"):
                continue
            out.append({
                "season": season,
                "contestant": contestant,
                "followers_june2017": followers,
            })
    return out


def load_table_metadata(path: Path) -> list[dict[str, Any]]:
    """Load Predict-a-Looza table_metadata.csv as schema reference (no merge)."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_local_data(data_dir: Path | None = None) -> dict[str, Any]:
    """
    Load and parse the 3 staged files from data_dir (default: data/ next to this file).
    Returns:
    - instagram_week23: list of {contestant, followers_week23, season}
    - instagram_june2017: list of {season, contestant, followers_june2017}
    - table_metadata: list of schema rows for Predict-a-Looza tables
    """
    data_dir = data_dir or DATA_DIR_DEFAULT
    result: dict[str, Any] = {
        "instagram_week23": [],
        "instagram_june2017": [],
        "table_metadata": [],
    }
    result["instagram_week23"] = load_instagram_week23(data_dir / INSTAGRAM_WEEK23_FILENAME)
    result["instagram_june2017"] = load_instagram_june2017(data_dir / INSTAGRAM_JUNE2017_FILENAME)
    result["table_metadata"] = load_table_metadata(data_dir / PREDICTALOOZA_METADATA_FILENAME)
    return result


def write_staged_csvs(data_dir: Path, local_data: dict[str, Any]) -> None:
    """Write parsed Instagram tables to data_dir/staged/ for reproducibility."""
    staged = data_dir / STAGED_DIR
    staged.mkdir(parents=True, exist_ok=True)
    w23 = local_data.get("instagram_week23", [])
    if w23:
        path = staged / "instagram_week23.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["contestant", "followers_week23", "season"])
            w.writeheader()
            w.writerows(w23)
    j17 = local_data.get("instagram_june2017", [])
    if j17:
        path = staged / "instagram_june2017.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["season", "contestant", "followers_june2017"])
            w.writeheader()
            w.writerows(j17)


def build_instagram_by_key(
    instagram_week23: list[dict],
    instagram_june2017: list[dict],
    canonical_keys: set[tuple[str, str]],
) -> dict[tuple[str, str], dict[str, Any]]:
    """
    Build (season, contestant) -> {followers_week23, followers_june2017} for keys in canonical_keys.
    Week 23 has no season for many rows; match by contestant only and attach to every matching (s, c).
    """
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    # June 2017: explicit (season, contestant)
    for r in instagram_june2017:
        s, c = (r.get("season") or "").strip(), (r.get("contestant") or "").strip()
        if (s, c) in canonical_keys:
            entry = by_key.setdefault((s, c), {})
            if r.get("followers_june2017") is not None:
                entry["followers_june2017"] = r["followers_june2017"]
    # Week 23: by contestant; add to every (season, contestant) that matches
    name_to_followers: dict[str, int | None] = {}
    for r in instagram_week23:
        c = (r.get("contestant") or "").strip()
        if c:
            name_to_followers[c] = r.get("followers_week23")
    for (s, c) in canonical_keys:
        entry = by_key.setdefault((s, c), {})
        if c in name_to_followers and name_to_followers[c] is not None:
            entry["followers_week23"] = name_to_followers[c]
    return by_key


def build_tashapiro_by_name(
    tashapiro_rows: list[dict], us_only: bool = True
) -> dict[str, dict]:
    """Map drag name -> first row (real_name, gender, hometown, location). If us_only, keep F10* (US main series)."""
    rows = tashapiro_rows
    if us_only:
        rows = [r for r in rows if (r.get("original_season_id") or "").startswith("F10")]
    by_name: dict[str, dict] = {}
    for r in rows:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        if name not in by_name:
            by_name[name] = {
                "real_name": (r.get("real_name") or "").strip(),
                "gender": (r.get("gender") or "").strip(),
                "tashapiro_hometown": (r.get("hometown") or "").strip(),
                "location": (r.get("location") or "").strip(),
            }
    return by_name


def _key(r: dict) -> tuple[str, str]:
    s = (r.get("season") or "").strip()
    c = (r.get("contestant") or "").strip()
    return (s, c)


def reconcile_contestants(
    csvbase: list[dict], rdatasets: list[dict]
) -> dict[str, Any]:
    """
    Reconcile contestant-level tables. Returns dict with:
    - matched: list of (season, contestant) in both
    - only_csvbase: list of (season, contestant)
    - only_rdatasets: list of (season, contestant)
    - csvbase_count, rdatasets_count
    - age_diffs: list of (season, contestant, age_csvbase, age_rdatasets) where both have age and they differ
    """
    keys_c = {_key(r) for r in csvbase}
    keys_r = {_key(r) for r in rdatasets}
    matched = list(keys_c & keys_r)
    only_csvbase = list(keys_c - keys_r)
    only_rdatasets = list(keys_r - keys_c)

    age_diffs = []
    by_key_c = {_key(r): r for r in csvbase}
    by_key_r = {_key(r): r for r in rdatasets}
    for (s, c) in matched:
        rc = by_key_c[(s, c)]
        rr = by_key_r[(s, c)]
        ac = (rc.get("age") or "").strip()
        ar = (rr.get("age") or "").strip()
        if ac and ar and ac != ar:
            age_diffs.append((s, c, ac, ar))

    return {
        "matched": matched,
        "only_csvbase": only_csvbase,
        "only_rdatasets": only_rdatasets,
        "csvbase_count": len(csvbase),
        "rdatasets_count": len(rdatasets),
        "age_diffs": age_diffs,
    }


def build_merged_contestants(
    rdatasets_contestants: list[dict],
    tashapiro_by_name: dict[str, dict] | None = None,
    instagram_by_key: dict[tuple[str, str], dict] | None = None,
) -> dict[tuple[str, str], dict]:
    """Index Rdatasets contestants by (season, contestant) for join; optionally add tashapiro and local Instagram fields."""
    out: dict[tuple[str, str], dict] = {}
    for r in rdatasets_contestants:
        k = _key(r)
        row = {k: v for k, v in r.items() if k != "source"}
        if tashapiro_by_name:
            name = (r.get("contestant") or "").strip()
            extra = tashapiro_by_name.get(name)
            if extra:
                row.update(extra)
        if instagram_by_key and k in instagram_by_key:
            row.update(instagram_by_key[k])
        out[k] = row
    return out


def merge_contestants_with_contep(
    contestants: dict[tuple[str, str], dict], contep: list[dict]
) -> list[dict]:
    """
    One row per episode-contestant, with contestant attributes merged in.
    Contestant fields get prefix contestant_ to avoid clash with episode fields.
    """
    out = []
    for row in contep:
        k = _key(row)
        attrs = contestants.get(k, {})
        merged = dict(row)
        for key, val in attrs.items():
            if key in merged:
                merged["contestant_" + key] = val
            else:
                merged[key] = val
        out.append(merged)
    return out


def load_all(
    include_tashapiro: bool = True,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Fetch all sources, reconcile contestant tables, merge contep with contestants.
    If include_tashapiro is True, fetches tashapiro contestant.csv and merges real_name, gender, location.
    If data_dir is set, loads local staged files (Instagram, table_metadata) and merges Instagram into contestants.
    Returns dict with:
    - csvbase_contestants, rdatasets_contestants, contep (raw)
    - tashapiro_contestants (if include_tashapiro), tashapiro_by_name
    - reconciliation (output of reconcile_contestants)
    - merged (episode-contestant with contestant attributes)
    - local_data, instagram_by_key (if data_dir used)
    """
    csvbase = fetch_csvbase_contestants()
    rdatasets_c = fetch_rdatasets_contestants()
    contep = fetch_rdatasets_contep()

    tashapiro_rows: list[dict[str, Any]] = []
    tashapiro_by_name: dict[str, dict] = {}
    if include_tashapiro:
        try:
            tashapiro_rows = fetch_tashapiro_contestants()
            tashapiro_by_name = build_tashapiro_by_name(tashapiro_rows)
        except Exception:
            pass  # optional source

    reconciliation = reconcile_contestants(csvbase, rdatasets_c)
    canonical_keys = {_key(r) for r in rdatasets_c}

    instagram_by_key: dict[tuple[str, str], dict] = {}
    local_data: dict[str, Any] = {}
    if data_dir is not None:
        local_data = load_local_data(data_dir)
        write_staged_csvs(data_dir, local_data)
        instagram_by_key = build_instagram_by_key(
            local_data["instagram_week23"],
            local_data["instagram_june2017"],
            canonical_keys,
        )

    contestant_index = build_merged_contestants(
        rdatasets_c,
        tashapiro_by_name if tashapiro_by_name else None,
        instagram_by_key if instagram_by_key else None,
    )
    merged = merge_contestants_with_contep(contestant_index, contep)

    result: dict[str, Any] = {
        "csvbase_contestants": csvbase,
        "rdatasets_contestants": rdatasets_c,
        "contep": contep,
        "reconciliation": reconciliation,
        "merged": merged,
    }
    if include_tashapiro:
        result["tashapiro_contestants"] = tashapiro_rows
        result["tashapiro_by_name"] = tashapiro_by_name
    if data_dir is not None:
        result["local_data"] = local_data
        result["instagram_by_key"] = instagram_by_key
    return result
