"""Color utilities for Plotly discrete colorscales.

Provides helpers to sample n distinct colors from a Matplotlib colormap,
convert colors to Plotly strings and construct stepped (discrete) Plotly
colorscales suitable for heatmaps with categorical integer labels.
"""
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Union
import numpy as np
from matplotlib import colormaps

ColorLike = Union[str, Tuple[float, float, float], Tuple[float, float, float, float]]


def get_nclusters_cmap(
    cmap_name: str,
    n_clusters: int,
    index_order: Sequence[int] | None = None,
) -> List[Tuple[float, float, float, float]]:
    """Return exactly ``n_clusters`` RGBA color tuples sampled from the named
    Matplotlib colormap.

    By default this samples ``n_clusters`` positions evenly across the colormap
    range. Optionally, an ``index_order`` may be supplied: this is a sequence
    of integer indices that select colors from a discrete colormap (for
    example Matplotlib's ``tab20`` family). When provided, colors are taken in
    the order specified by ``index_order`` and repeated/cycled if
    ``n_clusters`` is larger than the order length.
    """
    cmap = colormaps.get_cmap(cmap_name)

    # If the Matplotlib colormap exposes a .colors sequence (ListedColormap),
    # use it directly so discrete palettes like 'tab20' preserve their entries.
    base_colors: List[Tuple[float, float, float, float]] = []
    if hasattr(cmap, 'colors'):
        try:
            colors_attr = getattr(cmap, 'colors')
            for c in colors_attr:
                color_tuple = tuple(map(float, c))
                if len(color_tuple) == 3:
                    base_colors.append((color_tuple[0], color_tuple[1], color_tuple[2], 1.0))
                elif len(color_tuple) >= 4:
                    base_colors.append((color_tuple[0], color_tuple[1], color_tuple[2], color_tuple[3]))
        except Exception:
            base_colors = []

    # If we don't have a discrete list, sample a grid sized to the request.
    # Use the requested number of clusters and the index_order maximum (if any)
    # rather than a hard-coded constant.
    if not base_colors:
        required = n_clusters
        if index_order:
            required = max(required, max(index_order) + 1)
        resolution = max(required, 1)
        base_colors = []
        for p in np.linspace(0.0, 1.0, resolution):
            color = cmap(p)
            color_tuple = tuple(map(float, color))
            if len(color_tuple) == 3:
                base_colors.append((color_tuple[0], color_tuple[1], color_tuple[2], 1.0))
            elif len(color_tuple) >= 4:
                base_colors.append((color_tuple[0], color_tuple[1], color_tuple[2], color_tuple[3]))

    if index_order:
        # Validate and build ordered list, cycling if necessary
        ordered: List[Tuple[float, float, float, float]] = []
        idxs = list(index_order)
        if not idxs:
            raise ValueError("index_order provided but empty")
        # If any index is out of range, extend base_colors by sampling at higher resolution
        max_idx = max(idxs)
        if max_idx >= len(base_colors):
            resolution = max_idx + 1
            base_colors = []
            for p in np.linspace(0.0, 1.0, resolution):
                color = cmap(p)
                color_tuple = tuple(map(float, color))
                if len(color_tuple) == 3:
                    base_colors.append((color_tuple[0], color_tuple[1], color_tuple[2], 1.0))
                elif len(color_tuple) >= 4:
                    base_colors.append((color_tuple[0], color_tuple[1], color_tuple[2], color_tuple[3]))

        i = 0
        while len(ordered) < n_clusters:
            idx = idxs[i % len(idxs)]
            ordered.append(base_colors[idx])
            i += 1
        return ordered

    # default: sample n distinct positions in the [0,1] range
    positions = np.linspace(0.0, 1.0, n_clusters)
    result = []
    for p in positions:
        color = cmap(p)
        if len(color) == 3:
            result.append((float(color[0]), float(color[1]), float(color[2]), 1.0))
        else:
            result.append((float(color[0]), float(color[1]), float(color[2]), float(color[3])))
    return result


def to_plotly_color(color: ColorLike) -> str:
    """Convert a color specification to a Plotly-compatible color string.

    Accepts:
    - 'rgb(r,g,b)' strings, hex strings or named colors -> returned unchanged
    - matplotlib-style RGB/RGBA tuples (values 0..1) -> 'rgb(r,g,b)'
    - other objects -> str(color)
    """
    if isinstance(color, str):
        return color
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        try:
            r = int(float(color[0]) * 255)
            g = int(float(color[1]) * 255)
            b = int(float(color[2]) * 255)
            return f'rgb({r},{g},{b})'
        except Exception:
            return str(color)
    return str(color)


def build_discrete_colorscale(colors: Sequence[ColorLike]) -> List[List[Union[float, str]]]:
    """Build a stepped Plotly colorscale (list of [pos, color]) from an
    iterable of colors.

    The function creates duplicate boundaries for each color so Plotly renders
    hard steps (blocks) instead of smoothing between colors.

    Input ``colors`` can contain color strings or RGB(A) tuples. Returned
    colorscale is suitable for passing directly to ``go.Heatmap(colorscale=...)``.
    """
    n = len(colors)
    if n == 0:
        return []
    discrete = []
    for i, c in enumerate(colors):
        color_str = to_plotly_color(c)
        start = i / float(n)
        end = (i + 1) / float(n)
        discrete.append([start, color_str])
        discrete.append([end, color_str])
    return discrete
