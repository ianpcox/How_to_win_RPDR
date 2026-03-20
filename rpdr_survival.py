"""
RPDR Survival Analysis — Cox Proportional Hazards Model
How to Win RuPaul's Drag Race — Project Elevate

Models time-to-elimination as a function of cumulative performance metrics
using the Cox Proportional Hazards model (lifelines).

The "event" is elimination. Queens who reach the finale are right-censored
(they survived the full competition without being eliminated in the regular
episodes). This mirrors the classic survival analysis framing used by
Hanna (2013) in the seminal Bad Hessian RPDR survival study.

Covariates:
  - wins_per_episode       (time-invariant, cumulative at end of run)
  - highs_per_episode
  - lows_per_episode
  - lipsyncs_per_episode
  - age_num
  - is_New_York, is_California (geographic dummies)
  - had_any_win            (binary: did the queen ever win?)
  - had_any_lipsync        (binary: did the queen ever lipsync?)

Outputs:
  - 12_survival_km.png          — Kaplan-Meier curves: finalists vs. eliminated
  - 13_cox_hazard_ratios.png    — Forest plot of Cox PH hazard ratios
  - 14_cox_survival_curves.png  — Partial survival curves by archetype
  - 15_schoenfeld_residuals.png — Proportional hazards assumption check
  - survival_summary.txt        — Full Cox model summary
"""

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test
from lifelines.plotting import add_at_risk_counts

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


