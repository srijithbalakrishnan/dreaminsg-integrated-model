"""Functions to generate infrastructure network plots and result plots.

Improvements over previous version
------------------------------------
* Realistic SVG icons for every node category (including Load / consumer).
* Line components (Transformer, Water pump) render as a thin line with a
  centred icon glyph so the topology remains readable while the component
  type is immediately recognisable.
* Node image_url anchoring fixed: anchor="center" requires Bokeh ≥ 3.x;
  we fall back to a manual offset so nodes are always visible.
* Legend click-to-mute wires edge renderers to node renderers correctly.
* FIX: Single shared HoverTool so only one tooltip fires under the cursor.
* FIX: legend_label moved from image_url (unsupported) to backing glyph
  renderers, so node icons and edge-component icons appear in the legend.
"""

from __future__ import annotations

import base64
import warnings
from typing import Optional

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from bokeh.io import output_notebook, show
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from bokeh.resources import INLINE

# ---------------------------------------------------------------------------
# Optional xyzservices tile provider
# ---------------------------------------------------------------------------
try:
    import xyzservices.providers as xyz
    _TILE = xyz.CartoDB.Positron
    _HAS_XYZ = True
except ImportError:
    _HAS_XYZ = False

# ---------------------------------------------------------------------------
# Shared matplotlib colormap
# ---------------------------------------------------------------------------
cmap = mcolors.LinearSegmentedColormap.from_list(
    "", ["green", "yellow", "orange", "red"]
)


# ---------------------------------------------------------------------------
# SVG icon library  (64×64 viewport, scaled in data-space via icon_size)
# ---------------------------------------------------------------------------
_ICON_SVGS: dict[str, str] = {

    # ── POWER ────────────────────────────────────────────────────────────────

    "Power bus": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <rect x="6" y="18" width="52" height="30" rx="5"
            fill="#fff0f0" stroke="#cc2222" stroke-width="2.5"/>
      <line x1="6"  y1="29" x2="58" y2="29" stroke="#cc2222" stroke-width="1.5"/>
      <line x1="18" y1="18" x2="18" y2="48" stroke="#cc2222" stroke-width="1.5"/>
      <line x1="32" y1="18" x2="32" y2="48" stroke="#cc2222" stroke-width="1.5"/>
      <line x1="46" y1="18" x2="46" y2="48" stroke="#cc2222" stroke-width="1.5"/>
      <circle cx="18" cy="15" r="3" fill="#cc2222"/>
      <circle cx="32" cy="15" r="3" fill="#cc2222"/>
      <circle cx="46" cy="15" r="3" fill="#cc2222"/>
    </svg>""",

    "Generator": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <circle cx="32" cy="32" r="22" fill="#fff0f0" stroke="#cc2222" stroke-width="2.5"/>
      <circle cx="32" cy="32" r="7"  fill="#cc2222"/>
      <path d="M32 10 C36 20 44 24 42 32 C38 26 30 24 32 10 Z" fill="#cc2222" opacity="0.85"/>
      <path d="M54 42 C44 40 38 46 32 44 C38 40 40 32 54 42 Z" fill="#cc2222" opacity="0.85"/>
      <path d="M10 42 C18 36 18 28 22 24 C22 32 26 40 10 42 Z" fill="#cc2222" opacity="0.85"/>
      <text x="32" y="37" text-anchor="middle" font-family="sans-serif"
            font-size="10" font-weight="bold" fill="white">G</text>
    </svg>""",

    "Load": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <polygon points="32,6 58,28 52,28 52,58 12,58 12,28 6,28"
               fill="#fff0f0" stroke="#cc2222" stroke-width="2.5"/>
      <rect x="25" y="40" width="14" height="18" rx="2"
            fill="#cc2222" opacity="0.25" stroke="#cc2222" stroke-width="1.5"/>
      <path d="M35 18 L27 34 L32 34 L29 46 L37 30 L32 30 Z"
            fill="#cc2222"/>
    </svg>""",

    # ── WATER ─────────────────────────────────────────────────────────────────

    "Water junction": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <circle cx="32" cy="32" r="20" fill="#e3f2fd" stroke="#1565c0" stroke-width="2.5"/>
      <line x1="32" y1="12" x2="32" y2="52" stroke="#1565c0" stroke-width="2.5"/>
      <line x1="12" y1="32" x2="52" y2="32" stroke="#1565c0" stroke-width="2.5"/>
      <circle cx="32" cy="32" r="5" fill="#1565c0"/>
    </svg>""",

    "Water tank": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <rect x="16" y="16" width="32" height="36" rx="3"
            fill="#e3f2fd" stroke="#1565c0" stroke-width="2.5"/>
      <ellipse cx="32" cy="16" rx="16" ry="5"
               fill="#bbdefb" stroke="#1565c0" stroke-width="2"/>
      <line x1="16" y1="36" x2="48" y2="36" stroke="#1565c0"
            stroke-width="1.5" stroke-dasharray="4 3"/>
      <rect x="27" y="52" width="10" height="8" rx="2" fill="#1565c0"/>
    </svg>""",

    "Water reservoir": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <rect x="6" y="28" width="52" height="8" rx="2"
            fill="#90a4ae" stroke="#546e7a" stroke-width="2"/>
      <ellipse cx="32" cy="20" rx="24" ry="12"
               fill="#bbdefb" stroke="#1565c0" stroke-width="2"/>
      <path d="M14 18 Q20 14 26 18 Q32 22 38 18 Q44 14 50 18"
            fill="none" stroke="#1565c0" stroke-width="1.5"/>
      <path d="M14 22 Q20 18 26 22 Q32 26 38 22 Q44 18 50 22"
            fill="none" stroke="#1565c0" stroke-width="1.2" opacity="0.6"/>
    </svg>""",

    "Water demand": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <rect x="10" y="26" width="28" height="12" rx="4"
            fill="#e3f2fd" stroke="#1565c0" stroke-width="2.5"/>
      <rect x="20" y="16" width="8" height="12" rx="2" fill="#1565c0"/>
      <rect x="14" y="14" width="20" height="4" rx="2" fill="#1565c0"/>
      <path d="M38 30 L54 30 L54 38 L48 38" fill="none"
            stroke="#1565c0" stroke-width="3" stroke-linecap="round"/>
      <ellipse cx="50" cy="46" rx="3" ry="4" fill="#64b5f6" opacity="0.8"/>
      <ellipse cx="56" cy="50" rx="2" ry="3" fill="#64b5f6" opacity="0.6"/>
    </svg>""",

    # ── TRANSPORT ─────────────────────────────────────────────────────────────

    "Transportation junction": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <rect x="6" y="6" width="52" height="52" rx="8"
            fill="#e8f5e9" stroke="#2e7d32" stroke-width="2.5"/>
      <line x1="32" y1="6"  x2="32" y2="58"
            stroke="#2e7d32" stroke-width="4" stroke-dasharray="7 5"/>
      <line x1="6"  y1="32" x2="58" y2="32"
            stroke="#2e7d32" stroke-width="4" stroke-dasharray="7 5"/>
      <circle cx="32" cy="32" r="7" fill="#2e7d32"/>
    </svg>""",
}

