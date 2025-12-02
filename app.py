# app.py — FINAL CLINICAL VERSION (clean, no clutter)
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Resident Interviews", layout="centered")
st.title("Resident Interviews")

# ——— Upload (disappears after successful load) ———
if "df" not in st.session_state:
    st.caption("Upload the latest REDCap CSV to begin")
    uploaded_file = st.file_uploader("", type="csv")  # empty label = minimal
    if uploaded_file is None:
        st.stop()
    # Load once and store in session state
    df_raw = pd.read_csv(uploaded_file)
    df_raw = df_raw[df_raw["Complete?"] == "Complete"].copy()
    df_raw["total_score"] = pd.to_numeric(df_raw["Total score"], errors="coerce")
    st.session_state.df = df_raw
    st.success("Data loaded — refresh page if you have a newer export")
    st.rerun()

# ——— From here on: data already loaded, no uploader shown ———
df = st.session_state.df
st.caption(f"Updated {pd.Timestamp('now').strftime('%B %d, %Y · %I:%M %p')}  |  {len(df)} evaluations")

# Main ranking
ranking = (
    df.groupby("Applicant Name", as_index=False)
      .agg(n_evals=("total_score", "count"),
           avg_score=("total_score", "mean"))
      .round(1)
      .sort_values("avg_score", ascending=False)
      .reset_index(drop=True)
)
ranking.insert(0, "Rank", range(1, len(ranking) + 1))
ranking = ranking[["Rank", "Applicant Name", "avg_score", "n_evals"]]
ranking.columns = ["Rank", "Applicant", "Average Score", "# Evaluations"]

st.write(f"### Current Rank List — {len(ranking)} applicants")
st.dataframe(ranking, use_container_width=True, hide_index=True)

# ——— DETAIL VIEW WITH RANGE (now NaN-safe) ———
st.write("#### Select applicant for per-question breakdown")
selected = st.selectbox("", options=ranking["Applicant"].tolist(), index=0, key="detail")

details = df[df["Applicant Name"] == selected].copy()

likert_questions = [
    "How would you rate their communication skills?",
    "How well did the applicant respond to the behavioral interview question?",
    "How would you rate the applicant's resilience?",
    "How would you rate the applicant's likelihood to thrive in UH's training environment?",
    "This applicant fulfills a strategic need in the department (e.g. leadership, strong clinical care, research, education)"
]

for q in likert_questions:
    details[q] = pd.to_numeric(details[q], errors="coerce")

# Calculate stats safely
stats = details[likert_questions].agg(['mean', 'min', 'max']).round(1).T

def format_row(row):
    if pd.isna(row['min']) or pd.isna(row['max']):
        return f"{row['mean']:.1f}  (—)"          # no one answered this question
    else:
        return f"{row['mean']:.1f}  ({int(row['min'])}–{int(row['max'])})"

stats['display'] = stats.apply(format_row, axis=1)

avg_table = pd.DataFrame({
    "Question": [q.split("?")[0] + "?" for q in likert_questions],
    "Average ± Range": stats['display'].values
}).reset_index(drop=True)

st.write(f"**{selected}** — {details.shape[0]} evaluations")
st.dataframe(avg_table, hide_index=True, use_container_width=True)
# Download button (always visible)
csv = ranking.to_csv(index=False).encode()
st.download_button(
    "Download full ranking CSV",
    data=csv,
    file_name=f"ENT_Ranking_{pd.Timestamp('today').strftime('%Y-%m-%d')}.csv",
    mime="text/csv"
)
