# app.py — FINAL WITH DRAG-AND-DROP REORDERING
import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items

st.set_page_config(page_title="ENT Applicant Ranking", layout="centered")
st.title("ENT Applicant Ranking")

# ——— Upload (disappears after load) ———
# ——— ULTRA-ROBUST UPLOAD (handles any Total Score / Complete? variation) ———
if "df" not in st.session_state:
    st.caption("Upload the latest REDCap CSV export to begin")
    uploaded_file = st.file_uploader("", type="csv")
    if uploaded_file is None:
        st.stop()

    df_raw = pd.read_csv(uploaded_file)

    # 1. Find the "Complete?" column (any case, any variation)
    complete_col = None
    for col in df_raw.columns:
        if 'complete' in str(col).lower():
            complete_col = col
            break
    if complete_col is not None:
        if df_raw[complete_col].dtype in ['int64', 'float64']:
            df_raw = df_raw[df_raw[complete_col] == 2].copy()
        else:
            df_raw = df_raw[df_raw[complete_col].astype(str).str.contains('complete', case=False, na=False)].copy()
    else:
        st.warning("No completion column found — showing all rows")

    # 2. Find the Total Score column (case-insensitive, spaces/underscores)
    total_col = None
    for col in df_raw.columns:
        if 'total' in str(col).lower() and 'score' in str(col).lower():
            total_col = col
            break
    if total_col is None:
        st.error("Could not find a 'total_score' column. Check your CSV.")
        st.stop()
    
    df_raw["total_score"] = pd.to_numeric(df_raw[total_col], errors="coerce")

    # 3. Standardize Applicant Name column
    applicant_col = next((c for c in df_raw.columns if 'applicant' in str(c).lower()), None)
    if applicant_col and applicant_col != "Applicant Name":
        df_raw = df_raw.rename(columns={applicant_col: "Applicant Name"})

    st.session_state.df = df_raw
    st.success(f"Loaded {len(df_raw)} completed evaluations for {df_raw['Applicant Name'].nunique()} applicants")
    st.rerun()

df = st.session_state.df
st.caption(f"Updated {pd.Timestamp('now').strftime('%B %d, %Y · %I:%M %p')}  |  {len(df)} evaluations")

# Main scored ranking
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

st.write(f"### Current Scored Rank List — {len(ranking)} applicants")
st.dataframe(ranking, use_container_width=True, hide_index=True)

# ——— Dynamic per-question detail view (still fully automatic) ———
st.write("#### Select applicant for per-question breakdown")
selected = st.selectbox("", options=ranking["Applicant"].tolist(), index=0, key="detail")
details = df[df["Applicant Name"] == selected].copy()

known_non_likert = ["Record ID", "Repeat Instrument", "Repeat Instance", "Survey Identifier",
                    "Survey Timestamp", "total_score", "Complete?", "Applicant Name"]

likert_questions = []
for col in details.columns:
    if col not in known_non_likert:
        try:
            details[col] = pd.to_numeric(details[col], errors="coerce")
            if details[col].notna().any():
                likert_questions.append(col)
        except:
            pass

if likert_questions:
    stats = details[likert_questions].agg(['mean', 'min', 'max']).round(1).T
    def format_row(row):
        if pd.isna(row['min']) or pd.isna(row['max']):
            return f"{row['mean']:.1f}  (—)"
        else:
            return f"{row['mean']:.1f}  ({int(row['min'])}–{int(row['max'])})"
    stats['display'] = stats.apply(format_row, axis=1)
    avg_table = pd.DataFrame({
        "Question": [q.split("?")[0] + ("?" if "?" in q else "") for q in likert_questions],
        "Average ± Range": stats['display'].values
    })
    st.write(f"**{selected}** — {details.shape[0]} evaluations")
    st.dataframe(avg_table, hide_index=True, use_container_width=True)

# ——— DRAG-AND-DROP REORDERING (height fixed) ———
st.markdown("### Final Rank Order (drag to reorder during meeting)")

# Initialize with scored order
if "final_order" not in st.session_state:
    st.session_state.final_order = ranking["Applicant"].tolist()

# The sortable component (no height — auto-sizes)
ordered = sort_items(st.session_state.final_order, key="sortable_applicants")

# Update session state when reordered
if ordered != st.session_state.final_order:
    st.session_state.final_order = ordered
    st.rerun()

# Show numbered list (with optional styling)
st.markdown("""
<style>
    .sortable-item {
        font-size: 18px;
        padding: 10px;
        background-color: #f0f2f6;
        margin: 2px 0;
        border-radius: 4px;
        color: #111827;               /* NEW: text color */
    }
    .sortable-item strong {
        color: #111827;               /* NEW: index number color */
    }
</style>
""", unsafe_allow_html=True)

for i, name in enumerate(st.session_state.final_order, 1):
    st.markdown(f'<div class="sortable-item"><strong>{i}.</strong> {name}</div>', unsafe_allow_html=True)

# Download buttons
col1, col2 = st.columns(2)
with col1:
    scored_csv = ranking.to_csv(index=False).encode()
    st.download_button("Download scored ranking", scored_csv,
                       f"ENT_Scored_{pd.Timestamp('today').strftime('%Y-%m-%d')}.csv")
with col2:
    final_df = pd.DataFrame({"Final Rank": range(1, len(st.session_state.final_order)+1),
                             "Applicant": st.session_state.final_order})
    final_csv = final_df.to_csv(index=False).encode()
    st.download_button("Download FINAL adjusted ranking →",
                       final_csv,
                       f"ENT_FINAL_Ranking_{pd.Timestamp('today').strftime('%Y-%m-%d')}.csv",
                       mime="text/csv")