def load_survival_data() -> pd.DataFrame:
    """
    Load contestant_season.csv and engineer survival analysis columns.

    duration_T : number of episodes competed (time on show)
    event_E    : 1 = eliminated (event occurred), 0 = made finale (right-censored)
    """
    df = pd.read_csv(DATA_DIR / "contestant_season.csv")

    num_cols = ["age_num", "n_wins", "n_highs", "n_lows", "n_lipsyncs",
                "n_episodes", "wins_per_episode", "highs_per_episode",
                "lows_per_episode", "lipsyncs_per_episode",
                "total_top", "total_bottom", "season_num",
                "log_followers_june2017"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in ["made_finale", "winner", "had_any_win", "had_any_lipsync",
              "is_New_York", "is_California", "is_Puerto_Rico"]:
        if c in df.columns:
            df[c] = df[c].astype(float).fillna(0).astype(int)

    # Survival columns
    # duration = episodes competed (minimum 1 to avoid zero-time issues)
    df["duration_T"] = df["n_episodes"].fillna(1).clip(lower=1)
    # event = 1 if eliminated (did NOT make finale), 0 if censored (made finale)
    df["event_E"] = (1 - df["made_finale"]).astype(int)

    print(f"Survival dataset: {len(df)} queens")
    print(f"  Events (eliminations): {df['event_E'].sum()}")
    print(f"  Censored (finalists):  {(df['event_E']==0).sum()}")
    print(f"  Median duration:       {df['duration_T'].median():.0f} episodes")
    return df


def plot_kaplan_meier(df: pd.DataFrame):
    """
    Kaplan-Meier survival curves:
    1. Overall survival
    2. Finalists vs. eliminated (stratified by had_any_win)
    3. Stratified by lip sync experience
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    # ── 1. Overall KM ──────────────────────────────────────────────────────
    kmf = KaplanMeierFitter()
    kmf.fit(df["duration_T"], event_observed=df["event_E"], label="All Queens")
    kmf.plot_survival_function(ax=axes[0], color=RPDR_PINK, lw=2, ci_show=True)
    axes[0].set_title("Overall Survival Function\n(All Queens, Seasons 1–14)")
    axes[0].set_xlabel("Episodes Competed")
    axes[0].set_ylabel("Probability of Survival (Not Eliminated)")
    axes[0].set_ylim(0, 1.05)

    # ── 2. Stratified by any win ────────────────────────────────────────────
    kmf_win  = KaplanMeierFitter()
    kmf_lose = KaplanMeierFitter()

    win_group  = df[df["had_any_win"] == 1]
    lose_group = df[df["had_any_win"] == 0]

    kmf_win.fit(win_group["duration_T"],  event_observed=win_group["event_E"],
                label="Won ≥1 Challenge")
    kmf_lose.fit(lose_group["duration_T"], event_observed=lose_group["event_E"],
                 label="Never Won")

    kmf_win.plot_survival_function(ax=axes[1],  color=RPDR_GOLD,   lw=2, ci_show=True)
    kmf_lose.plot_survival_function(ax=axes[1], color=RPDR_PURPLE, lw=2, ci_show=True)

    # Log-rank test
    lr = logrank_test(win_group["duration_T"],  lose_group["duration_T"],
                      event_observed_A=win_group["event_E"],
                      event_observed_B=lose_group["event_E"])
    axes[1].set_title(f"Survival by Challenge Win History\n(Log-rank p = {lr.p_value:.4f})")
    axes[1].set_xlabel("Episodes Competed")
    axes[1].set_ylabel("Survival Probability")
    axes[1].set_ylim(0, 1.05)
    axes[1].legend(loc="lower left")

    # ── 3. Stratified by lip sync experience ───────────────────────────────
    kmf_nolip = KaplanMeierFitter()
    kmf_lip   = KaplanMeierFitter()

    nolip_group = df[df["had_any_lipsync"] == 0]
    lip_group   = df[df["had_any_lipsync"] == 1]

    kmf_nolip.fit(nolip_group["duration_T"], event_observed=nolip_group["event_E"],
                  label="Never Lip Synced")
    kmf_lip.fit(lip_group["duration_T"],   event_observed=lip_group["event_E"],
                label="Lip Synced ≥1")

    lr2 = logrank_test(nolip_group["duration_T"], lip_group["duration_T"],
                       event_observed_A=nolip_group["event_E"],
                       event_observed_B=lip_group["event_E"])

    kmf_nolip.plot_survival_function(ax=axes[2], color=RPDR_TEAL,   lw=2, ci_show=True)
    kmf_lip.plot_survival_function(ax=axes[2],   color=RPDR_PURPLE, lw=2, ci_show=True)
    axes[2].set_title(f"Survival by Lip Sync History\n(Log-rank p = {lr2.p_value:.4f})")
    axes[2].set_xlabel("Episodes Competed")
    axes[2].set_ylabel("Survival Probability")
    axes[2].set_ylim(0, 1.05)
    axes[2].legend(loc="lower left")

    plt.suptitle("Kaplan-Meier Survival Analysis — RPDR Elimination",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "12_survival_km.png")
    plt.close()
    print("Saved: 12_survival_km.png")

    print(f"\nLog-rank test (won vs. never won):      p = {lr.p_value:.6f}  "
          f"{'***' if lr.p_value < 0.001 else '**' if lr.p_value < 0.01 else '*' if lr.p_value < 0.05 else 'ns'}")
    print(f"Log-rank test (lip sync vs. no lipsync): p = {lr2.p_value:.6f}  "
          f"{'***' if lr2.p_value < 0.001 else '**' if lr2.p_value < 0.01 else '*' if lr2.p_value < 0.05 else 'ns'}")


def fit_cox_model(df: pd.DataFrame) -> CoxPHFitter:
    """
    Fit the Cox Proportional Hazards model.
    Returns the fitted CoxPHFitter object.
    """
    covariates = [
        "wins_per_episode",
        "highs_per_episode",
        "lows_per_episode",
        "lipsyncs_per_episode",
        "age_num",
        "is_New_York",
        "is_California",
        "is_Puerto_Rico",
    ]
    available = [c for c in covariates if c in df.columns]

    df_cox = df[["duration_T", "event_E"] + available].dropna()
    print(f"\nCox PH model: {len(df_cox)} queens, {df_cox['event_E'].sum()} events")

    cph = CoxPHFitter(penalizer=0.1)
    cph.fit(df_cox, duration_col="duration_T", event_col="event_E")

    print("\n" + "="*60)
    print("COX PROPORTIONAL HAZARDS MODEL SUMMARY")
    print("="*60)
    cph.print_summary()

    # Save full summary to text file
    import io
    buf = io.StringIO()
    cph.print_summary(file=buf)
    with open(OUT_DIR / "survival_summary.txt", "w") as f:
        f.write("COX PROPORTIONAL HAZARDS MODEL — RPDR ELIMINATION\n")
        f.write("="*60 + "\n\n")
        f.write(buf.getvalue())
    print("Saved: survival_summary.txt")

    return cph, df_cox


def plot_hazard_ratios(cph: CoxPHFitter):
    """Forest plot of hazard ratios with 95% CIs."""
    summary = cph.summary.copy()
    summary = summary.sort_values("exp(coef)")

    # Friendly labels
    label_map = {
        "wins_per_episode":      "Win Rate (wins/episode)",
        "highs_per_episode":     "High Rate (highs/episode)",
        "lows_per_episode":      "Low Rate (lows/episode)",
        "lipsyncs_per_episode":  "Lip Sync Rate (lipsyncs/episode)",
        "age_num":               "Age",
        "is_New_York":           "From New York",
        "is_California":         "From California",
        "is_Puerto_Rico":        "From Puerto Rico",
    }
    summary.index = [label_map.get(i, i) for i in summary.index]

    fig, ax = plt.subplots(figsize=(10, 6))

    y_pos = range(len(summary))
    hr    = summary["exp(coef)"]
    ci_lo = summary["exp(coef) lower 95%"]
    ci_hi = summary["exp(coef) upper 95%"]
    pvals = summary["p"]

    colors = [RPDR_PURPLE if v < 1 else RPDR_PINK for v in hr]

    ax.scatter(hr, y_pos, color=colors, s=80, zorder=3)
    for i, (lo, hi, y) in enumerate(zip(ci_lo, ci_hi, y_pos)):
        ax.plot([lo, hi], [y, y], color=colors[i], lw=2, alpha=0.7)

    ax.axvline(1.0, color="black", linestyle="--", lw=1.5, label="HR = 1.0 (no effect)")
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(summary.index, fontsize=10)
    ax.set_xlabel("Hazard Ratio (95% CI)")
    ax.set_title("Cox PH Model — Hazard Ratios for Elimination\n"
                 "(HR < 1 = protective, HR > 1 = increased elimination risk)",
                 fontsize=11, fontweight="bold")

    # Annotate p-values
    for i, (hr_val, p, y) in enumerate(zip(hr, pvals, y_pos)):
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        if sig:
            ax.text(ci_hi.iloc[i] + 0.02, y, sig, va="center", fontsize=10,
                    color="darkred", fontweight="bold")

    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "13_cox_hazard_ratios.png")
    plt.close()
    print("Saved: 13_cox_hazard_ratios.png")


def plot_survival_curves_by_profile(cph: CoxPHFitter, df_cox: pd.DataFrame):
    """
    Partial survival curves for four hypothetical queen profiles:
    1. Challenge Dominator: high wins, low lipsyncs
    2. Consistent Performer: moderate wins, some highs
    3. Safe Player: no wins, no lipsyncs, no highs
    4. Bottom Feeder: no wins, high lipsyncs, many lows
    """
    # Build profile dataframes using the mean of each covariate
    means = df_cox.drop(columns=["duration_T", "event_E"]).mean()

    profiles = {
        "Challenge Dominator":   means.copy(),
        "Consistent Performer":  means.copy(),
        "Safe Player":           means.copy(),
        "Bottom Feeder":         means.copy(),
    }

    # Dominator: high wins, low everything else
    profiles["Challenge Dominator"]["wins_per_episode"]     = df_cox["wins_per_episode"].quantile(0.85)
    profiles["Challenge Dominator"]["highs_per_episode"]    = df_cox["highs_per_episode"].quantile(0.70)
    profiles["Challenge Dominator"]["lows_per_episode"]     = df_cox["lows_per_episode"].quantile(0.15)
    profiles["Challenge Dominator"]["lipsyncs_per_episode"] = df_cox["lipsyncs_per_episode"].quantile(0.10)

    # Consistent: moderate wins, moderate highs
    profiles["Consistent Performer"]["wins_per_episode"]     = df_cox["wins_per_episode"].quantile(0.55)
    profiles["Consistent Performer"]["highs_per_episode"]    = df_cox["highs_per_episode"].quantile(0.60)
    profiles["Consistent Performer"]["lows_per_episode"]     = df_cox["lows_per_episode"].quantile(0.35)
    profiles["Consistent Performer"]["lipsyncs_per_episode"] = df_cox["lipsyncs_per_episode"].quantile(0.25)

    # Safe: no wins, no lows, no lipsyncs
    profiles["Safe Player"]["wins_per_episode"]     = 0.0
    profiles["Safe Player"]["highs_per_episode"]    = df_cox["highs_per_episode"].quantile(0.30)
    profiles["Safe Player"]["lows_per_episode"]     = df_cox["lows_per_episode"].quantile(0.30)
    profiles["Safe Player"]["lipsyncs_per_episode"] = 0.0

    # Bottom: no wins, many lows, many lipsyncs
    profiles["Bottom Feeder"]["wins_per_episode"]     = 0.0
    profiles["Bottom Feeder"]["highs_per_episode"]    = df_cox["highs_per_episode"].quantile(0.10)
    profiles["Bottom Feeder"]["lows_per_episode"]     = df_cox["lows_per_episode"].quantile(0.85)
    profiles["Bottom Feeder"]["lipsyncs_per_episode"] = df_cox["lipsyncs_per_episode"].quantile(0.85)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [RPDR_GOLD, RPDR_TEAL, RPDR_PINK, RPDR_PURPLE]
    styles = ["-", "--", "-.", ":"]

    for (name, profile), color, style in zip(profiles.items(), colors, styles):
        profile_df = pd.DataFrame([profile])
        sf = cph.predict_survival_function(profile_df)
        ax.plot(sf.index, sf.values.flatten(), label=name,
                color=color, lw=2.5, linestyle=style)

    ax.axhline(0.5, color="gray", linestyle=":", lw=1, alpha=0.7, label="50% survival")
    ax.set_xlabel("Episodes Competed")
    ax.set_ylabel("Predicted Survival Probability (Not Eliminated)")
    ax.set_title("Cox PH Predicted Survival Curves by Performance Archetype",
                 fontsize=11, fontweight="bold")
    ax.legend(loc="lower left")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "14_cox_survival_curves.png")
    plt.close()
    print("Saved: 14_cox_survival_curves.png")


def plot_schoenfeld_residuals(cph: CoxPHFitter, df_cox: pd.DataFrame):
    """
    Check the proportional hazards assumption via scaled Schoenfeld residuals.
    A flat line (no trend over time) supports the PH assumption.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    try:
        cph.check_assumptions(df_cox, p_value_threshold=0.05, show_plots=False)
        residuals = cph.compute_residuals(df_cox, kind="scaled_schoenfeld")
        # Plot first two most important covariates
        cols = [c for c in residuals.columns if c in
                ["wins_per_episode", "lipsyncs_per_episode"]][:2]
        for col in cols:
            ax.scatter(df_cox["duration_T"], residuals[col],
                       alpha=0.5, s=30, label=col)
        ax.axhline(0, color="black", lw=1, linestyle="--")
        ax.set_xlabel("Duration (Episodes)")
        ax.set_ylabel("Scaled Schoenfeld Residuals")
        ax.set_title("Proportional Hazards Assumption Check\n"
                     "(Flat trend = PH assumption holds)",
                     fontsize=11, fontweight="bold")
        ax.legend()
    except Exception as e:
        ax.text(0.5, 0.5, f"Schoenfeld residuals\nnot available:\n{e}",
                ha="center", va="center", transform=ax.transAxes)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "15_schoenfeld_residuals.png")
    plt.close()
    print("Saved: 15_schoenfeld_residuals.png")


def main():
    print("\n" + "="*60)
    print("  RPDR SURVIVAL ANALYSIS — COX PROPORTIONAL HAZARDS")
    print("="*60)

    df = load_survival_data()

    print("\nGenerating Kaplan-Meier curves...")
    plot_kaplan_meier(df)

    print("\nFitting Cox Proportional Hazards model...")
    cph, df_cox = fit_cox_model(df)

    print("\nGenerating hazard ratio forest plot...")
    plot_hazard_ratios(cph)

    print("\nGenerating partial survival curves by archetype...")
    plot_survival_curves_by_profile(cph, df_cox)

    print("\nChecking proportional hazards assumption...")
    plot_schoenfeld_residuals(cph, df_cox)

    print("\n" + "="*60)
    print("SURVIVAL ANALYSIS COMPLETE")
    print(f"  Concordance index (C-statistic): {cph.concordance_index_:.3f}")
    print(f"  Log-likelihood ratio test p:     {cph.log_likelihood_ratio_test().p_value:.6f}")
    print("="*60)


if __name__ == "__main__":
    main()
