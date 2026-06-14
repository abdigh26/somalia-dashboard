"""
Somali OSINT Brief — Interactive Dashboard
Reads Somalia security incidents data from Google Drive, displays
interactive trends, maps, and breakdowns.
"""

import io
import json
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Somali OSINT Brief — Dashboard",
    page_icon="🇸🇴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme: Dark intelligence-brief aesthetic ─────────────────────────────────
ACCENT = "#c8a96e"
BG = "#0a0a0c"
BG_CARD = "#111116"
BG_RAISED = "#17171e"
BORDER = "#222230"
TEXT = "#e2e2e8"
TEXT_DIM = "#7a7a90"

st.markdown(f"""
<style>
    .stApp {{
        background-color: {BG};
        color: {TEXT};
    }}
    section[data-testid="stSidebar"] {{
        background-color: {BG_CARD};
        border-right: 1px solid {BORDER};
    }}
    h1, h2, h3 {{
        font-family: 'Georgia', serif;
        color: {TEXT} !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {ACCENT} !important;
        font-family: 'Georgia', serif;
        font-size: 1.4rem !important;
        overflow: visible !important;
        white-space: nowrap !important;
    }}
    [data-testid="stMetric"] {{
        overflow: visible !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {TEXT_DIM} !important;
        font-size: 0.7rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }}
    .block-container {{
        padding-top: 2rem;
    }}
    div[data-baseweb="select"] {{
        background-color: {BG_RAISED};
    }}
    .eyebrow {{
        font-family: monospace;
        font-size: 0.7rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: {ACCENT};
        margin-bottom: 0.5rem;
    }}
    @media (max-width: 640px) {{
        [data-testid="stMetricValue"] {{
            font-size: 1.1rem !important;
        }}
        [data-testid="column"] {{
            min-width: 45% !important;
            flex: 1 1 45% !important;
        }}
    }}
</style>
""", unsafe_allow_html=True)

def base_layout(**overrides):
    """Return a dict of base layout settings, with overrides applied."""
    layout = dict(
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_CARD,
        font=dict(color=TEXT, family="Georgia, serif"),
        colorway=[ACCENT, "#8a9bd4", "#d47a7a", "#7ad4a0", "#d4b87a", "#a07ad4"],
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=20, t=50, b=40),
    )
    layout.update(overrides)
    return layout


# ── Data loading ───────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)  # refresh hourly
def load_data():
    sa_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds)

    file_id = st.secrets["GDRIVE_FILE_ID"]
    req = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    buf.seek(0)

    df = pd.read_excel(buf, dtype=str)
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df["FATALITY"] = pd.to_numeric(df["FATALITY"], errors="coerce").fillna(0)
    df["INJURY"] = pd.to_numeric(df["INJURY"], errors="coerce").fillna(0)
    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")
    df = df.dropna(subset=["DATE"])
    return df


# ── Header ────────────────────────────────────────────────────────────────
st.markdown('<div class="eyebrow">SOMALI OSINT BRIEF — LIVE DATA</div>', unsafe_allow_html=True)
st.title("Somalia Security Incident Dashboard")
st.caption("Ground-level data meets grand strategy. Sourced from ACLED, updated weekly.")

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────
st.sidebar.markdown('<div class="eyebrow">FILTERS</div>', unsafe_allow_html=True)

min_date = df["DATE"].min().date()
max_date = df["DATE"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(max_date.replace(year=max_date.year - 1), max_date),
    min_value=min_date,
    max_value=max_date,
)

fms_options = sorted(df["FMS"].dropna().unique().tolist())
selected_fms = st.sidebar.multiselect("Federal Member State", fms_options, default=[])

actor_options = sorted(df["ACTOR"].dropna().unique().tolist())
top_actors = df["ACTOR"].value_counts().head(15).index.tolist()
selected_actors = st.sidebar.multiselect(
    "Actor (top 15 shown)", actor_options, default=[],
    help="Leave empty to include all actors"
)

type_options = sorted(df["TYPE1"].dropna().unique().tolist())
selected_types = st.sidebar.multiselect("Event Type", type_options, default=[])

# ── Apply filters ─────────────────────────────────────────────────────────
filtered = df.copy()

if len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["DATE"].dt.date >= start) & (filtered["DATE"].dt.date <= end)]

if selected_fms:
    filtered = filtered[filtered["FMS"].isin(selected_fms)]

if selected_actors:
    filtered = filtered[filtered["ACTOR"].isin(selected_actors)]

if selected_types:
    filtered = filtered[filtered["TYPE1"].isin(selected_types)]

st.sidebar.markdown("---")
st.sidebar.caption(f"Showing **{len(filtered):,}** of **{len(df):,}** total incidents")
st.sidebar.caption(f"Dataset spans {min_date.strftime('%b %Y')} – {max_date.strftime('%b %Y')}")

