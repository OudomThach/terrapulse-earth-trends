"""Interface layer: design-system CSS and small HTML components.

Design rules applied (see theme.py): 8-point spacing, 12/14/16/20/28/40 type scale, one accent,
colour = direction of change (never good/bad), and every status carries text or an icon as well as colour.
"""

from __future__ import annotations

from html import escape

import numpy as np

from . import theme as C
from .narrative import signed, strength_dots
from .trends import TrendResult
from .variables import Variable

ACCENT_TEXT = "#3fd4a2"      # accent for text/links on dark surfaces (high contrast)
ACCENT_FILL = "#0f7a57"      # accent for filled buttons (white text >= 5:1)

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {{
  --bg:{C.BG}; --surface:{C.SURFACE}; --surface-2:{C.SURFACE_2}; --line:{C.LINE}; --line-strong:{C.LINE_STRONG};
  --ink:{C.INK}; --ink-2:{C.INK_2}; --muted:{C.MUTED}; --rise:{C.RISE}; --fall:{C.FALL};
  --accent:{ACCENT_TEXT}; --accent-fill:{ACCENT_FILL}; --warn:#fab219;
  --shadow-sm:0 1px 2px rgba(0,0,0,.35); --shadow-md:0 8px 24px rgba(0,0,0,.35);
}}
html, body, .stApp {{ font-family:{C.FONT}; }}
.stApp {{ background:var(--bg); color:var(--ink); }}
[data-testid="stToolbar"], [data-testid="stDecoration"], footer, #MainMenu {{ display:none !important; }}
[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ max-width:1240px; padding:24px 24px 96px; }}
[data-testid="stSidebar"] {{ background:#121211; border-right:1px solid var(--line); }}
[data-testid="stSidebar"] .block-container {{ padding:24px 16px; }}
h1, h2, h3, h4 {{ color:var(--ink); letter-spacing:-0.01em; }}
p, li, label {{ color:var(--ink-2); line-height:1.6; }}
a {{ color:var(--accent); }}
::selection {{ background:rgba(63,212,162,.3); }}

/* containers with border -> cards */
div[data-testid="stVerticalBlockBorderWrapper"] {{
  background:var(--surface); border:1px solid var(--line) !important; border-radius:16px; box-shadow:var(--shadow-sm);
}}
/* buttons */
.stButton > button, .stDownloadButton > button {{
  border-radius:8px; border:1px solid var(--line-strong); background:var(--surface-2); color:var(--ink);
  font-weight:600; font-size:14px; padding:8px 16px; transition:background .15s, border-color .15s, transform .05s;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color:var(--accent); background:#2a2a27; color:var(--ink); }}
.stButton > button:active {{ transform:translateY(1px); }}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
[data-baseweb="select"]:focus-within {{ outline:2px solid var(--accent); outline-offset:2px; }}
.stButton > button[kind="primary"] {{ background:var(--accent-fill); border-color:var(--accent-fill); color:#fff; }}
.stButton > button[kind="primary"]:hover {{ background:#139a6e; border-color:#139a6e; }}
/* expanders */
[data-testid="stExpander"] {{ border:1px solid var(--line); border-radius:12px; background:var(--surface); }}
[data-testid="stExpander"] summary {{ font-weight:600; color:var(--ink); }}
[data-testid="stMetric"] {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:16px; }}
.stDataFrame {{ border:1px solid var(--line); border-radius:12px; overflow:hidden; }}

/* ---------- components ---------- */
.tp-eyebrow {{ font-size:12px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); }}
.tp-hero {{ padding:8px 0 24px; }}
.tp-hero h1 {{ font-size:40px; line-height:1.1; font-weight:700; margin:8px 0 16px; max-width:20ch; }}
.tp-hero p.lead {{ font-size:18px; line-height:1.6; color:var(--ink-2); max-width:62ch; margin:0 0 24px; }}
.tp-steps {{ display:flex; gap:8px; flex-wrap:wrap; }}
.tp-step {{ display:flex; align-items:center; gap:8px; padding:8px 16px 8px 8px; border:1px solid var(--line);
  border-radius:999px; background:var(--surface); font-size:14px; color:var(--ink-2); }}
.tp-step b {{ display:inline-grid; place-items:center; width:24px; height:24px; border-radius:50%;
  background:var(--accent-fill); color:#fff; font-size:12px; }}

.tp-case {{ display:flex; flex-wrap:wrap; gap:8px 24px; align-items:baseline; padding:16px 0 8px; }}
.tp-case .place {{ font-size:20px; font-weight:700; color:var(--ink); }}
.tp-case .meta {{ font-size:14px; color:var(--muted); }}
.tp-case .blurb {{ font-size:14px; color:var(--ink-2); flex-basis:100%; }}

.tp-kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:16px; margin:8px 0 24px; }}
.tp-kpi {{ background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:16px 24px; }}
.tp-kpi .label {{ font-size:12px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }}
.tp-kpi .value {{ font-size:28px; font-weight:700; color:var(--ink); line-height:1.2; margin-top:8px; }}
.tp-kpi .sub {{ font-size:14px; color:var(--ink-2); margin-top:4px; }}
.tp-kpi .value.rise {{ color:var(--rise); }} .tp-kpi .value.fall {{ color:var(--fall); }}
.tp-kpi .value.sm {{ font-size:20px; line-height:1.3; min-height:52px; }}
.tp-kpi .sub.rise {{ color:var(--rise); }} .tp-kpi .sub.fall {{ color:var(--fall); }}

.tp-section {{ margin:32px 0 16px; }}
.tp-section h2 {{ font-size:20px; font-weight:700; margin:0 0 4px; }}
.tp-section p {{ font-size:14px; color:var(--muted); margin:0; max-width:75ch; }}

.tp-suspect {{ padding:4px 4px 0; }}
.tp-suspect-top {{ display:flex; justify-content:space-between; align-items:center; }}
.tp-chip {{ font-size:12px; color:var(--muted); font-weight:600; letter-spacing:.06em; text-transform:uppercase; }}
.tp-meter {{ font-size:12px; letter-spacing:2px; color:var(--accent); }}
.tp-meter.dim {{ color:var(--muted); }}
.tp-suspect-name {{ font-size:16px; font-weight:600; color:var(--ink); margin:8px 0 4px; }}
.tp-rate {{ font-size:28px; font-weight:700; line-height:1.1; }}
.tp-rate .unit {{ font-size:12px; font-weight:500; color:var(--muted); margin-left:4px; }}
.tp-rate.rise {{ color:var(--rise); }} .tp-rate.fall {{ color:var(--fall); }} .tp-rate.flat {{ color:var(--muted); }}
.tp-spark {{ display:block; margin:8px 0; }}
.tp-foot {{ display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:12px; color:var(--muted); }}
.tp-badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; font-weight:600;
  border:1px solid var(--line-strong); color:var(--ink-2); }}
.tp-badge.strong {{ background:var(--accent-fill); border-color:var(--accent-fill); color:#fff; }}
.tp-badge.sig {{ border-color:var(--accent); color:var(--accent); }}
.tp-badge.weak {{ border-color:var(--muted); color:var(--ink-2); border-style:dashed; }}
.tp-badge.none {{ color:var(--muted); }}
.tp-flag {{ margin-top:8px; font-size:12px; color:var(--warn); }}

.tp-banner {{ border-radius:16px; padding:24px; border:1px solid var(--line); background:var(--surface);
  border-left:4px solid var(--muted); margin:8px 0 24px; }}
.tp-banner.strong, .tp-banner.sig {{ border-left-color:var(--accent); }}
.tp-banner.warn {{ border-left-color:var(--warn); background:#211d12; }}
.tp-banner h3 {{ font-size:28px; line-height:1.2; margin:8px 0 8px; font-weight:700; }}
.tp-banner p {{ font-size:16px; line-height:1.7; color:var(--ink-2); max-width:70ch; margin:0; }}
.tp-banner p b, .tp-banner p strong {{ color:var(--ink); }}
.tp-banner.warn p {{ color:#e9dfc2; }}

.tp-story {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:16px; }}
.tp-story-card {{ background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:16px 24px; }}
.tp-story-card h4 {{ font-size:16px; margin:0 0 8px; }}
.tp-story-card p {{ font-size:14px; margin:0; }}

.tp-how {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; }}
.tp-how .card {{ background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:24px; }}
.tp-how .n {{ font-size:12px; font-weight:700; letter-spacing:.14em; color:var(--accent); }}
.tp-how h4 {{ font-size:16px; margin:8px 0; }} .tp-how p {{ font-size:14px; margin:0; }}

.tp-legend {{ display:flex; gap:24px; flex-wrap:wrap; font-size:13px; color:var(--ink-2); margin:8px 0 16px; }}
.tp-legend i {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:8px; vertical-align:-1px; }}
.tp-note {{ font-size:13px; color:var(--muted); line-height:1.6; max-width:80ch; }}
.tp-demo-title {{ font-weight:600; color:var(--ink); font-size:14px; }}
.tp-demo-text {{ font-size:13px; color:var(--muted); margin:4px 0 8px; line-height:1.5; }}
@media (max-width:700px) {{ .tp-hero h1 {{ font-size:28px; }} .block-container {{ padding:16px 16px 64px; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition:none !important; }} }}
</style>
"""


def inject_css() -> None:
    """Add the design-system stylesheet to the current Streamlit page."""
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- pure HTML builders
def _dir_class(res: TrendResult) -> str:
    return res.direction if res.direction in ("rising", "falling") and res.usable else "flat"


def _css_dir(res: TrendResult) -> str:
    return {"rising": "rise", "falling": "fall"}.get(res.direction, "flat")


def sparkline(values, direction_class: str, w: int = 180, h: int = 40) -> str:
    """Inline SVG of the yearly averages (decorative; the numbers beside it carry the meaning)."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) < 2:
        return ""
    lo, hi = float(v.min()), float(v.max())
    span = hi - lo or 1.0
    xs = np.linspace(3, w - 3, len(v))
    ys = h - 4 - (v - lo) / span * (h - 8)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    color = {"rise": C.RISE, "fall": C.FALL}.get(direction_class, C.MUTED)
    return (f'<svg class="tp-spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="yearly averages over time"><polyline points="{pts}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3.5" fill="{color}" stroke="{C.SURFACE}" stroke-width="2"/></svg>')


def hero() -> str:
    """Page header: title, one-paragraph pitch and the four steps."""
    return (
        '<div class="tp-hero"><div class="tp-eyebrow">Earth system &middot; Trend Detective</div>'
        "<h1>Is the planet changing where you live?</h1>"
        '<p class="lead">Pick any place on Earth. We pull 36 years of satellite-based records, scan 20 vital signs, '
        "and test each one for a real, statistically significant trend. Ask a question, or follow the clues yourself.</p>"
        '<div class="tp-steps"><div class="tp-step"><b>1</b>Choose a place</div>'
        '<div class="tp-step"><b>2</b>Ask a question</div><div class="tp-step"><b>3</b>Test the evidence</div>'
        '<div class="tp-step"><b>4</b>Compare the world</div></div></div>')


def case_strip(place: str, lat: float, lon: float, biome: str, blurb: str, start: int, end: int, n_vars: int) -> str:
    """One-line summary of the place and window being investigated."""
    return (f'<div class="tp-case"><span class="place">{escape(place)}</span>'
            f'<span class="meta">{lat:.2f}&deg;, {lon:.2f}&deg; &middot; {escape(biome)} &middot; {start}&ndash;{end} '
            f'&middot; {(end - start + 1) * 12} months &middot; {n_vars} variables</span>'
            f'<span class="blurb">{escape(blurb)}</span></div>')


def kpi(label: str, value: str, sub: str = "", tone: str = "", sub_tone: str = "") -> str:
    """A statistic card: small label, large value, explanatory line."""
    size = "sm" if len(value) > 14 else ""
    return (f'<div class="tp-kpi"><div class="label">{escape(label)}</div>'
            f'<div class="value {tone} {size}">{escape(value)}</div><div class="sub {sub_tone}">{escape(sub)}</div></div>')


def kpi_row(items: list[str]) -> str:
    """A responsive row of statistic cards."""
    return '<div class="tp-kpis">' + "".join(items) + "</div>"


def section(title: str, sub: str = "") -> str:
    """Section heading with an optional one-line description."""
    p = f"<p>{escape(sub)}</p>" if sub else ""
    return f'<div class="tp-section"><h2>{escape(title)}</h2>{p}</div>'


def badge(label: str, tone: str) -> str:
    """Small pill showing the strength of evidence (text plus style, never colour alone)."""
    return f'<span class="tp-badge {tone}">{escape(label)}</span>'


TONE_FROM_LABEL = {"Strong evidence": "strong", "Significant": "sig", "Weak hint": "weak"}


def _fmt_p(p: float) -> str:
    return "< 0.001" if p < 0.0005 else f"= {p:.3f}"


def suspect_card(v: Variable, res: TrendResult, label: str, p_shown: float) -> str:
    """Summary card for one variable: rate, sparkline, evidence badge and any data-jump flag."""
    tone = TONE_FROM_LABEL.get(label, "none")
    if not res.usable:
        return (f'<div class="tp-suspect"><div class="tp-suspect-top"><span class="tp-chip">{escape(v.group)}</span></div>'
                f'<div class="tp-suspect-name">{escape(v.name)}</div>'
                f'<div class="tp-note">{escape(res.reason)}</div></div>')
    arrow = {"rising": "&#9650;", "falling": "&#9660;"}.get(res.direction, "&ndash;")
    cls = _css_dir(res)
    dots = strength_dots(p_shown)
    flag = (f'<div class="tp-flag">&#9888; Possible data jump in {res.jump_year}</div>' if res.suspicious_jump else "")
    return (
        f'<div class="tp-suspect"><div class="tp-suspect-top"><span class="tp-chip">{escape(v.group)}</span>'
        f'<span class="tp-meter {"dim" if tone == "none" else ""}" title="Strength of evidence">{dots}</span></div>'
        f'<div class="tp-suspect-name">{escape(v.name)}</div>'
        f'<div class="tp-rate {cls}">{arrow} {escape(signed(res.per_decade, v.decimals))}'
        f'<span class="unit">{escape(v.unit)} / decade</span></div>'
        f'{sparkline(res.annual, cls)}'
        f'<div class="tp-foot">{badge(label, tone)}<span title="p-value after correcting for testing many variables">adj. p {_fmt_p(p_shown)}</span></div>{flag}</div>')


def banner(headline: str, body_html: str, tone: str, eyebrow: str = "") -> str:
    """Large message box (verdict, caution or finding) with a left accent bar."""
    eb = f'<div class="tp-eyebrow">{escape(eyebrow)}</div>' if eyebrow else ""
    return f'<div class="tp-banner {tone}">{eb}<h3>{escape(headline)}</h3><p>{body_html}</p></div>'


def story_cards(items: list[dict]) -> str:
    """Grid of short 'what it means' cards."""
    return '<div class="tp-story">' + "".join(
        f'<div class="tp-story-card"><h4>{escape(i["title"])}</h4><p>{escape(i["text"])}</p></div>' for i in items
    ) + "</div>"


def md_bold_to_html(text: str) -> str:
    """Tiny converter for the **bold** used in narrative strings (text is escaped first)."""
    parts = escape(text).split("**")
    return "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parts))


def direction_legend() -> str:
    """Key explaining that colour shows direction, not good or bad."""
    return (f'<div class="tp-legend"><span><i style="background:{C.RISE}"></i>Rising</span>'
            f'<span><i style="background:{C.FALL}"></i>Falling</span>'
            f'<span><i style="background:{C.LINE_STRONG}"></i>Colour shows direction, not good or bad</span>'
            f'<span>Solid = significant &middot; faded = not significant</span></div>')
