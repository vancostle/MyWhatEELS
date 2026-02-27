"""
Base spectrum image (datacube) visualization component.

Shared base for 3D EELS datacube visualization using HoloViews + Panel.
It provides:
- Integrated 2D heatmap showing summed intensity with invisible selection layer
- Pipe/DynamicMap-backed spectrum pane for efficient in-place updates
- Hover, click, and region selection interactions via HoloViews streams
- Zoom/pan range preservation for paneB

Page-specific features (like fitting, clustering, inactivity timers) should be
implemented in subclasses.
"""

import panel as pn
import numpy as np
import holoviews as hv
from holoviews import streams as hv_streams

from whateels.helpers import SpectrumExtractor
from whateels.interfaces import IPlot
from whateels.components import InfoPanel
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from xarray import Dataset


class BaseSpectrumImagePlot(IPlot):
    """
    Base component for spectrum image (datacube) visualization using HoloViews + Panel.

    Displays a 2D heatmap of integrated intensity alongside an interactive
    spectrum viewer. Supports hover, click, and region selection.

    Can be extended by page-specific visualizers for additional features
    like clustering, fitting, etc.
    """

    # Default axis titles — subclasses may override
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

    def __init__(self, dataset: "Dataset", eloss_name: str = 'Eloss'):
        """
        Initialize spectrum image visualizer.

        Args:
            dataset: xarray Dataset containing the EELS datacube
            eloss_name: Name of the energy loss axis (default: 'Eloss')
        """
        self._dataset = dataset
        self._eloss_name = eloss_name

        # Energy axis
        self._e_axis = self._dataset.coords[self._eloss_name].values

        # ElectronCount data cube
        self._electron_count_data: "Dataset" = self._dataset.ElectronCount

        # Range state for paneB (to preserve zoom/pan)
        self._current_x_range = None
        self._current_y_range = None
        self._current_x_autorange = None
        self._current_y_autorange = None

        # Selection / hover state
        self._region_pairs = []
        self._last_hover_point = None

        # Image width — used for index → (row, col) mapping in _on_paneA_selected
        self._nx = 0

        # Pane / stream placeholders
        self.paneA = None   # HoloViews heatmap pane
        self.paneB = None   # HoloViews spectrum pane
        self._selectors = None      # invisible hv.Points for lasso/box selection
        self._hover_stream = None
        self._tap_stream = None
        self._selection_stream = None
        self._rangexy_stream = None
        self._paneB_pipe = None     # Pipe stream for efficient paneB updates
        self._paneB_dmap = None     # DynamicMap backed by _paneB_pipe

        # Setup plots and callbacks
        self._setup_plots()
        self._setup_callbacks()

    # --- Public layout builders ---
    @override
    def create_plots(self):
        """Must be implemented by subclasses to compose the full layout."""
        raise NotImplementedError("Subclasses must implement create_plots() in BaseSpectrumImagePlot.")

    @override
    def create_dataset_info(self):
        """ Must be implemented by subclasses to return a dataset info panel."""
        raise NotImplementedError("Subclasses must implement create_dataset_info() in BaseSpectrumImagePlot.")

    # --- Plot / Pane Setup (HoloViews) ---
    def _setup_plots(self):
        """
        Initialize paneA (heatmap + invisible selection layer) and paneB
        (Pipe/DynamicMap spectrum) using HoloViews.
        """
        m_image_da = self._electron_count_data.sum(self._eloss_name)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Expected 2D integrated image, got shape={m_image.shape}")

        ny, nx = m_image.shape
        self._nx = nx

        # Energy axis
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # Background heatmap
        img = hv.Image(
            (np.arange(nx), np.arange(ny), m_image),
            kdims=['x', 'y'],
            vdims=['Intensity'],
        ).opts(
            cmap='Greys_r',
            colorbar=False,
            xaxis=None,
            yaxis=None,
            invert_yaxis=True,
            aspect='equal',
            responsive=True,
            shared_axes=False,
        )

        # Invisible Points layer — carries lasso/box select tools
        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        points_data = np.column_stack([XX.ravel().astype(float), YY.ravel().astype(float)])
        self._selectors = hv.Points(points_data, kdims=['x', 'y']).opts(
            size=0,
            alpha=0,
            nonselection_alpha=0,
            tools=['lasso_select', 'box_select'],
            shared_axes=False,
        )

        # Overlay: heatmap + selection layer
        overlay = (img * self._selectors).opts( # type: ignore
            hv.opts.Overlay(responsive=True, aspect='equal', shared_axes=False)
        )

        self.paneA = pn.pane.HoloViews(
            overlay,
            sizing_mode='stretch_height',
            margin=0,
            styles={'margin': 'auto'},
        )

        # paneB: Pipe + DynamicMap for in-place data updates (avoids Bokeh model rebuild)
        self._paneB_pipe = hv_streams.Pipe(data=None)
        self._paneB_dmap = hv.DynamicMap(lambda data: data, streams=[self._paneB_pipe])
        self.paneB = pn.pane.HoloViews(
            self._paneB_dmap,
            sizing_mode='stretch_both',
            margin=0,
        )
        # Seed with origin pixel so chart is immediately visible
        # Always wrap in Overlay for consistent DynamicMap type
        self._paneB_pipe.send(hv.Overlay([self._figB_hover({"x": 0, "y": 0})]))

    def _setup_callbacks(self):
        """Wire HoloViews streams to interaction handlers."""
        if self._selectors is not None:
            self._hover_stream = hv_streams.PointerXY(source=self._selectors)
            self._tap_stream = hv_streams.Tap(source=self._selectors)
            self._selection_stream = hv_streams.Selection1D(source=self._selectors)
            self._hover_stream.add_subscriber(self._on_paneA_hover)
            self._tap_stream.add_subscriber(self._on_paneA_click)
            self._selection_stream.add_subscriber(self._on_paneA_selected)

        # RangeXY stream to capture paneB zoom/pan
        self._rangexy_stream = hv_streams.RangeXY(source=self._paneB_dmap)
        self._rangexy_stream.add_subscriber(self._on_paneB_range_changed)

    # --- Spectrum figure helpers ---

    def _figB_hover(self, point):
        """Return an hv.Curve for a single pixel (hover/click)."""
        if not point:
            point = {"x": 0, "y": 0}
        i, j = round(point["y"]), round(point["x"])
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        return hv.Curve(
            (self._energy, spec),
            kdims=['x'],
            vdims=['y'],
        ).opts(
            color='black',
            line_width=1.5,
            title=f"Hover (x={j}, y={i})",
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True,
            shared_axes=False,
            framewise=True,
        )

    def _figB_region(self, pairs):
        """Return an hv.Curve for a region (summed spectrum)."""
        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)
        if res is None:
            return self._figB_hover({"x": 0, "y": 0})
        spec, n_points = res
        return hv.Curve(
            (self._energy, spec),
            kdims=['x'],
            vdims=['y'],
        ).opts(
            color='black',
            line_width=1.5,
            title=f"ROI — sum (points={n_points})",
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True,
            shared_axes=False,
            framewise=True,
        )

    # --- paneB update ---

    def _update_paneB(self, fig):
        """Push a new figure through the pipe. Always wraps in hv.Overlay for type consistency."""
        if self._paneB_pipe is not None:
            if fig is not None and not isinstance(fig, hv.Overlay):
                fig = hv.Overlay([fig])
            self._paneB_pipe.send(self._set_ranges_and_convert(fig))

    def _show_spectrum(self, *, point=None, region_pairs=None):
        """
        Unified helper: extract spectrum from a point or region and push to paneB.
        Subclasses can override for additional behaviour (e.g. fitting).
        """
        fig = None
        if region_pairs is not None:
            if not region_pairs:
                if self._last_hover_point is not None:
                    self._show_spectrum(point=self._last_hover_point)
                return
            fig = self._figB_region(region_pairs)
        elif point is not None:
            fig = self._figB_hover(point)
        self._update_paneB(fig)

    # --- Pane A event handlers ---

    def _on_paneA_hover(self, x=None, y=None):
        """Handle PointerXY hover — show pixel spectrum unless region is selected."""
        if x is None or y is None:
            return
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            self._show_spectrum(point=point, region_pairs=self._region_pairs)
        else:
            self._show_spectrum(point=point)

    def _on_paneA_click(self, x=None, y=None):
        """Handle Tap click — same as hover in the base implementation."""
        if x is None or y is None:
            return
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            self._show_spectrum(point=point, region_pairs=self._region_pairs)
        else:
            self._show_spectrum(point=point)

    def _on_paneA_selected(self, index=None):
        """Handle lasso/box Selection1D — show summed spectrum for selected pixels."""
        if not index:
            pairs = []
        else:
            pairs = list(dict.fromkeys(
                (idx // self._nx, idx % self._nx) for idx in index
            ))
        self._region_pairs = pairs
        self._show_spectrum(region_pairs=pairs)

    # --- Pane B range change (preserve zoom/pan) ---

    @staticmethod
    def _is_valid_range(r):
        """Return True only if r is a 2-tuple of finite, distinct values."""
        if r is None:
            return False
        try:
            lo, hi = r
            return (
                lo is not None and hi is not None
                and lo == lo and hi == hi  # NaN check
                and abs(hi - lo) > 1e-12
            )
        except Exception:
            return False

    def _on_paneB_range_changed(self, x_range=None, y_range=None):
        """Store current paneB zoom/pan ranges for re-application on updates."""
        if self._is_valid_range(x_range):
            self._current_x_range = x_range
            self._current_x_autorange = False
        elif x_range is None:
            self._current_x_autorange = True
            self._current_x_range = None

        if self._is_valid_range(y_range):
            self._current_y_range = y_range
            self._current_y_autorange = False
        elif y_range is None:
            self._current_y_autorange = True
            self._current_y_range = None

    def _apply_current_ranges(self, fig):
        """Apply stored xlim/ylim opts to a HoloViews element."""
        try:
            opts = {}
            if self._current_x_range is not None:
                opts['xlim'] = self._current_x_range
            if self._current_y_range is not None:
                opts['ylim'] = self._current_y_range
            if opts:
                return fig.opts(**opts)
        except Exception:
            pass
        return fig

    def _set_ranges_and_convert(self, fig):
        return self._apply_current_ranges(fig)
