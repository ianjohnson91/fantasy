import streamlit as st
import sqlite3
import pandas as pd
import numpy as np

DB_FILE = "fantasy.db"

from io import BytesIO

# =====================================================
# LOAD STANDINGS
# =====================================================
def load_data():
    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query("""
        SELECT
            season,
            manager_name,
            manager_guid,
            team_name,
            rank,
            wins,
            losses,
            ties,
            points_for,
            points_against
        FROM standings
    """, conn)

    conn.close()

    df["points_for"] = pd.to_numeric(
        df["points_for"],
        errors="coerce"
    )

    df["points_against"] = pd.to_numeric(
        df["points_against"],
        errors="coerce"
    )

    df["wins"] = pd.to_numeric(
        df["wins"],
        errors="coerce"
    )

    df["losses"] = pd.to_numeric(
        df["losses"],
        errors="coerce"
    )

    df["rank"] = pd.to_numeric(
        df["rank"],
        errors="coerce"
    )

    return df

# =====================================================
# LOAD ELO
# =====================================================

def load_elo():

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query("""
        SELECT *
        FROM manager_elo
    """, conn)

    conn.close()

    return df


# =====================================================
# LOAD MATCHUPS
# =====================================================
def load_matchups():

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query("""
        SELECT
            season,
            week,
            manager_name,
            opponent_manager_name,
            team_points,
            opponent_points,
            margin,
            result
        FROM matchups
    """, conn)

    conn.close()

    df["team_points"] = pd.to_numeric(
        df["team_points"],
        errors="coerce"
    )

    df["opponent_points"] = pd.to_numeric(
        df["opponent_points"],
        errors="coerce"
    )

    return df

# =====================================================
# Load Draft Analysis
# =====================================================

def load_draft_data():
    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query("""
        SELECT
            season,
            draft_position,
            rank,
            team_name
        FROM standings
        WHERE draft_position IS NOT NULL
    """, conn)

    conn.close()

    df["draft_position"] = pd.to_numeric(df["draft_position"], errors="coerce")
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

    df["championship"] = df["rank"].apply(lambda x: 1 if x == 1 else 0)

    champ_summary = df.groupby("draft_position").agg(
        championships=("championship", "sum"),
        seasons=("championship", "count"),
    ).reset_index()

    champ_summary["champ_rate"] = (
        champ_summary["championships"] / champ_summary["seasons"]
    )

    return df, champ_summary

# =====================================================
# Load Draft Analysis by Slot
# =====================================================

def draft_slot_summary(df, champ_summary):

    summary = df.groupby("draft_position").agg(
        avg_finish=("rank", "mean"),
        best_finish=("rank", "min"),
        worst_finish=("rank", "max"),
        seasons=("rank", "count")
    ).reset_index()

    summary = summary.sort_values("avg_finish")

    combined = summary.merge(
        champ_summary,
        on="draft_position",
        how="left"
    )

    combined["championships"] = combined["championships"].fillna(0)
    combined["champ_rate"] = combined["champ_rate"].fillna(0)

    return combined

# =====================================================
# EXPECTED WINS / LUCK INDEX
# =====================================================
def compute_expected_wins(season_df):

    scores = season_df["points_for"].values

    expected_wins = []

    for _, row in season_df.iterrows():

        pf = row["points_for"]

        win_prob = np.mean(
            pf > scores
        )

        expected_wins.append(
            win_prob * (len(season_df) - 1)
        )

    season_df = season_df.copy()

    season_df["expected_wins"] = expected_wins

    season_df["luck_index"] = (
        season_df["wins"] -
        season_df["expected_wins"]
    )

    return season_df
# =====================================================
# Excel File
# =====================================================
def to_excel():
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        # Standings (full)
        df.to_excel(writer, sheet_name="Standings_All", index=False)

        # Season filtered standings
        season_df.to_excel(writer, sheet_name="Season_Standings", index=False)

        # Luck index
        luck_table.to_excel(writer, sheet_name="Luck_Index", index=False)

        # Competitiveness
        competitiveness.to_excel(writer, sheet_name="Competitiveness", index=False)

        # All-time summary
        summary.to_excel(writer, sheet_name="All_Time_Summary", index=False)

        # Trends
        summary_df.to_excel(writer, sheet_name="League_Trends")

        # Matchup analytics
        winning_scores.to_frame().to_excel(writer, sheet_name="Winning_Scores")
        margin_by_season.to_frame().to_excel(writer, sheet_name="Margin_By_Season")

        # H2H
        h2h.to_excel(writer, sheet_name="H2H_Raw", index=False)

        # Rivalry view (manager-specific)
        view.to_excel(writer, sheet_name="Rivalry_View", index=False)

    output.seek(0)
    return output



