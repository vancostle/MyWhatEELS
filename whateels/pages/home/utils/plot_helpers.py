"""
Utility functions for SpectrumImagePlot and related homepage visualizations.
"""
import plotly.graph_objs as go

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
    POWERLAW_FIT_NAME = 'PowerLaw Fit'
    BG_SUBTRACTION_NAME = 'Background Subtraction'
    CRIMSON = 'crimson'
    BG_LINE_COLOR = 'rgba(255,160,122,0.2)'
    BG_FILL_COLOR = 'rgba(255,160,122,0.6)'
    LEGEND_X = 0.98
    LEGEND_Y = 0.98
    LEGEND_XANCHOR = 'right'
    LEGEND_YANCHOR = 'top'
    LEGEND_BGCOLOR = 'rgba(255,255,255,0.6)'
    LEGEND_BORDER_COLOR = 'rgba(0,0,0,0.1)'
    LEGEND_BORDER_WIDTH = 1
    FILL_TO_ZEROY = 'tozeroy'

    if y_fit is None:
        return fig
    newfig = go.Figure(fig)
    newfig.add_trace(go.Scatter(
        x=x,
        y=y_fit,
        line=dict(color=CRIMSON),
        name=POWERLAW_FIT_NAME
    ))
    newfig.add_trace(go.Scatter(
        x=x,
        y=(y - y_fit),
        fill=FILL_TO_ZEROY,
        line=dict(color=BG_LINE_COLOR),
        fillcolor=BG_FILL_COLOR,
        name=BG_SUBTRACTION_NAME
    ))
    newfig.update_layout(
        legend=dict(
            x=LEGEND_X,
            y=LEGEND_Y,
            xanchor=LEGEND_XANCHOR,
            yanchor=LEGEND_YANCHOR,
            bgcolor=LEGEND_BGCOLOR,
            bordercolor=LEGEND_BORDER_COLOR,
            borderwidth=LEGEND_BORDER_WIDTH,
        )
    )
    return newfig

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