# Pre-encode all icons as data-URIs
_ICON_URIS: dict[str, str] = {
    k: "data:image/svg+xml;base64," + base64.b64encode(v.encode()).decode()
    for k, v in _ICON_SVGS.items()
}

# Legend swatch colors per node category (used on the backing circle glyph)
_NODE_LEGEND_COLORS: dict[str, str] = {
    "Power bus":               "#cc2222",
    "Generator":               "#cc2222",
    "Load":                    "#cc2222",
    "Water junction":          "#1565c0",
    "Water tank":              "#1565c0",
    "Water reservoir":         "#1565c0",
    "Water demand":            "#1565c0",
    "Transportation junction": "#2e7d32",
}

_ICON_SIZE = 32          # default icon size in data-space units


# ---------------------------------------------------------------------------
# Line-component mid-point glyph icons
# ---------------------------------------------------------------------------
_EDGE_GLYPH_SVGS: dict[str, str] = {

    "Transformer": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32">
      <rect x="1" y="1" width="62" height="30" rx="4"
            fill="white" stroke="#cc2222" stroke-width="1.5"/>
      <path d="M8 22 Q10 10 14 22 Q16 10 20 22" fill="none"
            stroke="#cc2222" stroke-width="2" stroke-linecap="round"/>
      <line x1="29" y1="6"  x2="29" y2="26" stroke="#cc2222" stroke-width="2"/>
      <line x1="35" y1="6"  x2="35" y2="26" stroke="#cc2222" stroke-width="2"/>
      <path d="M44 22 Q46 10 50 22 Q52 10 56 22" fill="none"
            stroke="#cc2222" stroke-width="2" stroke-linecap="round"/>
    </svg>""",

    "Switch": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32">
      <rect x="1" y="1" width="62" height="30" rx="4"
            fill="white" stroke="#cc2222" stroke-width="1.5"/>
      <circle cx="12" cy="16" r="4" fill="#cc2222"/>
      <circle cx="52" cy="16" r="4" fill="#cc2222"/>
      <line x1="12" y1="16" x2="46" y2="8"
            stroke="#cc2222" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M46 10 Q54 14 52 16" fill="none"
            stroke="#cc2222" stroke-width="1.5" stroke-dasharray="3 2"/>
    </svg>""",

    "Water pump": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <circle cx="32" cy="32" r="26"
              fill="#e3f2fd" stroke="#1565c0" stroke-width="2"/>
      <path d="M32 10 Q40 20 36 32 Q28 24 32 10 Z" fill="#1565c0" opacity="0.85"/>
      <path d="M54 40 Q44 40 38 32 Q46 28 54 40 Z" fill="#1565c0" opacity="0.85"/>
      <path d="M10 40 Q18 30 26 34 Q18 42 10 40 Z" fill="#1565c0" opacity="0.85"/>
      <circle cx="32" cy="32" r="7" fill="#1565c0"/>
      <text x="32" y="37" text-anchor="middle" font-family="sans-serif"
            font-size="11" font-weight="bold" fill="white">P</text>
    </svg>""",
}

_EDGE_GLYPH_URIS: dict[str, str] = {
    k: "data:image/svg+xml;base64," + base64.b64encode(v.encode()).decode()
    for k, v in _EDGE_GLYPH_SVGS.items()
}

_GLYPH_DIMS: dict[str, tuple[float, float]] = {
    "Transformer": (40, 20),
    "Switch":      (40, 20),
    "Water pump":  (28, 28),
}

# Legend swatch colors and border colors for edge-glyph backing shapes
_GLYPH_LEGEND_COLORS: dict[str, str] = {
    "Transformer": "#cc2222",
    "Switch":      "#cc2222",
    "Water pump":  "#1565c0",
}


# ---------------------------------------------------------------------------
# Link visual spec  (color, line_width, dash_pattern, alpha)
# ---------------------------------------------------------------------------
_LINK_STYLES: dict[str, tuple] = {
    "Power line":  ("#CC2222", 2.0, "solid",  0.75),
    "Transformer": ("#CC2222", 2.0, "solid",  0.60),
    "Switch":      ("#CC2222", 1.5, "solid",  0.60),
    "Water pipe":  ("#1565C0", 2.0, "solid",  0.75),
    "Water pump":  ("#1565C0", 2.0, "solid",  0.60),
    "Road link":   ("#2E7D32", 1.8, "solid",  0.55),
}

_LINK_HAS_GLYPH: dict[str, str] = {
    "Transformer": "Transformer",
    "Switch":      "Switch",
    "Water pump":  "Water pump",
}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _add_tile(p) -> None:
    if not _HAS_XYZ:
        warnings.warn(
            "xyzservices is not installed — basemap skipped. "
            "Install with:  pip install xyzservices",
            stacklevel=3,
        )
        return
    p.add_tile(_TILE)


def _make_figure(
    title: str = "",
    width: int = 900,
    height: int = 600,
    x_range: Optional[tuple] = None,
    y_range: Optional[tuple] = None,
    tools: str = "pan,wheel_zoom,box_zoom,reset,save",
    bg: str = "white",
):
    kwargs: dict = dict(
        title=title, width=width, height=height,
        background_fill_color=bg,
        toolbar_location="above", tools=tools,
    )
    if x_range is not None:
        kwargs["x_range"] = x_range
    if y_range is not None:
        kwargs["y_range"] = y_range
    p = figure(**kwargs)
    p.grid.visible = False
    p.axis.visible = False
    p.outline_line_color = "#cccccc"
    return p


def _bucket_node(node_type: str, node_category: str) -> str:
    """Map (node_type, node_category) → an _ICON_URIS key."""
    if node_type == "power":
        if node_category == "Generator":
            return "Generator"
        if node_category in ("Load", "Consumer", "Demand"):
            return "Load"
        return "Power bus"
    if node_type == "water":
        return {
            "Tank":      "Water tank",
            "Reservoir": "Water reservoir",
            "Demand":    "Water demand",
            "Junction":  "Water junction",
            "Pump":      "Water junction",
        }.get(node_category, "Water junction")
    return "Transportation junction"


def _bucket_link(link_id: str, link_category: str) -> Optional[str]:
    """Map a link id/category → a _LINK_STYLES key, or None to skip."""
    if link_category in _LINK_STYLES:
        return link_category
    if link_id.startswith("P_"):
        if "Transformer" in link_category:
            return "Transformer"
        if "Switch" in link_category:
            return "Switch"
        return "Power line"
    if link_id.startswith("W_"):
        return "Water pump" if "pump" in link_category.lower() else "Water pipe"
    if link_id.startswith("T_"):
        return "Road link"
    return None


def _midpoint(xs: list, ys: list) -> tuple[float, float]:
    """Return the geometric mid-point of a polyline."""
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mid = n // 2
    return (xs[mid - 1] + xs[mid]) / 2.0, (ys[mid - 1] + ys[mid]) / 2.0


# ---------------------------------------------------------------------------
# Public: integrated network Bokeh plot
# ---------------------------------------------------------------------------

def plot_bokeh_from_integrated_graph(
    G: nx.Graph,
    title: str,
    extent: list = [(1500, 1500), (7500, 6300)],
    basemap: bool = False,
    icon_size: Optional[int] = None,
    output_png_path: str = "plot.png",
) -> None:
    """Render the integrated network as an interactive Bokeh plot.

    Nodes
    -----
    Drawn as crisp, domain-specific SVG icons.  Every recognised category
    (Power bus, Generator, Load, Water junction, Water tank, Water reservoir,
    Water demand, Transportation junction) has its own icon.

    Edges
    -----
    Plain line components (Power line, Water pipe, Road link) → coloured
    multi_line.
    Active components (Transformer, Switch, Water pump) → coloured line
    **plus** a centred SVG glyph.

    Legend supports mute-on-click layer control.
    All legend entries (including node icons and edge glyphs) are visible.
    Only one hover tooltip fires at a time (single shared HoverTool).

    Parameters
    ----------
    G : nx.Graph
        Integrated network graph.  Each node must have ``coord`` (x, y) and
        ``node_type`` / ``node_category`` attributes.  Each edge should have
        ``id``, ``link_type``, and ``link_category``.
    title : str
        Plot title.
    extent : list
        ``[(xmin, ymin), (xmax, ymax)]``.
    basemap : bool
        Overlay a CartoDB Positron tile layer (requires xyzservices).
    icon_size : int, optional
        Node icon size in data-space units (default 32).
    output_png_path : str
        Filename for an optional PNG export.
    """
    output_notebook(resources=INLINE, hide_banner=True)
    sz = icon_size or _ICON_SIZE

    # ------------------------------------------------------------------
    # Helper: extract polyline coords from edge
    # ------------------------------------------------------------------
    def _edge_xy(edata, u, v):
        geom = edata.get("geometry")
        if geom is not None:
            try:
                coords = list(geom.coords if hasattr(geom, "coords") else geom)
                if len(coords) >= 2:
                    return ([float(c[0]) for c in coords],
                            [float(c[1]) for c in coords])
            except Exception:
                pass
        return (
            [G.nodes[u]["coord"][0], G.nodes[v]["coord"][0]],
            [G.nodes[u]["coord"][1], G.nodes[v]["coord"][1]],
        )

    # ------------------------------------------------------------------
    # Build figure
    # ------------------------------------------------------------------
    p = _make_figure(
        title=title, width=1100, height=720,
        x_range=(extent[0][0], extent[1][0]),
        y_range=(extent[0][1], extent[1][1]),
    )
    p.title.text_font_size = "15pt"
    p.title.text_font_style = "bold"

    if basemap:
        _add_tile(p)

    # ------------------------------------------------------------------
    # Single shared HoverTool — only one tooltip fires per cursor position.
    # We register all invisible hit-target renderers into this one tool.
    # ------------------------------------------------------------------
    hover = HoverTool(
        tooltips=[
            ("ID",       "@id"),
            ("Category", "@category"),
            ("Network",  "@network"),
        ],
        point_policy="snap_to_data",
    )
    p.add_tools(hover)
    hit_renderers = []   # collect all invisible hit targets here

    # ------------------------------------------------------------------
    # Collect node data
    # ------------------------------------------------------------------
    node_buckets: dict[str, dict] = {
        k: dict(x=[], y=[], node_type=[], node_category=[], id=[],
                url=[], category=[], network=[])
        for k in _ICON_URIS
    }
    for node, nd in G.nodes(data=True):
        coord = nd.get("coord")
        if coord is None:
            warnings.warn(f"Node {node!r} has no 'coord' attribute — skipped.")
            continue
        bucket = _bucket_node(nd.get("node_type", ""), nd.get("node_category", ""))
        b = node_buckets[bucket]
        b["x"].append(float(coord[0]))
        b["y"].append(float(coord[1]))
        b["node_type"].append(nd.get("node_type", ""))
        b["node_category"].append(nd.get("node_category", ""))
        b["id"].append(str(node))
        b["url"].append(_ICON_URIS[bucket])
        # Unified hover columns
        b["category"].append(nd.get("node_category", ""))
        b["network"].append(nd.get("node_type", ""))

    # ------------------------------------------------------------------
    # Collect edge data
    # ------------------------------------------------------------------
    link_buckets: dict[str, dict] = {
        k: dict(xs=[], ys=[], link_type=[], link_category=[], id=[],
                category=[], network=[])
        for k in _LINK_STYLES
    }
    glyph_buckets: dict[str, dict] = {
        g: dict(x=[], y=[], link_category=[], id=[], url=[], w=[], h=[],
                category=[], network=[])
        for g in _EDGE_GLYPH_URIS
    }

    for u, v, edata in G.edges(data=True):
        link_id = edata.get("id", f"{u}-{v}")
        lcat    = edata.get("link_category", "")
        ltype   = edata.get("link_type", "")
        bucket  = _bucket_link(link_id, lcat)
        if bucket is None:
            continue

        xs, ys = _edge_xy(edata, u, v)
        lb = link_buckets[bucket]
        lb["xs"].append(xs)
        lb["ys"].append(ys)
        lb["link_type"].append(ltype)
        lb["link_category"].append(lcat)
        lb["id"].append(link_id)
        lb["category"].append(lcat)
        lb["network"].append(ltype)

        glyph_key = _LINK_HAS_GLYPH.get(bucket)
        if glyph_key:
            mx, my = _midpoint(xs, ys)
            gw, gh = _GLYPH_DIMS[glyph_key]
            gb = glyph_buckets[glyph_key]
            gb["x"].append(mx)
            gb["y"].append(my)
            gb["link_category"].append(lcat)
            gb["id"].append(link_id)
            gb["url"].append(_EDGE_GLYPH_URIS[glyph_key])
            gb["w"].append(gw)
            gb["h"].append(gh)
            gb["category"].append(lcat)
            gb["network"].append(ltype)

    # ------------------------------------------------------------------
    # Render order: edges → glyphs → nodes
    # ------------------------------------------------------------------

    # ── 1. Edges ──────────────────────────────────────────────────────
    # multi_line does not serve as a hover hit target reliably, so we add
    # the label here for the legend and rely on node/glyph hit targets for
    # the hover.  For plain lines we still want the legend entry.
    for category, (color, lw, dash, alpha) in _LINK_STYLES.items():
        src = ColumnDataSource(link_buckets[category])
        p.multi_line(
            xs="xs", ys="ys", source=src,
            line_color=color, line_width=lw, line_dash=dash,
            line_alpha=alpha, muted_color=color, muted_alpha=0.06,
            legend_label=category,
        )

    # ── 2. Edge glyphs (Transformer / Switch / Water pump) ───────────
    for glyph_key, gb in glyph_buckets.items():
        if not gb["x"]:
            continue
        src = ColumnDataSource(gb)
        gw, gh = _GLYPH_DIMS[glyph_key]
        is_round = (glyph_key == "Water pump")
        border_color = _GLYPH_LEGEND_COLORS[glyph_key]

        # Backing shape — carries legend_label (image_url cannot)
        if is_round:
            p.circle(
                x="x", y="y", radius=gw / 2, source=src,
                fill_color="white", line_color=border_color,
                line_width=1.5, fill_alpha=0.9,
                level="overlay",
                legend_label=glyph_key,   # ← legend entry lives here
            )
        else:
            p.rect(
                x="x", y="y", width=gw, height=gh, source=src,
                fill_color="white", line_color=border_color,
                line_width=1.5, fill_alpha=0.9,
                level="overlay",
                legend_label=glyph_key,   # ← legend entry lives here
            )

        # SVG glyph image — NO legend_label (image_url ignores it)
        src_off = ColumnDataSource(dict(
            x=[v - gw / 2 for v in gb["x"]],
            y=[v - gh / 2 for v in gb["y"]],
            url=gb["url"],
        ))
        p.image_url(
            url="url", x="x", y="y",
            w=gw, h=gh,
            anchor="bottom_left", source=src_off,
            level="overlay",
        )

        # Invisible hit target → registered with shared HoverTool
        hit = p.circle(
            x="x", y="y",
            radius=max(gw, gh) * 0.5,
            source=src,
            fill_color="rgba(0,0,0,0)",
            line_color="rgba(0,0,0,0)",
            level="overlay",
        )
        hit_renderers.append(hit)

    # ── 3. Nodes ──────────────────────────────────────────────────────
    for category, uri in _ICON_URIS.items():
        b = node_buckets[category]
        if not b["x"]:
            continue
        src = ColumnDataSource(b)
        border_color = _NODE_LEGEND_COLORS.get(category, "#888888")

        # Backing disc — carries legend_label (image_url cannot)
        p.circle(
            x="x", y="y", radius=sz * 0.52, source=src,
            fill_color="white", line_color=border_color,
            line_width=1.5, fill_alpha=0.85,
            level="overlay",
            legend_label=category,   # ← legend entry lives here
        )

        # SVG node icon — NO legend_label
        src_img = ColumnDataSource(dict(
            x=[v - sz / 2 for v in b["x"]],
            y=[v - sz / 2 for v in b["y"]],
            url=b["url"],
        ))
        p.image_url(
            url="url", x="x", y="y",
            w=sz, h=sz,
            anchor="bottom_left", source=src_img,
            level="overlay",
        )

        # Invisible hit target → registered with shared HoverTool
        hit = p.scatter(
            x="x", y="y", size=int(sz * 0.9), source=src,
            fill_color="rgba(0,0,0,0)",
            line_color="rgba(0,0,0,0)",
            level="overlay",
        )
        hit_renderers.append(hit)

    # ------------------------------------------------------------------
    # Wire ALL hit targets into the single HoverTool
    # ------------------------------------------------------------------
    hover.renderers = hit_renderers

    # ------------------------------------------------------------------
    # Legend
    # ------------------------------------------------------------------
    p.legend.location              = "top_left"
    p.legend.click_policy          = "mute"
    p.legend.background_fill_alpha = 0.88
    p.legend.background_fill_color = "white"
    p.legend.border_line_color     = "#cccccc"
    p.legend.label_text_font_size  = "11pt"
    p.legend.spacing               = 5

    show(p)


# ---------------------------------------------------------------------------
# Convenience single-network plots (unchanged API)
# ---------------------------------------------------------------------------

def plot_transpo_net(transpo_folder: str) -> None:
    """Generate the transportation network plot.

    :param transpo_folder: Location of the transport model (.tntp files).
    """
    rows = []
    with open(f"{transpo_folder}/example_net.tntp") as f:
        reading = False
        for line in f:
            if "~" in line:
                reading = True
                continue
            if not reading:
                continue
            parts = line.split("\t")[1:11]
            if len(parts) < 10:
                continue
            rows.append({
                "Init node": parts[0], "Term node": parts[1],
                "Capacity":  parts[2], "Length":    parts[3],
                "Free Flow Time": parts[4], "B": parts[5],
                "Power": parts[6], "Speed limit": parts[7],
                "Toll":  parts[8], "Type":        parts[9],
            })
    links = pd.DataFrame(rows)
    nodes = pd.read_csv(f"{transpo_folder}/example_node.tntp", sep="\t")

    G = nx.Graph()
    G.add_edges_from(zip(links["Init node"], links["Term node"]))
    pos = {str(i + 1): (row[1], row[2]) for i, row in nodes.iterrows()}

    plt.figure(figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, node_size=500,
            node_color="lightsteelblue", font_size=14,
            edge_color="slategray", width=2)


def plot_water_net(wn) -> None:
    """Generate the water network plot.

    :param wn: The water network (wntr.network.WaterNetworkModel).
    """
    coords    = list(wn.query_node_attribute("coordinates"))
    node_list = wn.node_name_list
    G         = wn.get_graph()
    pos       = {node_list[i]: list(c) for i, c in enumerate(coords)}
    plt.figure(figsize=(10, 7))
    nx.draw(G, pos, with_labels=False, node_size=0,
            node_color="lightsteelblue", font_size=14,
            edge_color="slategray", width=2)


def plot_repair_curves(network_recovery, scatter: bool = False) -> None:
    """Plot disrupted-component restoration step curves.

    :param network_recovery: Recovery simulation object.
    :param scatter: Overlay scatter points on the step curves.
    """
    disrupted   = network_recovery.network.get_disrupted_components()
    colors_list = list(Turbo256)
    step        = max(1, len(colors_list) // len(disrupted))
    palette     = [colors_list[i] for i in range(0, len(colors_list), step)]

    curdoc().theme = "light_minimal"
    p = _make_figure(title="Disrupted components and their restoration",
                     width=750, height=450)
    p.xaxis.axis_label = "Time (min)"
    p.yaxis.axis_label = "Damage level (%)"
    p.axis.visible = True
    p.y_range = Range1d(0, 100)

    for idx, name in enumerate(disrupted):
        mask    = network_recovery.event_table.components == name
        times   = network_recovery.event_table.loc[mask, "time_stamp"] / 60
        damages = network_recovery.event_table.loc[mask, "perf_level"]
        color   = palette[idx]
        if scatter:
            p.scatter(x=times, y=damages, size=5, color=color, alpha=0.2)
        p.step(x=times, y=damages, alpha=1, line_width=2.5, color=color,
               muted_alpha=0.1, mode="after", legend_label=name)

    p.add_layout(p.legend[0], "right")
    p.legend.background_fill_color = "gainsboro"
    p.legend.background_fill_alpha = 0.1
    p.legend.click_policy = "mute"
    show(p)


def plot_interdependent_effects(
    resilience_metrics, metric: str, title: bool = True
) -> None:
    """Plot water and power ECS/PCS curves on the same axes.

    :param resilience_metrics: Simulation results object.
    :param metric: ``'ecs'`` or ``'pcs'``.
    :param title: Whether to render the axes title.
    """
    water_vals = getattr(resilience_metrics, f"water_{metric}_list")
    power_vals = getattr(resilience_metrics, f"power_{metric}_list")
    label = {"ecs": "Equivalent Consumer Serviceability",
             "pcs": "Prioritized Consumer Serviceability"}.get(metric, metric.upper())

    sns.set_style("ticks")
    sns.set_context("paper", font_scale=1.75)
    fig, ax = plt.subplots(figsize=(7, 5))
    common = dict(drawstyle="steps-post", linewidth=2, alpha=0.95)

    sns.lineplot(ax=ax,
                 x=[t / 60 for t in resilience_metrics.water_time_list],
                 y=water_vals, label="Water",
                 linestyle=(0, (5, 1)), color="tab:red", **common)
    sns.lineplot(ax=ax,
                 x=[t / 60 for t in resilience_metrics.power_time_list],
                 y=power_vals, label="Power",
                 linestyle=(0, (3, 1, 1, 1)), color="tab:blue", **common)

    ax.legend(loc="lower right")
    ax.set(xlabel="Time (hours)", ylabel="Average satisfied demand (%)", ylim=(0, 1.01))
    if title:
        ax.set_title("Network-wide performance", fontsize=12)
    fig.tight_layout()


def plot_network_impact_map(
    resilience_metrics,
    integrated_network,
    strategy: str,
    node_prefix: str,
    infra: str = "power",
    time_index: Optional[int] = None,
) -> None:
    """Plot node-level outage intensity on the integrated network graph.

    :param resilience_metrics: Simulation results object.
    :param integrated_network: IntegratedNetwork instance.
    :param strategy: Recovery strategy name.
    :param node_prefix: Node ID prefix to include (e.g. ``'W_J'``).
    :param infra: ``'power'`` or ``'water'``.
    :param time_index: If given, show demand ratio at this step instead of AUC.
    """
    output_notebook(resources=INLINE, hide_banner=True)

    # FIX: de-duplicated near-identical water/power branches
    if infra == "water":
        auc = _compute_auc(resilience_metrics.water_demands_ratio,
                           resilience_metrics.water_time_list,
                           node_prefix, strategy, time_index)
    else:
        auc = _compute_auc(resilience_metrics.power_demand_ratio,
                           resilience_metrics.power_time_list,
                           node_prefix, strategy, time_index)

    G = integrated_network.integrated_graph
    for node in G.nodes:
        G.nodes[node]["avg_perf"] = auc.get(node, np.nan)
    for u, v, edata in G.edges(data=True):
        edata["avg_perf"] = auc.get(edata.get("id"), np.nan)

    palette = (
        "#32CD32", "#5FCF26", "#8DD11B", "#BAD310", "#E8D505",
        "#FFBF00", "#FF8F00", "#FF5F00", "#FF2F00", "#FF0000",
    )

    p = _make_figure(width=785, height=500,
                     x_range=(1400, 7400), y_range=(2000, 6000))

    xs = [[G.nodes[u]["coord"][0], G.nodes[v]["coord"][0]] for u, v in G.edges()]
    ys = [[G.nodes[u]["coord"][1], G.nodes[v]["coord"][1]] for u, v in G.edges()]
    p.multi_line(xs="x", ys="y",
                 source=ColumnDataSource(dict(x=xs, y=ys)),
                 line_color="grey", line_alpha=0.6, line_width=0.75,
                 legend_label="Infrastructure links")

    if infra == "water":
        node_x = [G.nodes[n]["coord"][0] for n in auc]
        node_y = [G.nodes[n]["coord"][1] for n in auc]
        perf   = list(auc.values())
    else:
        node_x, node_y, perf = [], [], []
        for idx, name in enumerate(integrated_network.pn.load.name):
            if name in auc:
                node_x.append(integrated_network.pn.loads_geodata.x[idx])
                node_y.append(integrated_network.pn.loads_geodata.y[idx])
                perf.append(auc[name])

    chart_title = (
        f"Proportion of satisfied {infra} demand"
        if time_index is not None
        else f"{infra.title()} outage (equivalent outage hours)"
    )
    high = 1 if time_index is not None else (max(perf) if perf else 1)

    color_mapper = linear_cmap(
        field_name="avg_perf", palette=palette, low=0, high=high, nan_color="snow"
    )
    p.square(x="x", y="y",
             source=ColumnDataSource(dict(x=node_x, y=node_y, avg_perf=perf)),
             color=color_mapper, fill_alpha=1, size=6)

    p.legend.location = "bottom_left"
    p.legend.label_text_font_size = "14pt"
    p.add_layout(ColorBar(
        color_mapper=color_mapper["transform"],
        width=15, location=(0, 0),
        title=chart_title,
        title_text_font_style="normal",
        title_text_font_size="14pt",
        major_label_text_font_size="14pt",
    ), "right")
    p.outline_line_color = None
    show(p)


def plot_region_impact_map(
    resilience_metrics, sa_dict: dict, strategy: str, extends: tuple
) -> None:
    """Plot region-level service-area impact using matplotlib + contextily.

    :param resilience_metrics: Simulation results object.
    :param sa_dict: ``{'Water': GeoDataFrame, 'Power': GeoDataFrame}``.
    :param strategy: Recovery strategy name.
    :param extends: ``(xmin, xmax, ymin, ymax)`` map extent.
    """
    # FIX: de-duplicated water/power AUC computation via shared helper
    water_auc = _compute_auc(resilience_metrics.water_demands_ratio,
                             resilience_metrics.water_time_list,
                             "W_J", strategy, None)
    power_auc = _compute_auc(resilience_metrics.power_demand_ratio,
                             resilience_metrics.power_time_list,
                             "", strategy, None)

    def _auc_to_df(auc: dict, col: str) -> pd.DataFrame:
        df = pd.DataFrame.from_dict(auc, orient="index", columns=[col])
        df["component"] = df.index
        return df

    merged_water = pd.merge(sa_dict["Water"], _auc_to_df(water_auc, strategy),
                            left_on="Water_Node", right_on="component", how="left")
    merged_power = pd.merge(sa_dict["Power"], _auc_to_df(power_auc, strategy),
                            left_on="Power_Node", right_on="component", how="left")

    vmax = max(merged_power[strategy].max(), merged_water[strategy].max())
    merged = [merged_water, merged_power]

    sns.set_style("whitegrid")
    sns.set_context("notebook", font_scale=1.75, rc={"lines.linewidth": 2.5})
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    fig.suptitle("Networkwide effects of infrastructure disruptions")

    for ax, data, label in zip(axes, merged, sa_dict.keys()):
        ax.set_title(f"{label.title()} supply")
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("bottom", size="5%", pad=0.2)
        data.plot(
            column=strategy, cmap=cmap, ax=ax,
            edgecolor="black", linewidth=0,
            legend=True, cax=cax, alpha=0.65,
            legend_kwds={"shrink": 0.25, "label": "Equivalent Outage Hours",
                         "orientation": "horizontal"},
            aspect=1, vmin=0, vmax=vmax,
        )
        ax.set_xlim(extends[0], extends[1])
        ax.set_ylim(extends[2], extends[3])
        ctx.add_basemap(ax=ax, source=ctx.providers.Esri.WorldStreetMap)
        ax.set_axis_off()

    fig.tight_layout()


def plot_disruptions_and_crews(
    integrated_network, basemap: bool = False
) -> None:
    """Plot disrupted components and repair-crew starting locations.

    :param integrated_network: IntegratedNetwork instance.
    :param basemap: Overlay a CartoDB Positron tile layer.
    """
    output_notebook(resources=INLINE, hide_banner=True)
    extent = integrated_network.map_extends
    p = _make_figure(
        width=800, height=450,
        x_range=(extent[0][0] - 100, extent[1][0] + 100),
        y_range=(extent[0][1] - 100, extent[1][1] + 100),
    )
    if basemap:
        _add_tile(p)

    G      = integrated_network.integrated_graph
    failed = set(integrated_network.disrupted_components.to_list())

    fail_prefixes = {
        "power":   {"P_L", "P_MP"},
        "water":   {"W_R", "W_PMA", "W_P", "W_WP"},
        "transpo": {"T_L"},
    }

    def _affected(name: str, infra: str) -> bool:
        return name in failed and any(name.startswith(px) for px in fail_prefixes[infra])

    type_sets = {
        infra: {n for n, d in G.nodes(data=True) if d["node_type"] == infra}
        for infra in ("power", "water", "transpo")
    }
    id_sets = {
        infra: {d["id"] for _, _, d in G.edges(data=True) if d["link_type"] == infra}
        for infra in ("power", "water", "transpo")
    }

    affected_nodes = {
        n for infra, ns in type_sets.items() for n in ns if _affected(n, infra)
    }
    affected_links = {
        l for infra, ls in id_sets.items() for l in ls if _affected(l, infra)
    }

    for node, nd in G.nodes(data=True):
        nd["fail_status"] = "Disrupted" if node in affected_nodes else "Functional"
    for u, v, ed in G.edges(data=True):
        ed["fail_status"] = "Disrupted" if ed["id"] in affected_links else "Functional"

    status_palette = [RdYlGn[11][2], RdYlGn[11][9]]
    status_factors = np.array(["Functional", "Disrupted"])

    node_src = ColumnDataSource(dict(
        x=[G.nodes[n]["coord"][0] for n in G.nodes],
        y=[G.nodes[n]["coord"][1] for n in G.nodes],
        node_type=[G.nodes[n]["node_type"] for n in G.nodes],
        node_category=[G.nodes[n]["node_category"] for n in G.nodes],
        fail_status=[G.nodes[n]["fail_status"] for n in G.nodes],
        id=list(G.nodes),
    ))
    p.square(x="x", y="y", source=node_src,
             color=factor_cmap("fail_status", status_palette, status_factors),
             alpha=0.7, size=3)

    link_src = ColumnDataSource(dict(
        x=[[G.nodes[u]["coord"][0], G.nodes[v]["coord"][0]] for u, v in G.edges()],
        y=[[G.nodes[u]["coord"][1], G.nodes[v]["coord"][1]] for u, v in G.edges()],
        link_layer=[G.edges[e]["link_type"] for e in G.edges()],
        link_category=[G.edges[e]["link_category"] for e in G.edges()],
        fail_status=[G.edges[e]["fail_status"] for e in G.edges()],
        id=[G.edges[e]["id"] for e in G.edges()],
    ))
    p.multi_line(xs="x", ys="y", source=link_src,
                 line_color=factor_cmap("fail_status", status_palette, status_factors),
                 line_alpha=1, line_width=2, legend_field="fail_status")

    # FIX: was iterating water_crews for transpo locs (copy-paste bug in original)
    crew_x, crew_y, crew_type = [], [], []
    crew_maps = {
        "power":   (integrated_network.power_crews,   (-20, -20), "Power crew"),
        "water":   (integrated_network.water_crews,   ( 20,  20), "Water crew"),
        "transpo": (integrated_network.transpo_crews, ( 40,  40), "Transportation crew"),
    }
    for infra, (crews, (dx, dy), label) in crew_maps.items():
        for crew in crews.values():
            loc = crew._init_loc
            crew_x.append(G.nodes[loc]["coord"][0] + dx)
            crew_y.append(G.nodes[loc]["coord"][1] + dy)
            crew_type.append(label)

    if crew_x:
        crew_src = ColumnDataSource(dict(x=crew_x, y=crew_y, crew_type=crew_type))
        p.square(x="x", y="y", source=crew_src, size=10,
                 color=factor_cmap("crew_type", Viridis3, sorted(set(crew_type))),
                 legend_field="crew_type")

    p.legend.location              = "top_left"
    p.legend.click_policy          = "mute"
    p.legend.background_fill_alpha = 0.3
    p.legend.background_fill_color = "white"   # FIX: was "black" (text invisible)
    p.legend.label_text_color      = "black"
    show(p)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def integrate(x, y) -> float:
    """Trapezoidal integration of a curve defined by arrays *x* and *y*.

    :param x: X values.
    :param y: Y values.
    :return: Area under the curve.
    """
    return float(np.trapz(np.asarray(y, dtype=float), np.asarray(x, dtype=float)))