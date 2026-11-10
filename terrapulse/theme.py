"""Design tokens shared by the CSS and the charts (dark surface, validated palette)."""

# Surfaces and ink
BG = "#0d0d0d"
SURFACE = "#1a1a19"
SURFACE_2 = "#222220"
LINE = "#2c2c2a"          # hairlines, gridlines
LINE_STRONG = "#383835"   # borders, baselines
INK = "#f0efec"
INK_2 = "#c3c2b7"
MUTED = "#898781"

# Categorical series (dark steps of the reference palette; first three validated all-pairs)
BLUE = "#3987e5"
ORANGE = "#d95926"
AQUA = "#199e70"
VIOLET = "#9085e9"

# Direction of change: diverging pair with a neutral midpoint. Colour = direction, never "good/bad".
RISE = "#e66767"
FALL = "#3987e5"
NEUTRAL = "#383835"
DIVERGING = [[0.0, FALL], [0.5, NEUTRAL], [1.0, RISE]]

# Accent for interface chrome (focus, primary actions); not used for data
ACCENT = "#2fbf8f"

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
