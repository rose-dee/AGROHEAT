
"""Komponen tampilan bersama: tema AgroHeat, kartu metrik, grafik."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config

C = config.COLORS


def is_dark_mode() -> bool:
    """Memeriksa tema Streamlit yang sedang digunakan."""
    return st.get_option("theme.base") == "dark"


def get_tones():
    """Warna badge yang menyesuaikan tema."""
    if is_dark_mode():
        return {
            "green": ("#214B35", "#B7F0C5"),
            "yellow": ("#59451F", "#FFE09A"),
            "red": ("#5C2929", "#FFC1C1"),
            "gray": ("#374151", "#E2E8F0"),
        }

    return {
        "green": ("#DCFCE7", "#166534"),
        "yellow": ("#FEF3C7", "#92400E"),
        "red": ("#FEE2E2", "#991B1B"),
        "gray": ("#E2E8F0", "#334155"),
    }


def inject_css() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* GLOBAL */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif;
    }

    .stApp {
        background: var(--background-color);
        color: var(--text-color);
    }

    .block-container {
        padding-top: 1.6rem;
        max-width: 1400px;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #174D35 0%, #103B2A 100%);
    }

    section[data-testid="stSidebar"] * {
        color: #F0F7F1;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #243449 !important;
    }

    /* BRAND */
    .ah-brand {
        font-weight: 800;
        font-size: 1.55rem;
        letter-spacing: .08em;
        margin-bottom: 0;
    }

    .ah-brand span {
        color: #A7E5B8;
    }

    .ah-tag {
        font-size: .72rem;
        opacity: .8;
        margin-bottom: 1rem;
    }

    /* PAGE HEADER */
    .ah-header {
        border-left: 6px solid var(--primary-color);
        padding: .2rem 0 .2rem 1rem;
        margin-bottom: 1.4rem;
    }

    .ah-header h1 {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--text-color);
        margin: 0;
    }

    .ah-header p {
        color: var(--text-color);
        opacity: .8;
        margin: .15rem 0 0;
        font-size: .92rem;
    }

    /* SECTION HEADINGS */
    .stApp h1, .stApp h2, .stApp h3 {
        color: var(--text-color);
        font-weight: 750;
    }

    /* METRIC CARDS */
    .ah-card {
        background: var(--secondary-background-color);
        color: var(--text-color);
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        border: 1px solid rgba(128, 128, 128, .25);
        box-shadow: 0 3px 10px rgba(0, 0, 0, .06);
        height: 100%;
    }

    .ah-card .lbl {
        font-size: .74rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .05em;
        color: var(--text-color);
        opacity: .8;
    }

    .ah-card .val {
        font-size: 1.8rem;
        font-weight: 800;
        color: var(--text-color);
        line-height: 1.3;
    }

    .ah-card .sub {
        font-size: .78rem;
        color: var(--text-color);
        opacity: .8;
    }

    /* BADGES */
    .ah-badge {
        display: inline-block;
        padding: .2rem .7rem;
        border-radius: 999px;
        font-size: .75rem;
        font-weight: 700;
    }

    /* NOTES */
    .ah-note {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, .3);
        border-radius: 12px;
        padding: .8rem 1rem;
        font-size: .85rem;
        color: var(--text-color);
    }

    /* ALERTS */
    div[data-testid="stAlert"] {
        border-radius: 12px;
    }

    /* TABS */
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--primary-color);
        font-weight: 700;
    }

    /* BUTTONS */
    .stButton > button {
        background: var(--primary-color);
        color: white;
        border-radius: 9px;
        font-weight: 600;
        border: none;
    }

    .stButton > button:hover {
        opacity: .85;
        color: white;
    }

    /* INPUTS */
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTimeInput input,
    .stTextArea textarea {
        color: var(--text-color);
    }

    /* DATAFRAME */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }

    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="ah-header"><h1>{title}</h1>'
        f'<p>{subtitle}</p></div>',
        unsafe_allow_html=True
    )


def badge(text: str, tone: str = "gray") -> str:
    tones = get_tones()
    bg, fg = tones.get(tone, tones["gray"])

    return (
        f'<span class="ah-badge" '
        f'style="background:{bg};color:{fg}">{text}</span>'
    )


def metric_card(
    label: str,
    value,
    sub: str = "",
    tone: str = "green"
) -> None:

    dark = is_dark_mode()

    if dark:
        colors = {
            "green": "#86DFA4",
            "yellow": "#FFD166",
            "red": "#FF9999",
            "gray": "#E2E8F0",
        }
    else:
        colors = {
            "green": "#166534",
            "yellow": "#92400E",
            "red": "#991B1B",
            "gray": "#334155",
        }

    color = colors.get(tone, colors["gray"])

    st.markdown(
        f'<div class="ah-card" style="border-top:4px solid {color}">'
        f'<div class="lbl">{label}</div>'
        f'<div class="val" style="color:{color}">{value}</div>'
        f'<div class="sub">{sub or "&nbsp;"}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def note(text: str) -> None:
    st.markdown(
        f'<div class="ah-note">{text}</div>',
        unsafe_allow_html=True
    )


def source_badge(source_key: str) -> str:
    tone = {
        "real_sensor": "green",
        "simulation": "yellow",
        "manual": "gray",
        "public_dataset": "gray",
    }.get(source_key, "gray")

    return badge(
        config.DATA_SOURCES.get(source_key, source_key),
        tone
    )


def fmt_duration(seconds) -> str:
    if seconds is None or pd.isna(seconds):
        return "—"

    s = int(round(float(seconds)))

    return (
        f"{s // 3600}j {s % 3600 // 60}m {s % 60}d"
        if s >= 3600
        else f"{s // 60}m {s % 60}d"
    )


def style_fig(fig: go.Figure, height: int = 380) -> go.Figure:
    """Mengatur grafik agar mengikuti Light/Dark Mode."""

    dark = is_dark_mode()

    if dark:
        template = "plotly_dark"
        font_color = "#E2E8F0"
        grid_color = "#3B4658"
    else:
        template = "plotly_white"
        font_color = "#334155"
        grid_color = "#E2E8F0"

    fig.update_layout(
        height=height,
        template=template,
        font=dict(
            family="Plus Jakarta Sans, Segoe UI",
            color=font_color
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.2),
    )

    fig.update_xaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color
    )

    fig.update_yaxes(
        gridcolor=grid_color,
        zerolinecolor=grid_color
    )

    return fig


def temp_chart(
    readings: pd.DataFrame,
    target: float,
    title: str = "Suhu terhadap waktu"
) -> go.Figure:

    fig = go.Figure()
    d = readings.dropna(subset=["temperature_c"])

    fig.add_trace(
        go.Scatter(
            x=d["elapsed_seconds"],
            y=d["temperature_c"],
            mode="lines+markers",
            name="Suhu aktual",
            line=dict(color=C["green"], width=3),
            marker=dict(size=4)
        )
    )

    fig.add_hline(
        y=target,
        line_dash="dash",
        line_color=C["red"],
        annotation_text=f"Target {target:.1f} °C",
        annotation_position="top left"
    )

    fig.update_layout(
        title=title,
        xaxis_title="Elapsed (detik)",
        yaxis_title="Suhu (°C)"
    )

    return style_fig(fig)


def empty_state(text: str) -> None:
    st.info(text)