# =====================================================
# LOAD DATA
# =====================================================
df = load_data()
matchups = load_matchups()

st.title("🏈 Fantasy League Dashboard")

# =====================================================
# SIDEBAR
# =====================================================
seasons = sorted(
    df["season"].unique(),
    reverse=True
)

selected_season = st.sidebar.selectbox(
    "Season",
    seasons
)

managers = sorted(
    df["manager_name"].dropna().unique()
)

selected_manager = st.sidebar.selectbox(
    "Manager",
    ["All"] + list(managers)
)

# =====================================================
# FILTERED SEASON
# =====================================================
season_df = df[
    df["season"] == selected_season
]

season_df = compute_expected_wins(
    season_df
)

if selected_manager != "All":

    filtered = season_df[
        season_df["manager_name"] ==
        selected_manager
    ]

else:

    filtered = season_df


# =====================================================
# STANDINGS
# =====================================================
st.subheader(
    f"Standings - {selected_season}"
)

st.dataframe(
    filtered.sort_values("rank")[
        [
            "rank",
            "team_name",
            "manager_name",
            "wins",
            "losses",
            "expected_wins",
            "luck_index",
            "points_for"
        ]
    ]
)

# =====================================================
# LUCK INDEX
# =====================================================
st.subheader(
    "🍀 Luck Index"
)

luck_table = season_df.sort_values(
    "luck_index",
    ascending=False
)[
    [
        "team_name",
        "manager_name",
        "wins",
        "expected_wins",
        "luck_index"
    ]
]

st.dataframe(luck_table)

# =====================================================
# COMPETITIVENESS
# =====================================================
st.subheader(
    "📊 Season Competitiveness"
)

competitiveness = df.groupby(
    "season"
).agg(
    std_points=("points_for", "std"),
    avg_points=("points_for", "mean"),
    win_parity=("wins", "std")
).reset_index()

competitiveness[
    "competitiveness_score"
] = (
    1 /
    (
        competitiveness["std_points"]
        + 0.000001
    )
)

most_competitive = (
    competitiveness
    .sort_values(
        "competitiveness_score",
        ascending=False
    )
    .iloc[0]
)

st.dataframe(
    competitiveness.sort_values(
        "season",
        ascending=False
    )
)

st.success(
    f"Most Competitive Season: "
    f"{int(most_competitive['season'])}"
)

# =====================================================
# FRANCHISE HISTORY
# =====================================================
st.subheader(
    "Franchise History"
)

if selected_manager != "All":

    history = (
        df[
            df["manager_name"] ==
            selected_manager
        ]
        .sort_values("season")
    )

    st.write("Rank History")
    st.line_chart(
        history.set_index("season")["rank"]
    )

    st.write("Points For")
    st.line_chart(
        history.set_index("season")[
            "points_for"
        ]
    )

else:

    st.write(
        "Select a manager to view "
        "historical charts."
    )

# =====================================================
# ALL-TIME SUMMARY
# =====================================================
st.subheader(
    "All-Time Summary"
)

summary = (
    df.groupby("manager_name")
    .agg(
        seasons=("season", "count"),
        total_wins=("wins", "sum"),
        avg_rank=("rank", "mean"),
        best_rank=("rank", "min"),
        total_points=("points_for", "sum")
    )
    .reset_index()
)

st.dataframe(
    summary.sort_values(
        "total_wins",
        ascending=False
    )
)

# =====================================================
# LEAGUE-WIDE MATCHUP ANALYTICS
# =====================================================
st.subheader(
    "📈 Average Winning Score by Year"
)

winning_scores = (
    matchups[
        matchups["result"] == "W"
    ]
    .groupby("season")[
        "team_points"
    ]
    .mean()
)

st.line_chart(
    winning_scores.rename(
        "Avg Winning Score"
    )
)

# =====================================================
# MARGIN OF VICTORY
# =====================================================
st.subheader(
    "⚔️ Competitive Balance"
)

margin_by_season = (
    matchups.groupby("season")[
        "margin"
    ]
    .mean()
)

st.line_chart(
    margin_by_season.rename(
        "Avg Margin of Victory"
    )
)

most_competitive_margin = (
    margin_by_season.idxmin()
)

least_competitive_margin = (
    margin_by_season.idxmax()
)

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Most Competitive Season",
        int(most_competitive_margin),
        f"{margin_by_season[most_competitive_margin]:.2f}"
    )