# ── KPI row ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Incidents", f"{len(filtered):,}")
col2.metric("Fatalities", f"{int(filtered['FATALITY'].sum()):,}")
col3.metric("Injuries", f"{int(filtered['INJURY'].sum()):,}")
col4.metric("Avg. Fatalities/Incident", f"{filtered['FATALITY'].mean():.2f}" if len(filtered) else "0")

st.markdown("---")

# ── Row 1: Trend over time + Event type breakdown ───────────────────────────
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Incidents Over Time")
    freq = st.radio("Aggregation", ["Monthly", "Yearly"], horizontal=True, label_visibility="collapsed")
    period = "ME" if freq == "Monthly" else "YE"

    trend = filtered.set_index("DATE").resample(period).agg(
        incidents=("ID", "count"),
        fatalities=("FATALITY", "sum")
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=trend["DATE"], y=trend["incidents"], name="Incidents", marker_color=ACCENT, opacity=0.7))
    fig.add_trace(go.Scatter(x=trend["DATE"], y=trend["fatalities"], name="Fatalities", yaxis="y2",
                              mode="lines", line=dict(color="#d47a7a", width=2)))
    fig.update_layout(**base_layout(
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
        yaxis=dict(title="Incidents", gridcolor=BORDER),
        yaxis2=dict(title="Fatalities", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
        height=400,
    ))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Event Types")
    type_counts = filtered["TYPE1"].value_counts().head(8).reset_index()
    type_counts.columns = ["TYPE1", "count"]
    fig2 = px.pie(type_counts, values="count", names="TYPE1", hole=0.5)
    fig2.update_layout(**base_layout(height=400, showlegend=True,
                       legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)")))
    fig2.update_traces(textinfo="percent", textfont_size=10)
    st.plotly_chart(fig2, use_container_width=True)

# ── Row 2: Map + FMS breakdown ────────────────────────────────────────────
c3, c4 = st.columns([2, 1])

with c3:
    st.subheader("Incident Map")
    map_df = filtered.dropna(subset=["LATITUDE", "LONGITUDE"])
    map_df = map_df[(map_df["LATITUDE"] != 0) & (map_df["LONGITUDE"] != 0)]

    if len(map_df) > 5000:
        map_df = map_df.sample(5000, random_state=1)
        st.caption("Showing a sample of 5,000 points for performance")

    if len(map_df):
        fig3 = px.scatter_mapbox(
            map_df, lat="LATITUDE", lon="LONGITUDE",
            color="TYPE1", size="FATALITY", size_max=15,
            hover_data=["DATE", "ACTOR", "LOCALITY", "FATALITY"],
            zoom=4.5, center=dict(lat=5.0, lon=46.0),
            mapbox_style="carto-darkmatter",
        )
        fig3.update_layout(**base_layout(height=450,
                          legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)")))
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No geolocated incidents in current filter.")

with c4:
    st.subheader("By Federal Member State")
    fms_counts = filtered["FMS"].value_counts().head(10).reset_index()
    fms_counts.columns = ["FMS", "count"]
    fig4 = px.bar(fms_counts, x="count", y="FMS", orientation="h")
    fig4.update_traces(marker_color=ACCENT)
    fig4.update_layout(**base_layout(height=450,
                       xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
                       yaxis=dict(autorange="reversed", gridcolor=BORDER)))
    st.plotly_chart(fig4, use_container_width=True)

# ── Row 3: Top actors + fatality breakdown ───────────────────────────────
c5, c6 = st.columns(2)

with c5:
    st.subheader("Most Active Actors")
    actor_counts = filtered["ACTOR"].value_counts().head(10).reset_index()
    actor_counts.columns = ["ACTOR", "count"]
    fig5 = px.bar(actor_counts, x="count", y="ACTOR", orientation="h")
    fig5.update_traces(marker_color=ACCENT)
    fig5.update_layout(**base_layout(height=400,
                       xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
                       yaxis=dict(autorange="reversed", gridcolor=BORDER)))
    st.plotly_chart(fig5, use_container_width=True)

with c6:
    st.subheader("Fatalities by Actor (Top 10)")
    fatal_by_actor = filtered.groupby("ACTOR")["FATALITY"].sum().sort_values(ascending=False).head(10).reset_index()
    fig6 = px.bar(fatal_by_actor, x="FATALITY", y="ACTOR", orientation="h")
    fig6.update_traces(marker_color="#d47a7a")
    fig6.update_layout(**base_layout(height=400,
                       xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
                       yaxis=dict(autorange="reversed", gridcolor=BORDER)))
    st.plotly_chart(fig6, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(f"Data sourced from ACLED. Last refreshed: {datetime.now().strftime('%d %B %Y, %H:%M UTC')}. "
          f"Dataset updates automatically every Monday.")
