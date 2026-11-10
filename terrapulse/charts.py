"""Plotly figure builders (no Streamlit imports, so they are easy to test)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from . import theme as C
from .narrative import signed
from .trends import TrendResult, monthly_anomalies
from .variables import VARIABLES, Variable

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
GIBS_TILES = ("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/"
              "default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg")


def _layout(height: int = 380, **kw) -> dict:
    base = dict(
        height=height, margin=dict(l=8, r=16, t=40, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=C.FONT, color=C.INK_2, size=13),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=C.INK_2)),
        hoverlabel=dict(bgcolor=C.SURFACE_2, bordercolor=C.LINE_STRONG, font=dict(color=C.INK, size=13)),
        xaxis=dict(showgrid=False, linecolor=C.LINE_STRONG, tickcolor=C.LINE_STRONG, tickfont=dict(color=C.MUTED),
                   automargin=True),
        yaxis=dict(gridcolor=C.LINE, zeroline=False, linecolor="rgba(0,0,0,0)", tickfont=dict(color=C.MUTED),
                   automargin=True, title=dict(standoff=12)),
    )
    base.update(kw)
    return base


def _decimal_year(idx: pd.DatetimeIndex) -> np.ndarray:
    return idx.year.to_numpy() + (idx.month.to_numpy() - 0.5) / 12


def _wedge(res: TrendResult, t: np.ndarray, shift: float = 0.0):
    lo = res.line_at(t, res.ci_low) - shift
    hi = res.line_at(t, res.ci_high) - shift
    return np.minimum(lo, hi), np.maximum(lo, hi)


def _jump_marker(fig: go.Figure, res: TrendResult, date) -> None:
    fig.add_vline(x=date, line=dict(color=C.INK_2, width=1, dash="dot"))
    fig.add_annotation(x=date, y=1.0, yref="paper", text=f"possible data jump, {res.jump_year}",
                       showarrow=False, xanchor="left", yanchor="top", xshift=6,
                       font=dict(size=12, color=C.INK_2))


def trend_figure(series: pd.Series, res: TrendResult, v: Variable, anomalies: bool = False) -> go.Figure:
    """Monthly record, 12-month average, Sen trend line and the 95% slope-uncertainty wedge."""
    s = series.dropna()
    y = monthly_anomalies(s) if anomalies else s
    t = _decimal_year(s.index)
    shift = res.mean if anomalies else 0.0
    smooth = y.rolling(12, min_periods=9, center=True).mean()
    lo, hi = _wedge(res, t, shift)
    trend = res.line_at(t) - shift
    unit = v.unit
    fig = go.Figure()
    fig.add_scatter(x=np.r_[s.index, s.index[::-1]], y=np.r_[hi, lo[::-1]], fill="toself", mode="none",
                    fillcolor="rgba(217,89,38,0.16)", name="95% range of the trend", hoverinfo="skip")
    fig.add_scatter(x=s.index, y=y, mode="lines", name="Monthly", line=dict(color=C.MUTED, width=1),
                    opacity=0.75, hovertemplate=f"%{{y:,.{v.decimals}f}} {unit}<extra>Monthly</extra>")
    fig.add_scatter(x=s.index, y=smooth, mode="lines", name="12-month average",
                    line=dict(color=C.BLUE, width=2),
                    hovertemplate=f"%{{y:,.{v.decimals}f}} {unit}<extra>12-month average</extra>")
    fig.add_scatter(x=s.index, y=trend, mode="lines", name="Trend (Sen slope)", line=dict(color=C.ORANGE, width=2.5),
                    hovertemplate=f"%{{y:,.{v.decimals}f}} {unit}<extra>Trend</extra>")
    fig.add_annotation(x=s.index[-1], y=trend[-1], text=f"{signed(res.per_decade, v.decimals)}/decade",
                       showarrow=False, xanchor="left", xshift=8, font=dict(color=C.ORANGE, size=12))
    if anomalies:
        fig.add_hline(y=0, line=dict(color=C.LINE_STRONG, width=1))
    if res.suspicious_jump:
        _jump_marker(fig, res, pd.Timestamp(f"{res.jump_year}-01-01"))
    fig.update_layout(**_layout(height=400, hovermode="x unified", margin=dict(l=8, r=84, t=40, b=8),
                                yaxis_title=(f"Anomaly ({unit})" if anomalies else unit)))
    return fig


def annual_figure(res: TrendResult, v: Variable) -> go.Figure:
    """One dot per year plus the trend: the data the statistics are actually run on."""
    yrs = res.years.astype(float) + 0.5
    lo, hi = _wedge(res, yrs)
    fig = go.Figure()
    fig.add_scatter(x=np.r_[res.years, res.years[::-1]], y=np.r_[hi, lo[::-1]], fill="toself", mode="none",
                    fillcolor="rgba(217,89,38,0.16)", name="95% range of the trend", hoverinfo="skip")
    fig.add_scatter(x=res.years, y=res.annual, mode="lines+markers", name="Yearly average",
                    line=dict(color=C.LINE_STRONG, width=1),
                    marker=dict(size=8, color=C.BLUE, line=dict(color=C.SURFACE, width=2)),
                    hovertemplate=f"%{{x}}: %{{y:,.{v.decimals}f}} {v.unit}<extra></extra>")
    fig.add_scatter(x=res.years, y=res.line_at(yrs), mode="lines", name="Trend (Sen slope)",
                    line=dict(color=C.ORANGE, width=2.5), hoverinfo="skip")
    hi_i, lo_i = int(np.argmax(res.annual)), int(np.argmin(res.annual))
    for i, word in ((hi_i, "highest"), (lo_i, "lowest")):
        fig.add_annotation(x=res.years[i], y=res.annual[i], text=f"{word}: {res.years[i]}", showarrow=True,
                           arrowcolor=C.MUTED, arrowwidth=1, ay=-26 if word == "highest" else 26,
                           font=dict(size=12, color=C.INK_2))
    if res.suspicious_jump:
        fig.add_vline(x=res.jump_year - 0.5, line=dict(color=C.INK_2, width=1, dash="dot"))
        fig.add_annotation(x=res.jump_year - 0.5, y=1.0, yref="paper", text="possible data jump", showarrow=False,
                           xanchor="left", yanchor="top", xshift=6, font=dict(size=12, color=C.INK_2))
    fig.update_layout(**_layout(height=340, yaxis_title=v.unit, xaxis=dict(
        showgrid=False, linecolor=C.LINE_STRONG, tickfont=dict(color=C.MUTED), dtick=5, automargin=True)))
    return fig


def seasonal_figure(fp: pd.DataFrame, v: Variable) -> go.Figure:
    """Rate of change for each calendar month: which seasons drive the trend?"""
    sig = (fp["p"] < 0.05).to_numpy()
    colors = [C.RISE if d > 0 else C.FALL for d in fp["per_decade"].fillna(0)]
    fig = go.Figure(go.Bar(
        x=MONTHS, y=fp["per_decade"], marker=dict(color=colors, opacity=[1.0 if s else 0.35 for s in sig],
                                                   cornerradius=4),
        customdata=np.c_[fp["p"].to_numpy()],
        hovertemplate=f"%{{x}}: %{{y:+,.{v.decimals}f}} {v.unit} per decade<br>p = %{{customdata[0]:.3f}}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=C.LINE_STRONG, width=1))
    fig.update_layout(**_layout(height=300, margin=dict(l=8, r=16, t=16, b=8), yaxis_title=f"{v.unit} per decade",
                                bargap=0.35, showlegend=False))
    return fig


def map_figure(df: pd.DataFrame, v: Variable, satellite: bool = True, selected: str | None = None,
               events: pd.DataFrame | None = None) -> go.Figure:
    """World map of one variable's trend across places. Solid + ringed = significant."""
    zmax = max(float(np.nanpercentile(np.abs(df["per_decade"]), 85)) if len(df) else 1.0, 1e-9)
    fig = go.Figure()
    sig = df[df["significant"]]
    rest = df[~df["significant"]]
    if len(sig):  # white ring under significant places (map markers have no outline of their own)
        fig.add_trace(go.Scattermap(lat=sig["lat"], lon=sig["lon"], mode="markers", hoverinfo="skip",
                                    marker=dict(size=25, color="#f0efec", opacity=0.95), showlegend=False))
    for part, size, opacity, name in ((rest, 14, 0.62, "Not significant"), (sig, 20, 1.0, "Significant")):
        if not len(part):
            continue
        fig.add_trace(go.Scattermap(
            lat=part["lat"], lon=part["lon"], mode="markers", name=name,
            marker=dict(size=size, opacity=opacity, color=part["per_decade"], colorscale=C.DIVERGING,
                        cmin=-zmax, cmax=zmax, showscale=(name == "Significant"),
                        colorbar=dict(title=dict(text=f"{v.unit}<br>per decade", font=dict(size=11, color=C.INK_2)),
                                      thickness=10, len=0.4, tickfont=dict(color=C.INK_2, size=11), x=0.985, xanchor="right",
                                      y=0.3, yanchor="middle", outlinewidth=0, bgcolor="rgba(13,13,13,0.7)",
                                      xpad=10, ypad=10)),
            customdata=np.c_[part["name"], part["p"], part["biome"]],
            hovertemplate=("<b>%{customdata[0]}</b> (%{customdata[2]})<br>"
                           f"%{{marker.color:+,.{v.decimals}f}} {v.unit} per decade<br>p = %{{customdata[1]:.3f}}<extra></extra>")))
    if selected is not None and selected in set(df["name"]):
        row = df[df["name"] == selected].iloc[0]
        fig.add_trace(go.Scattermap(lat=[row["lat"]], lon=[row["lon"]], mode="markers+text", text=[row["name"]],
                                    textposition="top center", textfont=dict(size=13, color="#ffffff"),
                                    marker=dict(size=8, color="#ffffff"), hoverinfo="skip", showlegend=False))
    if events is not None and len(events):
        palette = {"Wildfires": "#ffb347", "Sea and Lake Ice": "#8fd3ff", "Severe Storms": C.VIOLET,
                   "Volcanoes": "#ff6b6b"}
        for cat, grp in events.groupby("category"):
            fig.add_trace(go.Scattermap(
                lat=grp["lat"], lon=grp["lon"], mode="markers", name=f"Live: {cat.lower()}",
                marker=dict(size=7, color=palette.get(cat, C.INK_2), opacity=0.9),
                customdata=np.c_[grp["title"], grp["date"]],
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>"))
    layout = _layout(height=520, margin=dict(l=0, r=0, t=0, b=0))
    layout["legend"] = dict(orientation="h", yanchor="top", y=0.99, xanchor="left", x=0.01,
                            bgcolor="rgba(13,13,13,0.7)", font=dict(size=12, color=C.INK))
    layout["map"] = dict(center=dict(lat=22, lon=10), zoom=0.9,
                         style="white-bg" if satellite else "carto-darkmatter",
                         layers=([dict(sourcetype="raster", source=[GIBS_TILES], below="traces", opacity=0.92)]
                                 if satellite else []))
    fig.update_layout(**layout)
    return fig


def trend_bars_figure(df: pd.DataFrame, v: Variable) -> go.Figure:
    """Same data as the map, ranked: easiest way to see opposite signs side by side."""
    d = df.sort_values("per_decade")
    colors = [C.RISE if x > 0 else C.FALL for x in d["per_decade"]]
    fig = go.Figure(go.Bar(
        y=d["name"], x=d["per_decade"], orientation="h",
        marker=dict(color=colors, opacity=[1.0 if s else 0.35 for s in d["significant"]], cornerradius=4),
        customdata=np.c_[d["p"]],
        hovertemplate=f"%{{y}}: %{{x:+,.{v.decimals}f}} {v.unit} per decade<br>p = %{{customdata[0]:.3f}}<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=C.LINE_STRONG, width=1))
    fig.update_layout(**_layout(height=max(360, 24 * len(d) + 60), margin=dict(l=8, r=16, t=8, b=8),
                                xaxis_title=f"{v.unit} per decade", showlegend=False, bargap=0.3,
                                yaxis=dict(showgrid=False, tickfont=dict(color=C.INK_2, size=12), automargin=True)))
    return fig


def correlation_figure(corr: pd.DataFrame) -> go.Figure:
    """Heatmap of month-to-month link strength between every pair of variables."""
    names = [VARIABLES[c].name for c in corr.columns]
    fig = go.Figure(go.Heatmap(
        z=corr.to_numpy(), x=names, y=names, zmin=-1, zmax=1, colorscale=C.DIVERGING,
        colorbar=dict(title=dict(text="Link", font=dict(size=11, color=C.INK_2)), thickness=10, outlinewidth=0,
                      tickfont=dict(color=C.MUTED, size=11)),
        hovertemplate="%{y} vs %{x}<br>link strength %{z:+.2f}<extra></extra>", xgap=1, ygap=1))
    fig.update_layout(**_layout(height=620, margin=dict(l=8, r=8, t=8, b=8),
                                xaxis=dict(tickangle=-45, showgrid=False, tickfont=dict(size=11, color=C.INK_2), automargin=True,
                                           side="bottom"),
                                yaxis=dict(autorange="reversed", showgrid=False, tickfont=dict(size=11, color=C.INK_2),
                                           automargin=True)))
    return fig
