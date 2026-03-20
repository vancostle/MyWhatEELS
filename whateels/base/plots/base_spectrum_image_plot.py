"""
Base spectrum image (datacube) visualization component.

Shared base for 3D EELS datacube visualization using HoloViews + Panel.
It provides:
- Integrated 2D heatmap showing summed intensity with invisible selection layer
- Pipe/DynamicMap-backed spectrum pane for efficient in-place updates
- Hover, click, and region selection interactions via HoloViews streams (region selection may be disabled in subclasses)
- Zoom/pan range preservation for paneB

Page-specific features (like fitting, clustering, inactivity timers) should be implemented in subclasses. Subclasses may override or disable region selection logic as needed.
"""

import panel as pn
import numpy as np
import time
import holoviews as hv
from holoviews import streams as hv_streams

from whateels.helpers import SpectrumExtractor
from whateels.interfaces import IPlot
from whateels.components import InfoPanel, SplitJs
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from xarray import Dataset


class BaseSpectrumImagePlot(IPlot):
    """
    Base component for spectrum image (datacube) visualization using HoloViews + Panel.

    Displays a 2D heatmap of integrated intensity alongside an interactive spectrum viewer. Supports hover, click, and region selection by default.

    Subclasses may override or disable region selection logic (e.g., clustering visualizer disables region selection).

    Can be extended by page-specific visualizers for additional features like clustering, fitting, etc.
    """

    # Default axis titles — subclasses may override
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

    # TODO: Consider making paneA_select_tools a parameter for flexibility in subclasses (e.g., disable region selection in clustering visualizer)
    def __init__(self, dataset: "Dataset", eloss_name: str = 'Eloss', paneA_select_tools=['lasso_select', 'box_select']):
        """
        Initialize spectrum image visualizer.

        Args:
            dataset: xarray Dataset containing the EELS datacube
            eloss_name: Name of the energy loss axis (default: 'Eloss')
        """
        self._dataset = dataset
        self._eloss_name = eloss_name
        self._paneA_select_tools = paneA_select_tools

        # Energy axis
        self._e_axis: np.ndarray = self._dataset.coords[self._eloss_name].values

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

        # Overlay + lasso debounce state — must exist before _setup_plots() runs
        self._paneA_base_overlay = None
        self._selection_overlay = hv.Points([], kdims=['x', 'y'])
        self._hover_blocked = False
        self._pending_selection_index = None
        self._pending_selection_ts = None
        self._SELECTION_DEBOUNCE_MS = 200
        self._debounce_pc = None
        self._double_tap_stream: hv_streams.DoubleTap | None = None

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
    def create_plots(self) -> pn.viewable.Viewable:
        """
        Default two-column SplitJs layout for spectrum image plots.
        Subclasses can override if they need a custom layout.
        """
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both',
            margin=0
        )
        right_column = pn.Column(
            self.paneB,
            sizing_mode='stretch_both',
            margin=0
        )
        splitjs = SplitJs(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )
        # Allow subclasses to store/restore layout if needed
        self._plots_layout = splitjs
        container = pn.Column(
            splitjs,
            sizing_mode='stretch_both'
        )
        return container

    @override
    def create_dataset_info(self) -> InfoPanel:
        """
        Returns a panel with dataset information (shape, beam energy, angles).
        Shared implementation for all spectrum image plot subclasses.
        """
        NOT_AVAILABLE = 'N/A'
        attrs = self._dataset.attrs if self._dataset is not None else {}

        shape = attrs.get('shape', NOT_AVAILABLE)
        beam_energy = attrs.get('beam_energy', NOT_AVAILABLE)
        convergence_angle = attrs.get('convergence_angle', NOT_AVAILABLE)
        collection_angle = attrs.get('collection_angle', NOT_AVAILABLE)

        beam_energy_fmt = f"{beam_energy} keV" if beam_energy != NOT_AVAILABLE else NOT_AVAILABLE
        convergence_angle_fmt = f"{convergence_angle} mrad" if convergence_angle != NOT_AVAILABLE else NOT_AVAILABLE
        collection_angle_fmt = f"{collection_angle} mrad" if collection_angle != NOT_AVAILABLE else NOT_AVAILABLE

        return InfoPanel(
            title="Dataset Information",
            information={
                "Shape": shape,
                "Beam Energy": beam_energy_fmt,
                "Convergence Angle": convergence_angle_fmt,
                "Collection Angle": collection_angle_fmt,
            },
            sizing_mode='stretch_width',
            margin=0,
        )

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
        self._energy: np.ndarray = energy

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

        # Capture base overlay for selection dot recomposition
        self._paneA_base_overlay = overlay
        self._update_selection_overlay([])

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

        # Debounce periodic callback for lasso selection
        self._debounce_pc = pn.state.add_periodic_callback(
            self._check_selection_debounce, period=250, start=False
        )
        # DoubleTap stream to reset lasso selection
        if self._selectors is not None:
            self._double_tap_stream = hv_streams.DoubleTap(source=self._selectors)
            self._double_tap_stream.add_subscriber(self._on_paneA_double_tap)

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

    def _now_ms(self):
        return int(time.time() * 1000)

    def _index_to_pairs(self, index):
        """Convert a flat Selection1D index list to (row, col) pairs."""
        if not index:
            return []
        return list(dict.fromkeys(
            (idx // self._nx, idx % self._nx) for idx in index
        ))

    def _check_selection_debounce(self):
        """Periodic callback: flush a pending lasso selection after the debounce window."""
        if self._pending_selection_ts is None:
            if self._debounce_pc and self._debounce_pc.running:
                self._debounce_pc.stop()
            return
        if self._now_ms() - self._pending_selection_ts >= self._SELECTION_DEBOUNCE_MS:
            index = self._pending_selection_index
            self._pending_selection_index = None
            self._pending_selection_ts = None
            if self._debounce_pc and self._debounce_pc.running:
                self._debounce_pc.stop()
            self._process_selection(index)

    def _update_selection_overlay(self, pairs):
        """Rebuild the red-dot selection overlay and recompose paneA."""
        if pairs:
            xs = [col for row, col in pairs]
            ys = [row for row, col in pairs]
            self._selection_overlay = hv.Points(
                (xs, ys), kdims=['x', 'y']
            ).opts(color='red', size=5, alpha=0.5)
        else:
            self._selection_overlay = hv.Points([], kdims=['x', 'y'])
        if self._paneA_base_overlay is not None and self.paneA is not None:
            self.paneA.object = (
                self._paneA_base_overlay * self._selection_overlay
            ).opts(
                hv.opts.Overlay(
                    responsive=True, aspect='equal', shared_axes=False,
                    active_tools=['lasso_select'],
                )
            )

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
        """Store pending lasso index and start debounce timer."""
        if not index:
            return
        self._hover_blocked = True
        self._pending_selection_ts = self._now_ms()
        self._pending_selection_index = index
        if self._debounce_pc and not self._debounce_pc.running:
            self._debounce_pc.start()

    def _process_selection(self, index=None):
        """Commit a debounced lasso selection: compute pairs, update overlay, show spectrum."""
        pairs = self._index_to_pairs(index)
        self._region_pairs = pairs
        self._update_selection_overlay(pairs)
        if not pairs:
            self._hover_blocked = False
            return
        self._show_spectrum(region_pairs=pairs)
        self._hover_blocked = True

    def _on_paneA_double_tap(self, x=None, y=None):
        """Reset lasso selection, clear red dots, and unblock hover."""
        self._hover_blocked = False
        self._region_pairs = []
        self._pending_selection_index = None
        self._pending_selection_ts = None
        self._update_selection_overlay([])
        if self._debounce_pc and self._debounce_pc.running:
            self._debounce_pc.stop()

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

    def cleanup(self):
        """Unsubscribe all HoloViews streams and release dataset references."""
        # Stop and clean up debounce periodic callback
        if self._debounce_pc is not None:
            try:
                if self._debounce_pc.running:
                    self._debounce_pc.stop()
            except Exception:
                pass
            self._debounce_pc = None

        # Remove subscribers first — streams hold strong refs to bound methods
        # (e.g. self._on_paneA_hover), which would keep this plot alive via the
        # stream→callback→self chain even after all other refs are nulled.
        subscriber_pairs = [
            (self._hover_stream,       self._on_paneA_hover),
            (self._tap_stream,         self._on_paneA_click),
            (self._selection_stream,   self._on_paneA_selected),
            (self._double_tap_stream,  self._on_paneA_double_tap),
            (self._rangexy_stream,     self._on_paneB_range_changed),
        ]
        for stream, callback in subscriber_pairs:
            if stream is not None:
                try:
                    stream.remove_subscriber(callback)
                except Exception:
                    pass

        for stream in [
            self._hover_stream,
            self._tap_stream,
            self._selection_stream,
            self._double_tap_stream,
            self._rangexy_stream,
            self._paneB_pipe,
        ]:
            if stream is not None:
                try:
                    stream.clear()
                except Exception:
                    pass

        # Explicitly null out large data references so numpy arrays are freed
        # even if something else still holds a reference to this plot object.
        self._dataset = None  # type: ignore[assignment]
        self._e_axis = None  # type: ignore[assignment]
        self._electron_count_data = None  # type: ignore[assignment]
        self._energy = None  # type: ignore[assignment]
        self._region_pairs = []
        self.paneA = None
        self.paneB = None
        self._selectors = None
        self._hover_stream = None
        self._tap_stream = None
        self._selection_stream = None
        self._double_tap_stream = None
        self._rangexy_stream = None
        self._paneB_pipe = None
        self._paneB_dmap = None
        self._plots_layout = None
        self._paneA_base_overlay = None
        self._selection_overlay = None
