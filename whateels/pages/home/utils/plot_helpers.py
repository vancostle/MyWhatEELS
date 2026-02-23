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
    i, j = int(round(point["y"])), int(round(point["x"]))
    if electron_count_data is None:
        raise RuntimeError("_electron_count_data is not set on SpectrumImagePlot.")
    return SpectrumExtractor.get_spectrum_from_pixel(electron_count_data, i, j)

def plot_fit_traces(fig, x, y, y_fit):
    """Overlay PowerLaw fit and background-subtraction traces on an hv.Curve figure."""
    POWERLAW_FIT_NAME = 'PowerLaw Fit'
    BG_SUBTRACTION_NAME = 'Background Subtraction'
    CRIMSON = 'crimson'
    BG_FILL_COLOR = 'salmon'

    if y_fit is None:
        return fig

    fit_curve = hv.Curve(
        (x, y_fit), label=POWERLAW_FIT_NAME
    ).opts(color=CRIMSON, line_width=1.5)

    bg_area = hv.Area(
        (x, y - y_fit), label=BG_SUBTRACTION_NAME
    ).opts(color=BG_FILL_COLOR, alpha=0.5, line_width=0)

    return (fig * fit_curve * bg_area)

def start_pc(pc):
    if pc is not None:
        running = getattr(pc, 'running', False)
        if not running:
            pc.start()

def stop_pc(pc):
    if pc is not None:
        running = getattr(pc, 'running', False)
        if running:
            pc.stop()