with col2:

    st.metric(
        "Least Competitive Season",
        int(least_competitive_margin),
        f"{margin_by_season[least_competitive_margin]:.2f}"
    )

# =====================================================
# LEAGUE TRENDS TABLE
# =====================================================
st.subheader(
    "League Trends Summary"
)

summary_df = pd.DataFrame({
    "Avg Winning Score": winning_scores,
    "Avg Margin Of Victory": margin_by_season
}).sort_index()

# =========================================================
# 🥊 MANAGER RIVALRIES DASHBOARD
# =========================================================

st.subheader("🥊 Manager Rivalries")

def load_h2h():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("""
        SELECT
            manager_a,
            manager_b,
            games,
            a_wins,
            b_wins,
            ties,
            a_win_pct,
            b_win_pct
        FROM manager_h2h
    """, conn)
    conn.close()
    return df


h2h = load_h2h()

all_managers = sorted(
    set(h2h["manager_a"]).union(set(h2h["manager_b"]))
)

h2h_manager = st.selectbox("Select Manager", all_managers)

filtered = h2h[
    (h2h["manager_a"] == h2h_manager) |
    (h2h["manager_b"] == h2h_manager)
].copy()

# 🚨 SAFETY CHECK
if filtered.empty:
    st.warning("No H2H data found for this manager.")
    st.stop()


def normalize(row):
    if row["manager_a"] == h2h_manager:
        return {
            "opponent": row["manager_b"],
            "games": row["games"],
            "wins": row["a_wins"],
            "losses": row["b_wins"],
            "ties": row["ties"],
            "win_pct": row["a_win_pct"]
        }
    else:
        return {
            "opponent": row["manager_a"],
            "games": row["games"],
            "wins": row["b_wins"],
            "losses": row["a_wins"],
            "ties": row["ties"],
            "win_pct": row["b_win_pct"]
        }


view = pd.DataFrame([normalize(r) for _, r in filtered.iterrows()])

# 🚨 FINAL SAFETY CHECK
if "win_pct" not in view.columns:
    st.error("win_pct column missing — check H2H data generation")
    st.write(view)
    st.stop()

view = view.sort_values(["win_pct", "games"], ascending=[False, False])

st.dataframe(view)

best = view.iloc[0]
worst = view.iloc[-1]

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Easiest Rivalry",
        best["opponent"],
        f"{best['wins']}-{best['losses']} ({best['win_pct']:.2%})"
    )

with col2:
    st.metric(
        "Hardest Rivalry",
        worst["opponent"],
        f"{worst['wins']}-{worst['losses']} ({worst['win_pct']:.2%})"
    )

st.bar_chart(view.set_index("opponent")["win_pct"])



# =====================================================
# HIGHEST SCORES EVER
# =====================================================

st.subheader("🔥 Highest Scores Ever")

highest_scores = (
    matchups[
        [
            "season",
            "week",
            "manager_name",
            "team_points"
        ]
    ]
    .sort_values(
        "team_points",
        ascending=False
    )
    .head(10)
)

st.dataframe(highest_scores)

# =====================================================
# LOWEST SCORES EVER
# =====================================================

st.subheader("🥶 Lowest Scores Ever")

lowest_scores = (
    matchups[
        ["season", "manager_name", "team_points"]
    ]
    .sort_values(
        "team_points",
        ascending=True
    )
    .head(10)
)

st.dataframe(lowest_scores)

# =====================================================
# BAD BEATS
# =====================================================

st.subheader("💔 Bad Beats")

closest_games = (
    matchups
    .sort_values("margin")
    .drop_duplicates(
        subset=[
            "season",
            "week",
            "margin"
        ]
    )
    .head(10)
)


st.write("Top 10 Closest Matchups")

st.dataframe(
    closest_games[
        [
            "season",
            "week",
            "manager_name",
            "opponent_manager_name",
            "team_points",
            "opponent_points",
            "margin"
        ]
    ]
)
bad_beats = (
    matchups[
        (matchups["result"] == "L")
        &
        (matchups["margin"] < 1)
    ]
    .groupby("manager_name")
    .size()
    .reset_index(name="bad_beats")
)

st.subheader("Losses by Less Than 1 Point")

st.dataframe(
    bad_beats.sort_values(
        "bad_beats",
        ascending=False
    )
)

# =====================================================
# DYNASTY POWER RANKINGS
# =====================================================

st.subheader("👑 Dynasty Power Rankings")
st.write("1st = 100, 2nd= 60, 3rd= 40, 4th= 25, 5th= 10, 6th= 5, Last= -10, Most Pts= 10, Wins= 1")

