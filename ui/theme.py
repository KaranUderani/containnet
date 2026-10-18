"""Visual identity: ward-chart paper, ink-teal text, signal-red for infection."""
from __future__ import annotations

import streamlit as st

INK = "#14262E"
PAPER = "#F2F5F4"
TEAL = "#0F7B8A"
INFECTED = "#D7263D"
MUTED = "#C9D3D6"
SOFT = "#E4EBEC"
AMBER = "#E08A1E"
GROUP_COLORS = ["#0F7B8A", "#D98324", "#5B7C99", "#8E6BAF", "#6E9A3C", "#3E4A89", "#B09A2B", "#8A5A44"]
FONT_BODY = "Atkinson Hyperlegible, 'Segoe UI', sans-serif"
FONT_DISPLAY = "Bricolage Grotesque, 'Segoe UI', sans-serif"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&display=swap');

html, body, [class*="css"], .stApp {{ font-family: {FONT_BODY}; color: {INK}; }}
.stApp {{ background: {PAPER}; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1240px; }}
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent; }}

h1, h2, h3, h4 {{ font-family: {FONT_DISPLAY}; letter-spacing: -0.02em; color: {INK}; }}
.cn-title {{ font-family: {FONT_DISPLAY}; font-weight: 800; font-size: 2.6rem; line-height: 1; letter-spacing: -0.035em; margin: 0; }}
.cn-sub {{ font-size: 1.12rem; color: #44575F; margin: .45rem 0 1.4rem; max-width: 46rem; line-height: 1.5; }}
.cn-verdict {{ font-family: {FONT_DISPLAY}; font-weight: 700; font-size: 1.85rem; line-height: 1.22; letter-spacing: -0.025em; max-width: 52rem; margin: .2rem 0 1rem; }}
.cn-verdict .inf {{ color: {INFECTED}; }}
.cn-verdict .ok {{ color: {TEAL}; }}
.cn-note {{ font-size: .95rem; color: #44575F; line-height: 1.55; max-width: 46rem; }}
.cn-small {{ font-size: .85rem; color: #5C6F77; }}

/* section navigation: radio styled as a tab strip */
.st-key-nav [role="radiogroup"] {{ gap: .35rem; flex-wrap: wrap; border-bottom: 2px solid {SOFT}; padding-bottom: .55rem; margin-bottom: 1.2rem; }}
.st-key-nav label {{ background: transparent; border-radius: 8px; padding: .4rem .95rem; cursor: pointer; border: 1px solid transparent; }}
.st-key-nav label > div:first-child {{ display: none; }}
.st-key-nav label p {{ font-family: {FONT_DISPLAY}; font-weight: 700; font-size: 1.02rem; }}
.st-key-nav label:hover {{ background: {SOFT}; }}
.st-key-nav label:has(input:checked) {{ background: {INK}; }}
.st-key-nav label:has(input:checked) p {{ color: {PAPER}; }}

/* people strip */
.cn-strip-label {{ font-size: .92rem; margin: .5rem 0 .3rem; }}
.cn-strip-label b {{ font-variant-numeric: tabular-nums; }}
.cn-strip {{ display: flex; flex-wrap: wrap; gap: 3px; max-width: 790px; }}
.cn-dot {{ width: 17px; height: 17px; border-radius: 4px; background: {MUTED}; }}
.cn-dot.inf {{ background: {INFECTED}; }}
.cn-dot.prot {{ background: {INK}; }}
.cn-dot.safe {{ background: #B9DDE2; }}
.cn-legend {{ display: flex; gap: 1.1rem; flex-wrap: wrap; margin-top: .6rem; font-size: .82rem; color: #5C6F77; }}
.cn-legend i {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: .35rem; vertical-align: -1px; }}

/* protect-first cards */
.cn-card {{ display: grid; grid-template-columns: 2.1rem 1fr; gap: .7rem; padding: .7rem .8rem; border-radius: 10px; background: #fff; border: 1px solid {SOFT}; margin-bottom: .5rem; }}
.cn-rank {{ font-family: {FONT_DISPLAY}; font-weight: 800; font-size: 1.35rem; color: {TEAL}; font-variant-numeric: tabular-nums; line-height: 1.1; }}
.cn-card .who {{ font-weight: 700; }}
.cn-card .meta {{ font-size: .83rem; color: #5C6F77; margin-top: .1rem; }}
.cn-chip {{ display: inline-block; font-size: .76rem; padding: .08rem .5rem; border-radius: 99px; margin: .3rem .3rem 0 0; background: {SOFT}; }}
.cn-chip.amber {{ background: #FBE8CC; }}
.cn-chip.red {{ background: #F8D6DA; }}

/* controls panel */
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 12px; border-color: {SOFT}; background: #fff; }}
.stSlider [data-baseweb="slider"] > div > div {{ background: {SOFT}; }}
button[kind="secondary"], button[kind="primary"] {{ border-radius: 8px; font-weight: 700; }}
[data-testid="stMetricValue"] {{ font-family: {FONT_DISPLAY}; font-weight: 800; }}
[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}

@media (max-width: 760px) {{
  .cn-title {{ font-size: 2rem; }}
  .cn-verdict {{ font-size: 1.4rem; }}
  .cn-dot {{ width: 13px; height: 13px; }}
}}
@media (prefers-reduced-motion: no-preference) {{
  .cn-dot {{ transition: background .25s ease; }}
}}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
