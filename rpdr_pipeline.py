"""
Elevated RPDR Analytics Pipeline — How to Win RuPaul's Drag Race
Project Elevate — How_to_win_RPDR

Performs:
  1. Data loading & feature engineering from contestant_season.csv
  2. Win-rate & finale-rate analysis by season
  3. Performance archetype clustering (K-Means)
  4. Logistic regression: predicting finale & winner
  5. Social media (Instagram) correlation analysis
  6. Geographic analysis by state/country
  7. 12 static charts + interactive Plotly dashboard

Dataset: 184 contestant-season records across RPDR Seasons 1-9
"""

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (classification_report, confusion_matrix,
                              roc_auc_score, roc_curve)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

DATA_DIR = Path("/home/ubuntu/rpdr_data")
OUT_DIR  = Path("/home/ubuntu/rpdr_outputs")
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
})

RPDR_PINK   = "#FF69B4"
RPDR_PURPLE = "#9B59B6"
RPDR_GOLD   = "#F1C40F"
RPDR_TEAL   = "#1ABC9C"


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "contestant_season.csv")
    print(f"Loaded {len(df)} contestant-season records")

    # Numeric coercions
    num_cols = ["age_num", "n_wins", "n_highs", "n_lows", "n_lipsyncs",
                "n_episodes", "wins_per_episode", "highs_per_episode",
                "lows_per_episode", "lipsyncs_per_episode",
                "followers_june2017", "followers_week23",
                "log_followers_june2017", "log_followers_week23",
                "total_top", "total_bottom", "season_num"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Boolean coercions
    for c in ["made_finale", "winner", "had_any_win", "had_any_lipsync"]:
        if c in df.columns:
            df[c] = df[c].astype(float).fillna(0).astype(int)

    # Composite performance score (normalized)
    df["performance_score"] = (
        df["n_wins"].fillna(0) * 3 +
        df["n_highs"].fillna(0) * 2 +
        df["n_lows"].fillna(0) * -1 +
        df["n_lipsyncs"].fillna(0) * -1
    )

    # Win consistency (wins per episode, 0 if no episodes)
    df["win_rate"] = df["wins_per_episode"].fillna(0)

    print(f"  Seasons: {sorted(df['season_num'].dropna().astype(int).unique())}")
    print(f"  Winners: {df['winner'].sum()}")
    print(f"  Finalists: {df['made_finale'].sum()}")
    return df


# ── Visualizations ────────────────────────────────────────────────────────────

def plot_season_overview(df):
    season_stats = df.groupby("season_num").agg(
        contestants=("contestant", "count"),
        winners=("winner", "sum"),
        finalists=("made_finale", "sum"),
        avg_wins=("n_wins", "mean"),
        avg_episodes=("n_episodes", "mean"),
    ).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Contestants per season
    axes[0].bar(season_stats["season_num"], season_stats["contestants"],
                color=RPDR_PINK, alpha=0.85, edgecolor="white")
    axes[0].plot(season_stats["season_num"], season_stats["finalists"],
                 "o-", color=RPDR_PURPLE, lw=2, markersize=7, label="Finalists")
    axes[0].set_xlabel("Season")
    axes[0].set_ylabel("Count")
    axes[0].set_title("Contestants & Finalists per Season")
    axes[0].legend()
    axes[0].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    # Avg wins per season
    axes[1].bar(season_stats["season_num"], season_stats["avg_wins"],
                color=RPDR_GOLD, alpha=0.85, edgecolor="white")
    axes[1].set_xlabel("Season")
    axes[1].set_ylabel("Average Challenge Wins per Contestant")
    axes[1].set_title("Average Challenge Wins per Season")
    axes[1].xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    plt.suptitle("RPDR Season Overview", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "01_season_overview.png")
    plt.close()
    print("Saved: 01_season_overview.png")


def plot_finale_drivers(df):
    """What separates finalists from eliminated queens?"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    metrics = [
        ("n_wins", "Challenge Wins"),
        ("n_highs", "High Placements"),
        ("n_lipsyncs", "Lip Syncs"),
    ]
    colors = {"Finalist": RPDR_PINK, "Eliminated": RPDR_PURPLE}

    for ax, (col, label) in zip(axes, metrics):
        for group, color in colors.items():
            flag = 1 if group == "Finalist" else 0
            data = df[df["made_finale"] == flag][col].dropna()
            ax.hist(data, bins=10, alpha=0.6, color=color, label=group, edgecolor="white")
        ax.set_xlabel(label)
        ax.set_ylabel("Number of Queens")
        ax.set_title(f"Distribution of {label}")
        ax.legend()

    plt.suptitle("What Separates Finalists from Eliminated Queens?",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "02_finale_drivers.png")
    plt.close()
    print("Saved: 02_finale_drivers.png")


def plot_winner_profile(df):
    """Profile of winners vs. finalists vs. eliminated."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Box plot: performance score by outcome
    df["outcome"] = df.apply(
        lambda r: "Winner" if r["winner"] else ("Finalist" if r["made_finale"] else "Eliminated"),
        axis=1
    )
    order = ["Winner", "Finalist", "Eliminated"]
    palette = {"Winner": RPDR_GOLD, "Finalist": RPDR_PINK, "Eliminated": RPDR_PURPLE}

    sns.boxplot(data=df, x="outcome", y="performance_score",
                order=order, palette=palette, ax=axes[0], linewidth=1.5)
    axes[0].set_xlabel("Outcome")
    axes[0].set_ylabel("Performance Score")
    axes[0].set_title("Performance Score by Outcome\n(wins×3 + highs×2 − lows − lipsyncs)")

    # Win rate by outcome
    win_rate = df.groupby("outcome")["win_rate"].mean().reindex(order)
    colors = [palette[o] for o in order]
    axes[1].bar(win_rate.index, win_rate.values, color=colors, alpha=0.85, edgecolor="white")
    axes[1].set_ylabel("Average Win Rate (wins/episode)")
    axes[1].set_title("Average Win Rate by Outcome")
    for i, v in enumerate(win_rate.values):
        axes[1].text(i, v + 0.005, f"{v:.3f}", ha="center", fontsize=10, fontweight="bold")

    plt.suptitle("Winner vs. Finalist vs. Eliminated — Performance Profile",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "03_winner_profile.png")
    plt.close()
    print("Saved: 03_winner_profile.png")


def plot_archetype_clusters(df):
    """K-Means clustering to identify performance archetypes."""
    features = ["wins_per_episode", "highs_per_episode",
                "lows_per_episode", "lipsyncs_per_episode"]
    df_feat = df[features].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_feat)

    # Elbow method
    inertias = []
    k_range = range(2, 8)
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)

    # Fit with k=4 (natural archetypes: winner, safe, bottom, lipsync-heavy)
    km4 = KMeans(n_clusters=4, random_state=42, n_init=10)
    df["archetype"] = km4.fit_predict(X_scaled)

    # Name archetypes by mean wins
    archetype_means = df.groupby("archetype")["wins_per_episode"].mean()
    rank_map = {k: i for i, k in enumerate(archetype_means.sort_values(ascending=False).index)}
    archetype_names = {
        rank_map[k]: name for k, name in zip(
            range(4), ["Challenge Dominator", "Consistent Performer", "Safe Player", "Bottom Feeder"]
        )
    }
    df["archetype_name"] = df["archetype"].map(archetype_names)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Elbow
    axes[0].plot(list(k_range), inertias, "o-", color=RPDR_PINK, lw=2, markersize=8)
    axes[0].axvline(4, color=RPDR_PURPLE, linestyle="--", lw=1.5, label="k=4 selected")
    axes[0].set_xlabel("Number of Clusters (k)")
    axes[0].set_ylabel("Inertia")
    axes[0].set_title("K-Means Elbow Method")
    axes[0].legend()

    # Archetype finale rates
    arch_finale = df.groupby("archetype_name").agg(
        finale_rate=("made_finale", "mean"),
        n=("contestant", "count"),
    ).sort_values("finale_rate", ascending=True)
    colors = [RPDR_GOLD, RPDR_PINK, RPDR_TEAL, RPDR_PURPLE]
    axes[1].barh(arch_finale.index, arch_finale["finale_rate"] * 100,
                 color=colors, alpha=0.85, edgecolor="white")
    for i, (_, row) in enumerate(arch_finale.iterrows()):
        axes[1].text(row["finale_rate"] * 100 + 0.5, i,
                     f"{row['finale_rate']*100:.0f}%  (n={row['n']})",
                     va="center", fontsize=9)
    axes[1].set_xlabel("Finale Rate (%)")
    axes[1].set_title("Finale Rate by Performance Archetype")

    plt.suptitle("Performance Archetypes (K-Means Clustering)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "04_archetype_clusters.png")
    plt.close()
    print("Saved: 04_archetype_clusters.png")
    return df


def plot_lipsync_curse(df):
    """Does the lipsync curse hold? More lipsyncs = less likely to finale?"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Finale rate by lipsync count
    lipsync_finale = (
        df.groupby("n_lipsyncs")["made_finale"]
        .agg(rate="mean", count="count")
        .reset_index()
        .query("count >= 3")
    )
    colors = [RPDR_GOLD if r < 0.3 else RPDR_PINK if r < 0.5 else RPDR_TEAL
              for r in lipsync_finale["rate"]]
    axes[0].bar(lipsync_finale["n_lipsyncs"], lipsync_finale["rate"] * 100,
                color=colors, alpha=0.85, edgecolor="white")
    axes[0].set_xlabel("Number of Lip Syncs")
    axes[0].set_ylabel("Finale Rate (%)")
    axes[0].set_title("Finale Rate by Number of Lip Syncs\n(The Lipsync Curse)")

    # Scatter: lipsyncs vs. performance score, colored by finale
    finale_colors = df["made_finale"].map({1: RPDR_PINK, 0: RPDR_PURPLE})
    axes[1].scatter(df["n_lipsyncs"], df["performance_score"],
                    c=finale_colors, alpha=0.6, s=50, edgecolors="white", lw=0.5)
    axes[1].set_xlabel("Number of Lip Syncs")
    axes[1].set_ylabel("Performance Score")
    axes[1].set_title("Lip Syncs vs. Performance Score")
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=RPDR_PINK, label="Finalist"),
                       Patch(facecolor=RPDR_PURPLE, label="Eliminated")]
    axes[1].legend(handles=legend_elements)

    plt.suptitle("The Lipsync Curse — Does It Hold?", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "05_lipsync_curse.png")
    plt.close()
    print("Saved: 05_lipsync_curse.png")


def plot_geographic_analysis(df):
    """Which states/regions produce the most finalists?"""
    geo = (
        df.groupby("state_or_country")
        .agg(n=("contestant", "count"), finalists=("made_finale", "sum"))
        .assign(finale_rate=lambda x: x["finalists"] / x["n"])
        .query("n >= 3")
        .sort_values("n", ascending=True)
        .tail(15)
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Headcount
    colors = plt.cm.RdPu(np.linspace(0.3, 0.9, len(geo)))
    axes[0].barh(geo.index, geo["n"], color=colors, alpha=0.85, edgecolor="white")
    axes[0].set_xlabel("Number of Contestants")
    axes[0].set_title("Top 15 States/Countries by Contestant Count")

    # Finale rate
    rate_colors = ["#E74C3C" if v < 0.2 else "#F39C12" if v < 0.4 else "#2ECC71"
                   for v in geo["finale_rate"].values]
    axes[1].barh(geo.index, geo["finale_rate"] * 100,
                 color=rate_colors, alpha=0.85, edgecolor="white")
    axes[1].set_xlabel("Finale Rate (%)")
    axes[1].set_title("Finale Rate by State/Country")
    for i, (_, row) in enumerate(geo.iterrows()):
        axes[1].text(row["finale_rate"] * 100 + 0.5, i,
                     f"{row['finale_rate']*100:.0f}%", va="center", fontsize=8)

    plt.suptitle("Geographic Analysis — Where Do Champions Come From?",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "06_geographic_analysis.png")
    plt.close()
    print("Saved: 06_geographic_analysis.png")


def plot_age_analysis(df):
    """Does age matter on RPDR?"""
    df_age = df[df["age_num"].notna()].copy()
    df_age["age_group"] = pd.cut(df_age["age_num"],
                                  bins=[18, 24, 29, 34, 39, 44, 60],
                                  labels=["18-24", "25-29", "30-34", "35-39", "40-44", "45+"])

    age_stats = df_age.groupby("age_group", observed=True).agg(
        n=("contestant", "count"),
        finale_rate=("made_finale", "mean"),
        avg_wins=("n_wins", "mean"),
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].bar(age_stats.index.astype(str), age_stats["finale_rate"] * 100,
                color=RPDR_PINK, alpha=0.85, edgecolor="white")
    axes[0].set_xlabel("Age Group")
    axes[0].set_ylabel("Finale Rate (%)")
    axes[0].set_title("Finale Rate by Age Group")

    axes[1].bar(age_stats.index.astype(str), age_stats["avg_wins"],
                color=RPDR_PURPLE, alpha=0.85, edgecolor="white")
    axes[1].set_xlabel("Age Group")
    axes[1].set_ylabel("Average Challenge Wins")
    axes[1].set_title("Average Challenge Wins by Age Group")

    plt.suptitle("Does Age Matter on RPDR?", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "07_age_analysis.png")
    plt.close()
    print("Saved: 07_age_analysis.png")


def plot_instagram_correlation(df):
    """Social media following vs. performance."""
    df_ig = df[df["followers_june2017"].notna()].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Scatter: Instagram followers vs. performance score
    finale_colors = df_ig["made_finale"].map({1: RPDR_PINK, 0: RPDR_PURPLE})
    axes[0].scatter(df_ig["log_followers_june2017"], df_ig["performance_score"],
                    c=finale_colors, alpha=0.7, s=60, edgecolors="white", lw=0.5)
    axes[0].set_xlabel("Instagram Followers (log scale)")
    axes[0].set_ylabel("Performance Score")
    axes[0].set_title("Instagram Following vs. Performance Score")
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=RPDR_PINK, label="Finalist"),
                       Patch(facecolor=RPDR_PURPLE, label="Eliminated")]
    axes[0].legend(handles=legend_elements)

    # Box: followers by outcome
    df_ig["outcome"] = df_ig.apply(
        lambda r: "Winner" if r["winner"] else ("Finalist" if r["made_finale"] else "Eliminated"),
        axis=1
    )
    order = ["Winner", "Finalist", "Eliminated"]
    palette = {"Winner": RPDR_GOLD, "Finalist": RPDR_PINK, "Eliminated": RPDR_PURPLE}
    sns.boxplot(data=df_ig, x="outcome", y="log_followers_june2017",
                order=order, palette=palette, ax=axes[1], linewidth=1.5)
    axes[1].set_xlabel("Outcome")
    axes[1].set_ylabel("Instagram Followers (log scale)")
    axes[1].set_title("Instagram Following by Outcome")

    plt.suptitle("Social Media Following vs. Competition Performance",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "08_instagram_correlation.png")
    plt.close()
    print("Saved: 08_instagram_correlation.png")


def plot_correlation_heatmap(df):
    """Feature correlation heatmap."""
    corr_cols = ["n_wins", "n_highs", "n_lows", "n_lipsyncs",
                 "wins_per_episode", "highs_per_episode",
                 "performance_score", "age_num",
                 "log_followers_june2017", "made_finale", "winner"]
    available = [c for c in corr_cols if c in df.columns]
    corr = df[available].corr()

    fig, ax = plt.subplots(figsize=(11, 9))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, cmap="RdBu_r", center=0, ax=ax,
                annot=True, fmt=".2f", annot_kws={"size": 8},
                linewidths=0.3, cbar_kws={"label": "Pearson r"})
    ax.set_title("Feature Correlation Heatmap", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "09_correlation_heatmap.png")
    plt.close()
    print("Saved: 09_correlation_heatmap.png")


# ── Logistic Regression Model ─────────────────────────────────────────────────

def build_prediction_model(df):
    """Logistic regression to predict finale appearance."""
    print("\nBuilding logistic regression model...")

    features = ["wins_per_episode", "highs_per_episode",
                "lows_per_episode", "lipsyncs_per_episode",
                "age_num", "season_num"]
    available = [c for c in features if c in df.columns]
    df_model = df[available + ["made_finale"]].dropna()

    X = df_model[available]
    y = df_model["made_finale"].astype(int)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)

    y_pred  = lr.predict(X_test)
    y_proba = lr.predict_proba(X_test)[:, 1]
    auc     = roc_auc_score(y_test, y_proba)
    cv_auc  = cross_val_score(lr, X_scaled, y, cv=5, scoring="roc_auc")

    print(f"  Test ROC-AUC:  {auc:.3f}")
    print(f"  5-Fold CV AUC: {cv_auc.mean():.3f} ± {cv_auc.std():.3f}")
    print("\n" + classification_report(y_test, y_pred,
                                       target_names=["Eliminated", "Finalist"]))

    # Plot model results
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt="d", cmap="RdPu", ax=axes[0],
                xticklabels=["Eliminated", "Finalist"],
                yticklabels=["Eliminated", "Finalist"])
    axes[0].set_title("Confusion Matrix")
    axes[0].set_ylabel("Actual")
    axes[0].set_xlabel("Predicted")

    # ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    axes[1].plot(fpr, tpr, color=RPDR_PINK, lw=2, label=f"ROC AUC = {auc:.3f}")
    axes[1].plot([0, 1], [0, 1], "k--", lw=1)
    axes[1].set_xlabel("False Positive Rate")
    axes[1].set_ylabel("True Positive Rate")
    axes[1].set_title("ROC Curve — Finale Prediction Model")
    axes[1].legend()

    # Coefficients
    coef_df = pd.Series(lr.coef_[0], index=available).sort_values()
    colors = [RPDR_PINK if v > 0 else RPDR_PURPLE for v in coef_df.values]
    axes[2].barh(coef_df.index, coef_df.values, color=colors, alpha=0.85, edgecolor="white")
    axes[2].axvline(0, color="black", lw=0.8)
    axes[2].set_xlabel("Coefficient (log-odds)")
    axes[2].set_title("Logistic Regression Coefficients\n(Predictors of Finale Appearance)")

    plt.suptitle("Finale Prediction Model Results", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "10_model_results.png")
    plt.close()
    print("Saved: 10_model_results.png")

    return lr, scaler, available


def plot_wins_needed(df):
    """How many wins does it take to make the finale?"""
    wins_finale = (
        df.groupby("n_wins")["made_finale"]
        .agg(rate="mean", n="count")
        .reset_index()
        .query("n >= 2")
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    bar_colors = [RPDR_GOLD if r >= 0.5 else RPDR_PINK if r >= 0.25 else RPDR_PURPLE
                  for r in wins_finale["rate"]]
    bars = ax.bar(wins_finale["n_wins"], wins_finale["rate"] * 100,
                  color=bar_colors, alpha=0.85, edgecolor="white")
    ax.axhline(50, color="black", linestyle="--", lw=1.5, label="50% threshold")
    ax.set_xlabel("Number of Main Challenge Wins")
    ax.set_ylabel("Finale Rate (%)")
    ax.set_title("How Many Wins Does It Take to Make the Finale?\n(RPDR Seasons 1-9)",
                 fontsize=12, fontweight="bold")
    ax.legend()
    for bar, (_, row) in zip(bars, wins_finale.iterrows()):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"n={int(row['n'])}", ha="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "11_wins_needed.png")
    plt.close()
    print("Saved: 11_wins_needed.png")


# ── Interactive Plotly Dashboard ──────────────────────────────────────────────

def build_dashboard(df):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=[
            "Finale Rate by Challenge Wins",
            "Performance Score by Outcome",
            "Finale Rate by Age Group",
            "Geographic: Top States by Contestant Count",
            "Instagram Following vs. Performance Score",
            "Wins per Episode — Finalists vs. Eliminated",
        ],
        specs=[
            [{"type": "bar"}, {"type": "box"}],
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "scatter"}, {"type": "violin"}],
        ],
        vertical_spacing=0.13,
        horizontal_spacing=0.1,
    )

    # 1. Finale rate by wins
    wins_finale = (
        df.groupby("n_wins")["made_finale"]
        .agg(rate="mean", n="count")
        .reset_index()
        .query("n >= 2")
    )
    fig.add_trace(go.Bar(
        x=wins_finale["n_wins"], y=wins_finale["rate"] * 100,
        marker_color=RPDR_PINK, opacity=0.85,
        hovertemplate="Wins: %{x}<br>Finale Rate: %{y:.1f}%<extra></extra>",
    ), row=1, col=1)

    # 2. Performance score by outcome
    df["outcome"] = df.apply(
        lambda r: "Winner" if r["winner"] else ("Finalist" if r["made_finale"] else "Eliminated"),
        axis=1
    )
    for outcome, color in [("Winner", RPDR_GOLD), ("Finalist", RPDR_PINK), ("Eliminated", RPDR_PURPLE)]:
        sub = df[df["outcome"] == outcome]["performance_score"].dropna()
        fig.add_trace(go.Box(
            y=sub, name=outcome, marker_color=color, opacity=0.85,
            hovertemplate=f"{outcome}: %{{y:.1f}}<extra></extra>",
        ), row=1, col=2)

    # 3. Finale rate by age group
    df_age = df[df["age_num"].notna()].copy()
    df_age["age_group"] = pd.cut(df_age["age_num"],
                                  bins=[18, 24, 29, 34, 39, 44, 60],
                                  labels=["18-24", "25-29", "30-34", "35-39", "40-44", "45+"])
    age_stats = df_age.groupby("age_group", observed=True)["made_finale"].mean() * 100
    fig.add_trace(go.Bar(
        x=age_stats.index.astype(str), y=age_stats.values,
        marker_color=RPDR_TEAL, opacity=0.85,
        hovertemplate="Age: %{x}<br>Finale Rate: %{y:.1f}%<extra></extra>",
    ), row=2, col=1)

    # 4. Geographic
    geo = (
        df.groupby("state_or_country")
        .agg(n=("contestant", "count"))
        .query("n >= 3")
        .sort_values("n", ascending=False)
        .head(12)
    )
    fig.add_trace(go.Bar(
        x=geo["n"], y=geo.index, orientation="h",
        marker_color=RPDR_PURPLE, opacity=0.85,
        hovertemplate="%{y}: %{x} contestants<extra></extra>",
    ), row=2, col=2)

    # 5. Instagram scatter
    df_ig = df[df["log_followers_june2017"].notna()].copy()
    for outcome, color in [("Winner", RPDR_GOLD), ("Finalist", RPDR_PINK), ("Eliminated", RPDR_PURPLE)]:
        sub = df_ig[df_ig["outcome"] == outcome]
        fig.add_trace(go.Scatter(
            x=sub["log_followers_june2017"], y=sub["performance_score"],
            mode="markers", name=outcome,
            marker=dict(color=color, size=8, opacity=0.7),
            hovertemplate=f"{outcome}<br>Log Followers: %{{x:.1f}}<br>Score: %{{y:.1f}}<extra></extra>",
        ), row=3, col=1)

    # 6. Win rate violin
    for outcome, color in [("Winner", RPDR_GOLD), ("Finalist", RPDR_PINK), ("Eliminated", RPDR_PURPLE)]:
        sub = df[df["outcome"] == outcome]["wins_per_episode"].dropna()
        fig.add_trace(go.Violin(
            y=sub, name=outcome, fillcolor=color, opacity=0.7,
            line_color="white", box_visible=True, meanline_visible=True,
        ), row=3, col=2)

    fig.update_layout(
        title=dict(
            text="How to Win RuPaul's Drag Race — Analytics Dashboard",
            font=dict(size=18, family="Arial"), x=0.5,
        ),
        height=1200,
        template="plotly_white",
        showlegend=True,
        font=dict(family="Arial", size=11),
    )
    fig.update_yaxes(ticksuffix="%", row=1, col=1)
    fig.update_yaxes(ticksuffix="%", row=2, col=1)

    out_path = OUT_DIR / "dashboard.html"
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    print("Saved: dashboard.html")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  HOW TO WIN RUPAUL'S DRAG RACE — ANALYTICS PIPELINE")
    print("="*60)

    df = load_data()

    print("\nGenerating visualizations...")
    plot_season_overview(df)
    plot_finale_drivers(df)
    plot_winner_profile(df)
    df = plot_archetype_clusters(df)
    plot_lipsync_curse(df)
    plot_geographic_analysis(df)
    plot_age_analysis(df)
    plot_instagram_correlation(df)
    plot_correlation_heatmap(df)
    build_prediction_model(df)
    plot_wins_needed(df)

    print("\nBuilding interactive Plotly dashboard...")
    build_dashboard(df)

    # Save enriched dataset
    df.to_csv(OUT_DIR / "contestant_season_enriched.csv", index=False)

    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    print(f"  Total contestant-seasons:  {len(df):,}")
    print(f"  Seasons covered:           {sorted(df['season_num'].dropna().astype(int).unique())}")
    print(f"  Finalists:                 {df['made_finale'].sum()} ({df['made_finale'].mean()*100:.1f}%)")
    print(f"  Winners:                   {df['winner'].sum()}")
    print(f"  Avg wins (finalists):      {df[df['made_finale']==1]['n_wins'].mean():.2f}")
    print(f"  Avg wins (eliminated):     {df[df['made_finale']==0]['n_wins'].mean():.2f}")
    print(f"\nAll outputs saved to: {OUT_DIR}")
    print("Done.")


if __name__ == "__main__":
    main()
