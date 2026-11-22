"""Komponen tampilan bersama: tema AgroHeat, kartu metrik, grafik."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config

C = config.COLORS
TONES = {"green": (C["green_soft"], C["green_dark"]), "yellow": (C["yellow_soft"], "#92400e"),
         "red": (C["red_soft"], "#991b1b"), "gray": (C["gray_soft"], "#334155")}



def inject_css() -> None:
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* GLOBAL */
    html, body, [class*="css"], .stApp {{
        font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif;
    }}

    .stApp {{
        background: #F4F6F1;
        color: #243449;
    }}

    .block-container {{
        padding-top: 1.6rem;
        max-width: 1400px;
    }}

    /* SIDEBAR */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #174D35 0%, #103B2A 100%);
    }}

    section[data-testid="stSidebar"] * {{
        color: #F0F7F1 !important;
    }}

    section[data-testid="stSidebar"] [data-baseweb="select"] * {{
        color: #243449 !important;
    }}

    /* BRAND */
    .ah-brand {{
        font-weight: 800;
        font-size: 1.55rem;
        letter-spacing: .08em;
        margin-bottom: 0;
    }}

    .ah-brand span {{
        color: #A7E5B8;
    }}

    .ah-tag {{
        font-size: .72rem;
        opacity: .8;
        margin-bottom: 1rem;
    }}

    /* PAGE HEADER */
    .ah-header {{
        border-left: 6px solid #258653;
        padding: .2rem 0 .2rem 1rem;
        margin-bottom: 1.4rem;
    }}

    .ah-header h1 {{
        font-size: 1.8rem;
        font-weight: 800;
        color: #174D35;
        margin: 0;
    }}

    .ah-header p {{
        color: #64748B;
        margin: .15rem 0 0 0;
        font-size: .92rem;
    }}

    /* SECTION HEADINGS */
    .stApp h1, .stApp h2, .stApp h3 {{
        color: #174D35 !important;
        font-weight: 750;
    }}

    /* METRIC CARDS */
    .ah-card {{
        background: #FFFFFF;
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        border: 1px solid #E2E8E0;
        box-shadow: 0 3px 10px rgba(23, 77, 53, .06);
        height: 100%;
    }}

    .ah-card .lbl {{
        font-size: .74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .05em;
        color: #64748B;
    }}

    .ah-card .val {{
        font-size: 1.8rem;
        font-weight: 800;
        color: #243449;
        line-height: 1.3;
    }}

    .ah-card .sub {{
        font-size: .78rem;
        color: #64748B;
    }}

    /* BADGES */
    .ah-badge {{
        display: inline-block;
        padding: .2rem .7rem;
        border-radius: 999px;
        font-size: .75rem;
        font-weight: 700;
    }}

    /* NOTES */
    .ah-note {{
        background: #E8F2E9;
        border: 1px solid #C8DFCC;
        border-radius: 12px;
        padding: .8rem 1rem;
        font-size: .85rem;
        color: #174D35;
    }}

    /* STREAMLIT ALERTS */
    div[data-testid="stAlert"] {{
        background: #E8F2E9;
        border: 1px solid #C8DFCC;
        border-radius: 12px;
        color: #174D35;
    }}

    div[data-testid="stAlert"] p {{
        color: #174D35 !important;
    }}

    /* TABS */
    div[data-testid="stTabs"] button[aria-selected="true"] {{
        color: #174D35;
        font-weight: 700;
    }}

    /* BUTTONS */
    .stButton > button {{
        background: #1D6344;
        color: white;
        border: none;
        border-radius: 9px;
        font-weight: 600;
    }}

    .stButton > button:hover {{
        background: #174D35;
        color: white;
        border: none;
    }}

    </style>
    """, unsafe_allow_html=True)



def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="ah-header"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def badge(text: str, tone: str = "gray") -> str:
    bg, fg = TONES.get(tone, TONES["gray"])
    return f'<span class="ah-badge" style="background:{bg};color:{fg}">{text}</span>'


def metric_card(label: str, value, sub: str = "", tone: str = "green") -> None:
    color = {"green": C["green_dark"], "yellow": C["yellow"], "red": C["red"], "gray": C["ink"]}[tone]
    st.markdown(f'<div class="ah-card" style="border-top:4px solid {color}"><div class="lbl">{label}</div>'
                f'<div class="val" style="color:{color}">{value}</div><div class="sub">{sub or "&nbsp;"}</div></div>',
                unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="ah-note">{text}</div>', unsafe_allow_html=True)


def source_badge(source_key: str) -> str:
    tone = {"real_sensor": "green", "simulation": "yellow", "manual": "gray", "public_dataset": "gray"}.get(source_key, "gray")
    return badge(config.DATA_SOURCES.get(source_key, source_key), tone)


def fmt_duration(seconds) -> str:
    if seconds is None or pd.isna(seconds):
        return "—"
    s = int(round(float(seconds)))
    return f"{s // 3600}j {s % 3600 // 60}m {s % 60}d" if s >= 3600 else f"{s // 60}m {s % 60}d"


def style_fig(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(height=height, template="plotly_white", font=dict(family="Plus Jakarta Sans, Segoe UI"),
                      margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=-0.2))
    return fig


def temp_chart(readings: pd.DataFrame, target: float, title: str = "Suhu terhadap waktu") -> go.Figure:
    fig = go.Figure()
    d = readings.dropna(subset=["temperature_c"])
    fig.add_trace(go.Scatter(x=d["elapsed_seconds"], y=d["temperature_c"], mode="lines+markers", name="Suhu aktual",
                             line=dict(color=C["green"], width=3), marker=dict(size=4)))
    fig.add_hline(y=target, line_dash="dash", line_color=C["red"],
                  annotation_text=f"Target {target:.1f} °C", annotation_position="top left")
    fig.update_layout(title=title, xaxis_title="Elapsed (detik)", yaxis_title="Suhu (°C)")
    return style_fig(fig)


def empty_state(text: str) -> None:
    st.info(text)
