"""Colormap utilities for UMAP_HDBSCAN visualizations."""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
import colorsys

from dataclasses import dataclass
from typing import List, Optional
@dataclass
class CmapObj:
    """Simple container for colormap data."""
    colors: List[str]  # List of colors in hex format
    cmap: Optional[mcolors.Colormap] = None  # Matplotlib colormap object


def get_nclusters_cmap(hdbscan_results, n_clusters, cmap='tab20b'):
    """
    Create a colormap with n_clusters colors based on a colormap with 20 colors, such as 'tab20b'.
    Returns a dict con .colors en formato hexadecimal para Bokeh/Holoviews.
    
    Parameters:
    -----------
    hdbscan_results : HDBSCAN object
        HDBSCAN results with labels_
    n_clusters : int
        Number of clusters
    cmap : str
        Name of matplotlib colormap to use
        
    Returns:
    --------
    CmapObj with .colors attribute
    """
    original_cmap = plt.cm.get_cmap(cmap)
    hex_colors = []
    
    # Obtener las labels presentes en el clustering actual
    labels = getattr(hdbscan_results, 'labels_', None)
    if labels is not None and -1 in np.unique(labels):
        # Si hay outlier, el primer color es lightgray
        hex_colors.append('lightgray')
        n_valid = n_clusters - 1
    else:
        n_valid = n_clusters
        
    if n_valid > 0:
        indices = np.linspace(0, 19, n_valid, dtype=int)
        colors = [original_cmap(i) for i in indices]
        hex_colors.extend([mcolors.to_hex(c) for c in colors])
        
    cmap_obj = CmapObj()
    cmap_obj.colors = hex_colors
    return cmap_obj


def get_cmap(cmap='cubehelix', n_colors=256):
    """
    Devuelve un objeto con una lista de colores hexadecimales generada con matplotlib.colors,
    compatible con Holoviews/Bokeh para mapas continuos (por ejemplo, cubehelix).
    
    Parameters:
    -----------
    cmap : str
        Name of matplotlib colormap
    n_colors : int
        Number of colors to generate
        
    Returns:
    --------
    CmapObj with .colors attribute
    """
    original_cmap = plt.cm.get_cmap(cmap, n_colors)
    hex_colors = [mcolors.to_hex(original_cmap(i)) for i in range(original_cmap.N)]
    
    cmap_obj = CmapObj()
    cmap_obj.colors = hex_colors
    return cmap_obj


def get_tinted_grey_cmap(tint_color='blue', n_colors=256, reverse=False):
    """
    Genera un colormap recorriendo la luminosidad del color tintado.
    Mantiene el tono (hue) y saturación constantes, variando solo la luminosidad.

    Parámetros:
    -----------
    tint_color : str or tuple
        str o tupla RGB (0-1) o hex, color para tintar la escala
    n_colors : int
        número de colores a generar (por defecto 256)
    reverse : bool
        si True invierte el gradiente (tint_color -> negro)

    Returns:
    --------
    CmapObj with:
        - colors: lista de strings hex ('#rrggbb') compatible con Holoviews/Bokeh
        - cmap: matplotlib.colors.Colormap (LinearSegmentedColormap)
    """
    # Normalizar y convertir tint_color a RGB
    try:
        rgb = mcolors.to_rgb(tint_color)
    except Exception:
        # Asumir que es una tupla ya en formato RGB
        rgb = tuple(tint_color)

    # Convertir RGB a HLS (Hue, Lightness, Saturation)
    h, l, s = colorsys.rgb_to_hls(*rgb)
    
    # Generar gradiente variando solo la luminosidad desde 0 (negro) hasta l (color original)
    colors_list = []
    luminosities = np.linspace(0, l, n_colors)
    
    if reverse:
        luminosities = luminosities[::-1]
    
    for lum in luminosities:
        # Mantener hue y saturación constantes, variar solo luminosidad
        rgb_varied = colorsys.hls_to_rgb(h, lum, s)
        colors_list.append(rgb_varied)
    
    cmap = LinearSegmentedColormap.from_list('tinted_grey', colors_list, N=n_colors)

    # Convertir a hex para compatibilidad con Holoviews/Bokeh
    hex_colors = [mcolors.to_hex(colors_list[i]) for i in range(n_colors)]

    cmap_obj = CmapObj()
    cmap_obj.colors = hex_colors
    cmap_obj.cmap = cmap
    return cmap_obj


def add_wavelength_axis(plot, element):
    """
    Hook para añadir un eje superior con valores de wavelength (1240/eV).
    Se usa FuncTickFormatter para calcular las etiquetas en nm a partir de eV,
    manejando divisiones por cero y valores no finitos.
    
    Parameters:
    -----------
    plot : holoviews plot
        The plot object
    element : holoviews element
        The plot element
    """
    from bokeh.models import LinearAxis, FuncTickFormatter

    fig = plot.state

    # Formatter JS: calcula 1240 / tick, evita division por cero y valores no finitos.
    fmt = FuncTickFormatter(code="""
        // tick es el valor en la escala del eje (eV)
        if (!isFinite(tick) || tick === 0) { return ""; }
        var nm = 1240.0 / tick;
        if (!isFinite(nm)) { return ""; }
        // Ajusta formato según magnitud (sin decimales por defecto)
        return nm.toFixed(0);
    """)

    axis = LinearAxis(axis_label='Wavelength (nm)', formatter=fmt)
    fig.add_layout(axis, 'above')
