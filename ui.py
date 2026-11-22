
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

    /* BASE */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif;
    }

    /* LIGHT MODE */
    :root {
        --ah-bg: #F5F2E8;
        --ah-sidebar: #315B40;
        --ah-card: #FFFFFF;
        --ah-text: #315B40;
        --ah-muted: #71816B;
        --ah-accent: #72966B;
        --ah-note: #DCE8D5;
        --ah-border: #E3E0D4;
    }

    /* DARK MODE */
    @media (prefers-color-scheme: dark) {
        :root {
            --ah-bg: #252D39;
            --ah-sidebar: #202A36;
            --ah-card: #354253;
            --ah-text: #DCE5EF;
            --ah-muted: #B8C6D5;
            --ah-accent: #91AFC9;
            --ah-note: #354B4D;
            --ah-border: #465568;
        }
    }

    .stApp {
        background: var(--ah-bg);
        color: var(--ah-text);
    }

    .block-container {
        padding-top: 1.6rem;
        max-width: 1400px;
    }

    section[data-testid="stSidebar"] {
        background: var(--ah-sidebar);
    }

    section[data-testid="stSidebar"] * {
        color: #F0F7F1;
    }

    section[data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #243449;
    }

    .ah-header {
        border-left: 6px solid var(--ah-accent);
        padding: .2rem 0 .2rem 1rem;
        margin-bottom: 1.4rem;
    }

    .ah-header h1,
    .stApp h1,
    .stApp h2,
    .stApp h3 {
        color: var(--ah-text);
        font-weight: 750;
    }

    .ah-header p {
        color: var(--ah-muted);
    }

    .ah-card {
        background: var(--ah-card);
        color: var(--ah-text);
        border: 1px solid var(--ah-border);
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        box-shadow: 0 3px 10px rgba(0,0,0,.05);
        height: 100%;
    }

    .ah-card .lbl,
    .ah-card .sub {
        color: var(--ah-muted);
    }

    .ah-card .val {
        color: var(--ah-text);
    }

    .ah-note {
        background: var(--ah-note);
        color: var(--ah-text);
        border: 1px solid var(--ah-border);
        border-radius: 12px;
        padding: .8rem 1rem;
    }

    .stButton > button {
        background: var(--ah-sidebar);
        color: white;
        border: none;
        border-radius: 9px;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--ah-accent);
        font-weight: 700;
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
