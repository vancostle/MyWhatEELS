"""Bokeh geometry helpers shared by responsive spatial plots."""

from __future__ import annotations

from bokeh.models import BoxZoomTool, DataRange1d, WheelZoomTool


def _range_is_flipped(axis_range) -> bool:
    """Return whether a finite range currently runs from high to low."""
    try:
        start = float(axis_range.start)
        end = float(axis_range.end)
    except (AttributeError, TypeError, ValueError):
        return False
    return start > end


def square_pixel_plot_hook(plot, _element) -> None:
    """Keep spatial X/Y units square without constraining the outer plot box.

    HoloViews' ``aspect='equal'`` and ``data_aspect`` options apply an aspect
    ratio to the complete Bokeh figure. That figure also owns its title,
    toolbar, axes and colour bar, so those options can squeeze or displace that
    plot furniture in a responsive layout.

    Bokeh's ``match_aspect`` works at the inner Cartesian frame instead, after
    the surrounding panels have received their space. It only operates when
    *both* axes are ``DataRange1d`` instances; HoloViews creates ``Range1d`` for
    ``Image`` by default, hence the deliberate one-time replacement below.

    Do not replace the HoloViews ``plot.handles`` ranges. They remain the
    stable data bounds used by streams while Bokeh owns the displayed,
    letterboxed ranges.
    """
    figure = getattr(plot, "state", None)
    if figure is None:
        return

    if not isinstance(figure.x_range, DataRange1d):
        figure.x_range = DataRange1d(
            range_padding=0,
            only_visible=True,
            flipped=_range_is_flipped(figure.x_range),
        )
    if not isinstance(figure.y_range, DataRange1d):
        figure.y_range = DataRange1d(
            range_padding=0,
            only_visible=True,
            flipped=_range_is_flipped(figure.y_range),
        )

    figure.match_aspect = True
    figure.aspect_scale = 1.0
    # Preserve the responsive outer box. Expected whitespace is added to the
    # data ranges, not to the title/toolbar/colour-bar allocation.
    figure.aspect_ratio = None
    figure.sizing_mode = "stretch_both"

    for tool in figure.select(type=BoxZoomTool):
        tool.match_aspect = True
    for tool in figure.select(type=WheelZoomTool):
        tool.zoom_on_axis = False