dynasty = df.copy()

# Base score from wins
dynasty["dynasty_points"] = dynasty["wins"] * 1

# Finishing bonuses
dynasty.loc[dynasty["rank"] == 1, "dynasty_points"] += 100
dynasty.loc[dynasty["rank"] == 2, "dynasty_points"] += 60
dynasty.loc[dynasty["rank"] == 3, "dynasty_points"] += 40
dynasty.loc[dynasty["rank"] == 4, "dynasty_points"] += 25
dynasty.loc[dynasty["rank"] == 5, "dynasty_points"] += 10
dynasty.loc[dynasty["rank"] == 6, "dynasty_points"] += 5

# Last-place penalty
max_rank = dynasty.groupby("season")["rank"].transform("max")

dynasty.loc[
    dynasty["rank"] == max_rank,
    "dynasty_points"
] -= 10

# Most-points bonus
for season in dynasty["season"].unique():

    season_df = dynasty[dynasty["season"] == season]

    idx = season_df["points_for"].idxmax()

    dynasty.loc[idx, "dynasty_points"] += 10

# Aggregate manager scores
dynasty_rankings = (
    dynasty.groupby("manager_name")
    .agg(
        dynasty_points=("dynasty_points", "sum"),
        championships=("rank", lambda x: (x == 1).sum()),
        second=("rank", lambda x: (x == 2).sum()),
        third=("rank", lambda x: (x == 3).sum()),
        seasons=("season", "count"),
        wins=("wins", "sum"),
        points_for=("points_for", "sum")
    )
    .reset_index()
)

dynasty_rankings = dynasty_rankings.sort_values(
    "dynasty_points",
    ascending=False
)

dynasty_rankings["Power Rank"] = range(
    1,
    len(dynasty_rankings) + 1
)

st.dataframe(
    dynasty_rankings[
        [
            "Power Rank",
            "manager_name",
            "dynasty_points",
            "championships",
            "second",
            "third",
            "wins",
            "seasons"
        ]
    ]
)



col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Dynasty King",
        dynasty_rankings.iloc[0]["manager_name"]
    )

with col2:
    st.metric(
        "Most Championships",
        dynasty_rankings.sort_values(
            "championships",
            ascending=False
        ).iloc[0]["manager_name"]
    )

with col3:
    st.metric(
        "Most Career Wins",
        dynasty_rankings.sort_values(
            "wins",
            ascending=False
        ).iloc[0]["manager_name"]
    )

# =====================================================
# ELO
# =====================================================

st.subheader("🔥 Manager Elo Ratings")

elo = load_elo()

elo["Rank"] = range(
    1,
    len(elo) + 1
)

st.dataframe(
    elo[
        [
            "Rank",
            "manager_name",
            "elo"
        ]
    ]
)

st.metric(
    "Highest Rated Manager",
    elo.iloc[0]["manager_name"],
    f"{elo.iloc[0]['elo']:.0f}"
)

chart = elo.head(10).set_index(
    "manager_name"
)
# =====================================================
# Draft Slot Analysis
# =====================================================

st.title("📊 Draft Slot Value Analysis")

df, champ_summary = load_draft_data()
combined = draft_slot_summary(df, champ_summary)

# Main table
st.subheader("📊 Full Draft Slot Value Table")
st.dataframe(combined.sort_values("avg_finish"))

# Chart
st.subheader("📉 Avg Finish by Draft Slot (lower = better)")
st.bar_chart(
    combined.set_index("draft_position")["avg_finish"]
)

# Elite finishes
df["elite_finish"] = df["rank"].apply(lambda x: 1 if x <= 3 else 0)
df["championship"] = df["rank"].apply(lambda x: 1 if x == 1 else 0)

elite = df.groupby("draft_position").agg(
    elite_rate=("elite_finish", "mean"),
    champ_rate=("championship", "mean")
).reset_index()

st.subheader("🔥 Elite Finish Rate (Top 3)")
st.dataframe(elite.sort_values("elite_rate", ascending=False))

# Best slot
best_slot = combined.sort_values("avg_finish").iloc[0]

st.success(
    f"🏆 Best historical draft slot: {int(best_slot['draft_position'])} "
    f"(Avg Finish: {best_slot['avg_finish']:.2f})"
)


# =====================================================
# EXPORT TO EXCEL
# =====================================================

st.subheader("📤 Export Full Dataset")

excel_data = to_excel()

st.download_button(
    label="📥 Download Full Excel Report",
    data=excel_data,
    file_name="fantasy_league_dashboard.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
