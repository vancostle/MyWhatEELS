"""
Utility functions for SpectrumImagePlot and related homepage visualizations.
"""

import holoviews as hv

from whateels.helpers import SpectrumExtractor, SpectrumFitting

# --- Spectrum extraction and fitting helpers ---
def get_range_slider_value(slider):
    value = getattr(slider, 'value', None)
    if value is not None and hasattr(value, "__iter__"):
        value_tuple = tuple(value)
        if len(value_tuple) == 2:
            return value_tuple
    return (0, 1)

def apply_fitting(fig, energy, spec, slider):
    range_slider_value = get_range_slider_value(slider)
    y_fit = SpectrumFitting.fit_powerlaw_curve(energy, spec, range_values=range_slider_value)
    return plot_fit_traces(fig, energy, spec, y_fit)

def get_pixel_spectrum(electron_count_data, point):
    i, j = int(point["y"]), int(point["x"])
    if electron_count_data is None:
        raise RuntimeError("_electron_count_data is not set on SpectrumImagePlot.")
    return SpectrumExtractor.get_spectrum_from_pixel(electron_count_data, i, j)

def plot_fit_traces(fig, x, y, y_fit):
    """
    Overlay power-law fit and background subtraction on a HoloViews spectrum plot.
    - fig: the base hv.Curve (spectrum)
    - x: energy axis
    - y: spectrum
    - y_fit: fitted background (same shape as y)
    Returns: HoloViews Overlay
    """
    if y_fit is None:
        return fig

    # Power-law fit curve — label is passed as element name for legend
    fit_curve = hv.Curve((x, y_fit), kdims=['x'], vdims=['y'], label='PowerLaw Fit').opts(
        color='crimson',
        line_dash='dashed',
        line_width=2,
    )

    # Background subtraction area (y - y_fit)
    bg_sub = hv.Area((x, y - y_fit), kdims=['x'], vdims=['y'], label='Background Subtraction').opts(
        color='salmon',
        alpha=0.4,
    )

    # Overlay: base spectrum, fit, and background subtraction
    # framewise=True ensures y-axis auto-scales to the full overlay content
    overlay = (fig * fit_curve * bg_sub).opts(
        hv.opts.Overlay(framewise=True, responsive=True, shared_axes=False)
    )
    return overlay

def start_pc(pc):
    if pc is None:
        return
    running = getattr(pc, 'running', False)
    if not running:
        pc.start()

def stop_pc(pc):
    if pc is None:
        return
    running = getattr(pc, 'running', False)
    if running:
        pc.stop()
