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
# LOAD MATCHUPS
# =====================================================
def load_matchups():

    conn = sqlite3.connect(DB_FILE)

    df = pd.read_sql_query("""
        SELECT
            season,
            team_points,
            opponent_points,
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

    df["margin"] = abs(
        df["team_points"] -
        df["opponent_points"]
    )

    return df


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

st.subheader("📤 Export Full Dataset")

excel_data = to_excel()

st.download_button(
    label="📥 Download Full Excel Report",
    data=excel_data,
    file_name="fantasy_league_dashboard.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)