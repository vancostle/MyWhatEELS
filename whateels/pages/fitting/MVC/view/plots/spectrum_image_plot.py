"""Spectrum-image (datacube) visualizer for the fitting page.

HoloViews + Panel implementation that replaces the previous Plotly-based version.
Extends BaseSpectrumImagePlot with fitting-specific features: inactivity timer,
fit-curve overlay, energy map display, and multifit ROI extraction.
"""

import panel as pn
import numpy as np
import time
import holoviews as hv
import bokeh.palettes as palettes
from matplotlib.colors import LinearSegmentedColormap, to_hex

from whateels.base.plots import BaseSpectrumImagePlot
from typing import override, TYPE_CHECKING
from whateels.components import create_dataset_info_card, DragGutter
from whateels.helpers.colormaps import get_nclusters_cmap
from whateels.state import CacheManager

if TYPE_CHECKING:
    from ...model import FittingModel
    from xarray import Dataset

class SpectrumImageVisualizer(BaseSpectrumImagePlot):
    """
    HoloViews/Panel implementation of the Spectrum Image visualizer for the fitting page.

    Extends BaseSpectrumImagePlot with:
    - Inactivity timer: hover temporarily shows pixel spectrum, then reverts to ROI.
    - Fit-curve overlay: magenta filled area drawn on top of the ROI spectrum.
    - Energy map display: replaces paneA image with a green-to-pink heatmap.
        - Data-source-aware ROI extraction: uses the currently selected data source
            (raw or Home-preprocessed) from shared AppState.
    """

    # Axis titles for spectrum plot
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'
    # None of the paneA hooks are overridden here, exactly as in Home,
    # Clustering and Quantification. The inherited aspect='equal' is what turns
    # on match_aspect, and match_aspect is what keeps the DATA pixels square
    # inside the pane. Adding square_pixel_plot_hook on top of it does the
    # opposite of what its name suggests: it nulls aspect_ratio and hands the
    # frame to Bokeh, which then stretches the map across the pane.
    #
    # The OUTER box is not decided here at all. DragGutter fits paneA on its
    # browser-side Bokeh model during a gesture and persists the final size in
    # Python. See __init__.

    def __init__(self, model: "FittingModel", dataset: "Dataset"):
        """Initialize visual state, interactive panes, and callback wiring."""
        self._model = model

        # Inactivity timer state — must be set before super().__init__ triggers _setup_plots
        self._last_hover_ts = None
        self._INACTIVITY_MS = 700
        self._pc : pn.state.PeriodicCallback | None = None # type: ignore[assignment] # Panel's PeriodicCallback type is not well-annotated

        # Fitting/UI state
        self.element_quant_data = []
        self.selected_slice = None
        self.range_slider = None
        self.fitting_button = None
        self._ignore_selection_until_ms = 0
        self._nlls_result_active = False
        self._nlls_clustering_active = False
        self._nlls_clustering_label_plot = None
        self._nlls_clustering_spectra_plot = None
        self._nlls_edge_preview_active = False
        self._nlls_edge_preview_plot = None
        self._nlls_edge_preview_previous_plot = None
        self._nlls_edge_preview_previous_result_active = False
        self._nlls_edge_preview_previous_ranges = None

        # BaseSpectrumImagePlot.__init__ expects (dataset, eloss_name) and calls
        # _setup_plots() + _setup_callbacks() internally.
        super().__init__(dataset, eloss_name=model.constants.ELOSS)

        # paneA is sized by the gutter with the same fit SplitJs runs for Home,
        # Clustering and Quantification. It is applied locally during dragging
        # and the browser hands only the final box to _apply_pane_ratio:
        #
        #     w = min(available_width, available_height * ratio),  h = w / ratio
        #
        # so the image fills the height while the pane is wide enough, and gives
        # height back as soon as the width becomes the binding side.
        #
        # It has to be done on the Bokeh model, not on disposable DOM styles.
        # During a drag that model is updated locally; release persists it in
        # Python. Two other layers were tried and neither can hold: Panel's
        # 'scale_height' measures the parent
        # once and this block lives inside _StableAdditiveColumn, a scroll
        # viewport, where that measurement is zero and paneA vanishes; and a
        # size written from JavaScript is erased by Bokeh's next layout solve,
        # because paneA is a Bokeh-managed element.
        #
        # match_aspect (inherited with aspect='equal') is a separate job: it
        # keeps the DATA pixels square inside that box, absorbing whatever the
        # title and colour bar take.
        self.paneA.sizing_mode = 'stretch_both'
        # _setup_plots() has just filled _nx/_ny; publish the ratio so the gutter
        # built later in create_plots() starts with it.
        self._publish_paneA_ratio()

        # Wire DoubleTap was moved to base _setup_callbacks — no manual wiring needed.

        # Periodic callback for inactivity logic (stopped initially)
        self._pc = pn.state.add_periodic_callback(
            self._check_inactivity, period=250, start=False
        )

    def _publish_paneA_ratio(self) -> None:
        """Publish the current spatial ratio to the gutter that sizes paneA.

        Must run again whenever ``_nx``/``_ny`` change: the energy map and the
        clustering map can carry a different spatial shape than the source cube,
        and a stale ratio would size them to the wrong box. Setting it re-fits
        immediately from the last box the browser reported, so switching maps
        does not have to wait for the next drag.
        """
        if not self._nx or not self._ny:
            return
        ratio = float(self._nx) / float(self._ny)
        self._paneA_ratio = ratio
        gutter = getattr(self, '_plots_gutter', None)
        if gutter is not None:
            gutter.pane_ratio = ratio

    def get_e_axis(self):
        """Return the 1D energy axis associated with the current datacube."""
        return self._e_axis

    def _inside_spatial_map(self, x, y) -> bool:
        """Reject pointer events that fall in aspect-preserving letterboxing."""
        try:
            x_value = float(x)
            y_value = float(y)
        except (TypeError, ValueError):
            return False
        return bool(
            np.isfinite(x_value)
            and np.isfinite(y_value)
            and -0.5 <= x_value < self._nx - 0.5
            and -0.5 <= y_value < self._ny - 0.5
        )

    @override
    def _get_display_data(self):
        """Return active ElectronCount source selected for fitting in AppState."""
        app_state = CacheManager.get_cached_app_state()
        dataset = app_state.plot_dataset
        if dataset is not None and hasattr(dataset, 'ElectronCount'):
            return dataset.ElectronCount
        return self._electron_count_data

    @override
    def create_dataset_info(self):
        """Return the shared editable Dataset Information card for the left sidebar.

        The base implementation builds a read-only InfoPanel. Fitting uses the very same card
        as Home so that E0, alpha and beta stay in sync: editing it writes straight into
        `dataset.attrs` and propagates through AppState, whichever page you edit it from.
        """
        return create_dataset_info_card(
            self._model,
            self._dataset,
            sizing_mode='stretch_width',
            margin=0,
        )

    # --- paneA setup override: now handled by base ---

    # --- Public layout builders (used by controller) ---
    @override
    def create_plots(self):
        """Build the two-pane split layout with image on the left and spectra on the right."""
        # No ``align`` here. Panel maps it to align-self, which on a Row is the
        # VERTICAL axis: it drops the column to content height and leaves paneA
        # with no height to scale from. paneA centres itself with its own
        # ``margin: auto`` instead.
        left_column = pn.Column(
            self.paneA,
            self._hover_gate_widget,
            sizing_mode='stretch_both',
            margin=0,
            css_classes=[DragGutter.PANE_CSS_CLASS],
            # 'overflow: hidden' guards the frames between two throttled Bokeh
            # solves: paneA is sized 'fixed', so while the pane shrinks under it
            # the map would otherwise spill past the gutter.
            styles={
                'min-width': '0',
                'min-height': '0',
                'overflow': 'hidden',
            },
        )
        right_column = pn.Column(
            self.paneB,
            # Button row (fitting + multifit), if available.
            self.buttons_row if hasattr(self, 'buttons_row') else self.fitting_button,
            # Energy-range slider row, if available.
            self.range_slider_row if hasattr(self, 'range_slider_row') else self.range_slider,
            sizing_mode='stretch_both',
            margin=0,
            css_classes=[DragGutter.PANE_CSS_CLASS],
            styles={'min-width': '0', 'min-height': '0'},
        )
        # A native Row keeps both plots inside the layout tree Bokeh solves.
        # The separator is draggable but owns nothing: ``ratio_pane`` is a plain
        # Python reference, not a Child parameter, so paneA stays exactly where
        # Panel mounted it. Reparenting is what detached axes and colour bars
        # from their canvas when an additive result invalidated the root.
        self._plots_gutter = DragGutter(
            ratio_pane=self.paneA,
            pane_ratio=getattr(self, '_paneA_ratio', 0.0),
        )
        self._plots_layout = pn.Row(
            left_column,
            self._plots_gutter,
            right_column,
            sizing_mode='stretch_both',
            margin=0,
            css_classes=[DragGutter.ROW_CSS_CLASS],
        )
        return self._plots_layout

    # --- Multifit-aware _figB_region override ---

    @override
    def _figB_region(self, pairs):
        """Return an hv.Curve for a region using the currently selected data source."""
        res = self._get_spectrum_from_indices_fast(pairs)
        if res is None:
            return self._figB_hover({"x": 0, "y": 0})
        spec, n_points = res
        CacheManager.get_cached_app_state().spectra = spec
        return hv.Curve(
            (self._energy, spec),
            kdims=['x'], vdims=['y'],
        ).opts(
            color='black', line_width=1.5,
            title=f"ROI — sum (points={n_points})",
            xlabel=self._X_AXIS_SPECTRUM_TITLE,
            ylabel=self._Y_AXIS_SPECTRUM_TITLE,
            responsive=True, shared_axes=False, framewise=True,
        )

    # --- Fitting overlay ---

    def plot_fitting(self, x, y_fit):
        """Overlay the fitted spectrum as a magenta filled area on paneB."""
        self._reset_nlls_edge_preview_state()
        CacheManager.get_cached_app_state().fitting_results = y_fit
        roi_curve = self._figB_region(self._region_pairs) if self._region_pairs else self._figB_hover({"x": 0, "y": 0})
        fit_area = hv.Area(
            (x, y_fit), kdims=['x'], vdims=['y'], label='Fit',
        ).opts(
            color='#FF00FF', alpha=0.35,
            line_color='#FF00FF', line_alpha=0.6,
            responsive=True, shared_axes=False, framewise=True,
        )
        overlay = hv.Overlay([roi_curve, fit_area]).opts(
            hv.opts.Overlay(responsive=True, shared_axes=False, framewise=True, show_legend=True)
        )
        self._update_paneB(overlay)

    def update_plot(self):
        """Refresh paneB based on ROI state (clears fit overlay)."""
        self._reset_nlls_edge_preview_state()
        self._nlls_result_active = False
        if self._region_pairs:
            self._update_paneB(self._figB_region(self._region_pairs))
        else:
            self._update_paneB(self._figB_hover(self._last_hover_point or {"x": 0, "y": 0}))

    @property
    def nlls_result_active(self) -> bool:
        return self._nlls_result_active

    @property
    def nlls_clustering_active(self) -> bool:
        return self._nlls_clustering_active

    @property
    def nlls_edge_preview_active(self) -> bool:
        """Whether paneB is showing the live Elemental component preview."""
        return self._nlls_edge_preview_active

    def _reset_nlls_edge_preview_state(self) -> None:
        """Forget the Edge Definition preview without changing the visible plot."""
        self._nlls_edge_preview_active = False
        self._nlls_edge_preview_plot = None
        self._nlls_edge_preview_previous_plot = None
        self._nlls_edge_preview_previous_result_active = False
        self._nlls_edge_preview_previous_ranges = None

    @staticmethod
    def _nlls_edge_preview_scale(
        energy: np.ndarray,
        spectrum: np.ndarray,
        curve_x: np.ndarray,
        curve_y: np.ndarray,
    ) -> float:
        """Return a positive visual scale for one Elemental component curve.

        The primary estimate is the non-negative one-parameter least-squares
        solution on the energy interval shared by the experimental spectrum and
        the OOS curve.  A percentile ratio is used when that fit is degenerate
        (for example, an all-zero curve or a non-positive correlation).
        """
        energy_order = np.argsort(energy, kind="stable")
        reference_x = energy[energy_order]
        reference_y = spectrum[energy_order]
        curve_order = np.argsort(curve_x, kind="stable")
        sorted_curve_x = curve_x[curve_order]
        sorted_curve_y = curve_y[curve_order]

        # np.interp expects an increasing x axis. Keep one finite sample per
        # coordinate so duplicated acquisition channels cannot destabilize it.
        reference_x, reference_indices = np.unique(reference_x, return_index=True)
        reference_y = reference_y[reference_indices]
        sorted_curve_x, curve_indices = np.unique(
            sorted_curve_x, return_index=True
        )
        sorted_curve_y = sorted_curve_y[curve_indices]

        overlap = (
            (reference_x >= sorted_curve_x[0])
            & (reference_x <= sorted_curve_x[-1])
        )
        overlap_reference = reference_y[overlap]
        if np.count_nonzero(overlap) >= 2:
            overlap_curve = np.interp(
                reference_x[overlap], sorted_curve_x, sorted_curve_y
            )
            finite = np.isfinite(overlap_reference) & np.isfinite(overlap_curve)
            overlap_reference = overlap_reference[finite]
            overlap_curve = overlap_curve[finite]
            if overlap_curve.size:
                denominator = float(np.dot(overlap_curve, overlap_curve))
                numerator = float(np.dot(overlap_curve, overlap_reference))
                if denominator > 0.0 and np.isfinite(denominator):
                    scale = numerator / denominator
                    if np.isfinite(scale) and scale > 0.0:
                        return float(scale)
        else:
            overlap_curve = np.array([], dtype=float)

        # The 95th percentile is insensitive to an isolated hot channel while
        # still placing the normalized OOS close to the experimental signal.
        reference_for_fallback = (
            overlap_reference if overlap_reference.size else reference_y
        )
        curve_for_fallback = (
            overlap_curve if overlap_curve.size else sorted_curve_y
        )
        reference_level = float(
            np.nanpercentile(np.abs(reference_for_fallback), 95.0)
        )
        curve_level = float(np.nanpercentile(np.abs(curve_for_fallback), 95.0))
        if (
            np.isfinite(reference_level)
            and np.isfinite(curve_level)
            and reference_level > 0.0
            and curve_level > 0.0
        ):
            return reference_level / curve_level
        return 1.0

    def show_nlls_edge_preview(
        self,
        energy,
        spectrum,
        curves,
        spectrum_label: str = "Spectrum",
        scale_bases=None,
    ) -> None:
        """Show the spectrum together with visually scaled Elemental components.

        ``curves`` is an iterable of ``(label, x, y)`` tuples. Its input arrays
        are never mutated: scaling is applied only to the HoloViews objects used
        for this preview. ``scale_bases`` may provide one unit-
        amplitude y array per curve; this keeps the visual gain stable while an
        amplitude parameter changes, so the change remains visible.
        """
        energy_values = np.asarray(energy, dtype=float).reshape(-1)
        spectrum_values = np.asarray(spectrum, dtype=float).reshape(-1)
        spectrum_size = min(energy_values.size, spectrum_values.size)
        spectrum_finite = (
            np.isfinite(energy_values[:spectrum_size])
            & np.isfinite(spectrum_values[:spectrum_size])
        )
        if np.count_nonzero(spectrum_finite) < 2:
            raise ValueError(
                "Edge preview needs at least two finite spectrum samples"
            )

        spectrum_x = energy_values[:spectrum_size][spectrum_finite]
        spectrum_y = spectrum_values[:spectrum_size][spectrum_finite]
        spectrum_order = np.argsort(spectrum_x, kind="stable")
        spectrum_x = spectrum_x[spectrum_order]
        spectrum_y = spectrum_y[spectrum_order]

        preview_elements = [
            hv.Curve(
                (spectrum_x, spectrum_y),
                kdims=["x"],
                vdims=["y"],
                label=str(spectrum_label or "Spectrum"),
            ).opts(
                color="black",
                line_width=1.75,
                alpha=0.7,
            )
        ]

        curve_entries = tuple(curves)
        basis_entries = (
            tuple(scale_bases)
            if scale_bases is not None
            else tuple(None for _ in curve_entries)
        )
        if len(basis_entries) != len(curve_entries):
            raise ValueError("Edge preview scale bases must match the curve count")

        for curve_index, (curve, scale_basis) in enumerate(
            zip(curve_entries, basis_entries)
        ):
            try:
                label, x_values, y_values = curve
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Each Edge preview curve must be a (label, x, y) tuple"
                ) from exc

            curve_x = np.asarray(x_values, dtype=float).reshape(-1)
            curve_y = np.asarray(y_values, dtype=float).reshape(-1)
            curve_size = min(curve_x.size, curve_y.size)
            curve_finite = (
                np.isfinite(curve_x[:curve_size])
                & np.isfinite(curve_y[:curve_size])
            )
            if np.count_nonzero(curve_finite) < 2:
                continue

            finite_x = curve_x[:curve_size][curve_finite]
            finite_y = curve_y[:curve_size][curve_finite]
            if scale_basis is None:
                basis_x = finite_x
                basis_y = finite_y
            else:
                raw_basis = np.asarray(scale_basis, dtype=float).reshape(-1)
                basis_size = min(curve_x.size, raw_basis.size)
                basis_finite = (
                    np.isfinite(curve_x[:basis_size])
                    & np.isfinite(raw_basis[:basis_size])
                )
                if np.count_nonzero(basis_finite) < 2:
                    continue
                basis_x = curve_x[:basis_size][basis_finite]
                basis_y = raw_basis[:basis_size][basis_finite]
            scale = self._nlls_edge_preview_scale(
                spectrum_x, spectrum_y, basis_x, basis_y
            )
            scaled_y = finite_y * scale
            if np.any(~np.isfinite(scaled_y)):
                continue

            curve_label = str(label).strip() if label is not None else ""
            if not curve_label:
                curve_label = f"OOS {curve_index + 1}"
            preview_elements.append(
                hv.Curve(
                    (finite_x, scaled_y),
                    kdims=["x"],
                    vdims=["y"],
                    label=curve_label,
                ).opts(
                    color=palettes.Category10[10][curve_index % 10],
                    line_width=2.25,
                )
            )

        preview_plot = hv.Overlay(preview_elements).opts(
            hv.opts.Overlay(
                title="Elemental model preview (visual scale)",
                xlabel=self._X_AXIS_SPECTRUM_TITLE,
                ylabel=self._Y_AXIS_SPECTRUM_TITLE,
                legend_position="top_right",
                responsive=True,
                shared_axes=False,
                framewise=True,
                show_legend=True,
                tools=["hover", "wheel_zoom", "pan", "reset"],
                active_tools=["wheel_zoom"],
            )
        )

        entering_preview = not self._nlls_edge_preview_active
        if entering_preview:
            self._nlls_edge_preview_previous_plot = (
                self._paneB_pipe.data if self._paneB_pipe is not None else None
            )
            self._nlls_edge_preview_previous_result_active = (
                self._nlls_result_active
            )
            self._nlls_edge_preview_previous_ranges = (
                self._current_x_range,
                self._current_y_range,
                self._current_x_autorange,
                self._current_y_autorange,
            )
        self._nlls_result_active = False
        self._nlls_edge_preview_active = True
        self._nlls_edge_preview_plot = preview_plot
        if self._pc and self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None
        if entering_preview:
            self._show_nlls_main_plot(preview_plot)
        else:
            # Shift is adjusted in small increments. Keep the current zoom so
            # the edge onset stays under the user's cursor while it moves.
            self._update_paneB(preview_plot)

    def clear_nlls_edge_preview(self) -> None:
        """Clear the Edge Definition preview and restore the underlying view."""
        if not self._nlls_edge_preview_active:
            return
        previous_plot = self._nlls_edge_preview_previous_plot
        previous_result_active = self._nlls_edge_preview_previous_result_active
        previous_ranges = self._nlls_edge_preview_previous_ranges
        self._reset_nlls_edge_preview_state()
        if self._pc and self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None
        if previous_plot is not None:
            self._nlls_result_active = previous_result_active
            if previous_ranges is not None:
                (
                    self._current_x_range,
                    self._current_y_range,
                    self._current_x_autorange,
                    self._current_y_autorange,
                ) = previous_ranges
            self._update_paneB(previous_plot)
        elif (
            self._nlls_clustering_active
            and self._nlls_clustering_spectra_plot is not None
        ):
            self._show_nlls_main_plot(self._nlls_clustering_spectra_plot)
        elif self._region_pairs:
            self._show_nlls_main_plot(self._figB_region(self._region_pairs))
        else:
            self._show_nlls_main_plot(
                self._figB_hover(self._last_hover_point or {"x": 0, "y": 0})
            )

    def _reset_spectrum_ranges(self) -> None:
        """Let a newly selected NLLS plot determine its complete visible ranges."""
        self._current_x_range = None
        self._current_y_range = None
        self._current_x_autorange = None
        self._current_y_autorange = None

    def _show_nlls_main_plot(self, plot) -> None:
        self._reset_spectrum_ranges()
        self._update_paneB(plot)

    def show_nlls_reference_result(self, plot) -> None:
        """Replace the large ROI/cluster-spectrum pane with an NLLS result plot."""
        if plot is None:
            self.clear_nlls_reference_result()
            return
        self._reset_nlls_edge_preview_state()
        self._nlls_result_active = True
        if self._pc and self._pc.running:
            self._pc.stop()
        self._show_nlls_main_plot(plot)

    def clear_nlls_reference_result(self) -> None:
        """Leave result mode and restore cluster references or the current ROI spectrum."""
        if not self._nlls_result_active:
            return
        self._nlls_result_active = False
        if self._nlls_clustering_active and self._nlls_clustering_spectra_plot is not None:
            self._show_nlls_main_plot(self._nlls_clustering_spectra_plot)
        elif self._region_pairs:
            self._show_nlls_main_plot(self._figB_region(self._region_pairs))
        else:
            self._show_nlls_main_plot(
                self._figB_hover(self._last_hover_point or {"x": 0, "y": 0})
            )

    def show_nlls_clustering(self, labels, energy, cluster_spectra) -> None:
        """Show categorical cluster labels and real mean spectra in the two main panes."""
        label_values = np.asarray(labels)
        if label_values.ndim != 2:
            raise ValueError(
                f"Expected a 2D clustering label map, got shape={label_values.shape}"
            )
        if np.any(~np.isfinite(label_values)) or np.any(label_values != np.floor(label_values)):
            raise ValueError("Clustering labels must be finite integers")
        label_values = label_values.astype(int, copy=False)
        unique_labels = np.unique(label_values)
        if unique_labels.size == 0 or int(unique_labels[0]) < 0:
            raise ValueError("Clustering labels must contain non-negative areas")

        color_count = max(int(unique_labels[-1]) + 1, int(unique_labels.size))
        color_order = [
            3, 7, 15, 11, 19,
            2, 6, 14, 10, 18,
            1, 5, 13, 9, 17,
            0, 4, 12, 8, 16,
        ]
        colors = [
            to_hex(color)
            for color in get_nclusters_cmap(
                "tab20b", color_count, index_order=color_order
            )
        ]

        ny, nx = label_values.shape
        label_image = hv.Image(
            (np.arange(nx), np.arange(ny), label_values.astype(float)),
            kdims=["x", "y"],
            vdims=["Cluster"],
        ).opts(
            cmap=colors,
            clim=(-0.5, color_count - 0.5),
            colorbar=True,
            invert_yaxis=True,
            xaxis=None,
            yaxis=None,
            title=f"Current Clustering — {unique_labels.size} clusters",
            responsive=True,
            shared_axes=False,
            framewise=True,
            tools=["hover", "reset"],
            **self._paneA_aspect_options(nx, ny),
        )

        x_axis = np.asarray(energy, dtype=float).reshape(-1)
        curves = []
        for cluster_label, area_label, spectrum in cluster_spectra:
            y_values = np.asarray(spectrum, dtype=float).reshape(-1)
            size = min(x_axis.size, y_values.size)
            finite = np.isfinite(x_axis[:size]) & np.isfinite(y_values[:size])
            if np.count_nonzero(finite) < 2:
                continue
            label_index = int(cluster_label)
            curves.append(
                hv.Curve(
                    (x_axis[:size][finite], y_values[:size][finite]),
                    kdims=["Energy loss (eV)"],
                    vdims=["Electron count"],
                    label=str(area_label),
                ).opts(
                    color=colors[label_index % len(colors)],
                    line_width=2,
                )
            )
        if not curves:
            curves.append(
                hv.Curve(
                    ([], []),
                    kdims=["Energy loss (eV)"],
                    vdims=["Electron count"],
                )
            )
        spectra_plot = hv.Overlay(curves).opts(
            hv.opts.Overlay(
                title="Cluster reference spectra",
                xlabel="Energy loss (eV)",
                ylabel="Electron count",
                legend_position="top_right",
                responsive=True,
                shared_axes=False,
                framewise=True,
                show_legend=True,
                tools=["hover", "wheel_zoom", "pan", "reset"],
                active_tools=["wheel_zoom"],
            )
        )

        self._nlls_result_active = False
        self._reset_nlls_edge_preview_state()
        self._nlls_clustering_active = True
        self._nlls_clustering_spectra_plot = spectra_plot
        self._nx, self._ny = nx, ny
        self._publish_paneA_ratio()
        # Publish the cluster map exactly the way the Clustering page does
        # (ClusteringSpectrumImagePlot._update_clustering_plots): overlay it with
        # the selection layer, point the hover source at the image and let
        # _update_selection_overlay() recompose through _paneA_overlay_options().
        # Assigning paneA.object directly, as this method used to, skipped those
        # shared options - which is how the map lost its aspect and its hover gate.
        self._paneA_base_overlay = label_image * self._selectors  # type: ignore
        self._hover_source = label_image
        self._update_selection_overlay([])
        self._nlls_clustering_label_plot = self.paneA.object
        self._show_nlls_main_plot(spectra_plot)

    def clear_nlls_clustering(self) -> None:
        """Restore the integrated image after leaving clustered-area mode."""
        if not self._nlls_clustering_active:
            return
        self.plot_image()

    def plot_image(self):
        """Re-render the integrated intensity heatmap and reset fit/spectra shared state."""
        self._reset_nlls_edge_preview_state()
        self._nlls_result_active = False
        self._nlls_clustering_active = False
        self._nlls_clustering_label_plot = None
        self._nlls_clustering_spectra_plot = None
        display_data = self._get_display_data()

        try:
            self._energy = np.asarray(display_data.coords[self._model.constants.ELOSS].values)
        except Exception:
            self._energy = np.asarray(self._e_axis)

        m_image_da = display_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Expected 2D integrated image, got shape={m_image.shape}")

        ny, nx = m_image.shape
        self._nx, self._ny = nx, ny
        self._publish_paneA_ratio()
        img = hv.Image(
            (np.arange(nx), np.arange(ny), m_image),
            kdims=['x', 'y'], vdims=['Intensity'],
        ).opts(
            cmap='Greys_r', colorbar=False,
            xaxis=None, yaxis=None,
            invert_yaxis=True,
            responsive=True, shared_axes=False,
        )
        self._paneA_base_overlay = img * self._selectors
        self._update_selection_overlay(self._region_pairs)

        # Streams remain connected to self._selectors — no rewiring needed.

        self._hover_blocked = False
        self._last_hover_ts = None

        # Restore paneB to whatever was showing before the energy map was opened.
        app_state = CacheManager.get_cached_app_state()
        if app_state.fitting_results is not None:
            self.plot_fitting(self._energy, app_state.fitting_results)
        elif self._region_pairs:
            self._update_paneB(self._figB_region(self._region_pairs))
        else:
            self._update_paneB(self._figB_hover(self._last_hover_point or {"x": 0, "y": 0}))

    def plot_energy_map(self, energy_map):
        """Render a model-computed 2D energy map on paneA."""
        # This method only replaces paneA. Restore paneB before dropping the
        # preview flag so a hidden OOS overlay cannot outlive its mode.
        self.clear_nlls_edge_preview()
        self._nlls_result_active = False
        self._nlls_clustering_active = False
        self._nlls_clustering_label_plot = None
        self._nlls_clustering_spectra_plot = None
        energy_map_arr = np.asarray(energy_map)
        if energy_map_arr.ndim != 2:
            raise ValueError(f"Expected a 2D energy map, got shape={energy_map_arr.shape}")
        energy_map_arr = np.where(np.isfinite(energy_map_arr), energy_map_arr, 0.0)
        ny, nx = energy_map_arr.shape

        _energy_map_cmap = LinearSegmentedColormap.from_list('energy_map', ['#00eb6c', '#ff1493'])

        img = hv.Image(
            (np.arange(nx), np.arange(ny), energy_map_arr),
            kdims=['x', 'y'], vdims=['Energy'],
        ).opts(
            cmap=_energy_map_cmap,
            colorbar=True,
            xaxis=None, yaxis=None,
            invert_yaxis=True,
            responsive=True, shared_axes=False,
            title='Energy Map',
        )
        self._nx, self._ny = nx, ny
        self._publish_paneA_ratio()
        self._paneA_base_overlay = img * self._selectors
        overlay_options = self._paneA_overlay_options()
        overlay_options["active_tools"] = ["lasso_select"]
        self.paneA.object = self._paneA_base_overlay.opts(
            hv.opts.Overlay(**overlay_options)
        )

    def reset_for_data_source_change(self):
        """Hard-reset derived fitting state after raw/preprocessed source switches.

        Keeps component definitions in the sidebar/model, but clears:
        - fit overlay/results cache
        - ROI/lasso selection
        - transient hover/timer state
        """
        app_state = CacheManager.get_cached_app_state()
        app_state.fitting_results = None
        app_state.spectra = None

        # Ignore stale Selection1D events for a short window while streams settle.
        self._ignore_selection_until_ms = self._now_ms() + max(700, self._SELECTION_DEBOUNCE_MS)

        # Clear current lasso/ROI and unblock hover interactions.
        self._on_paneA_double_tap()
        self._pending_selection_index = None
        self._pending_selection_ts = None

        # Reset transient interaction state and any saved zoom ranges.
        self._last_hover_ts = None
        self._last_hover_point = {"x": 0, "y": 0}
        self._current_x_range = None
        self._current_y_range = None
        self._current_x_autorange = None
        self._current_y_autorange = None
        if self._pc and self._pc.running:
            self._pc.stop()

        # Rebuild base image from the selected source and restore plain spectrum view.
        self.plot_image()
        self._update_paneB(self._figB_hover({"x": 0, "y": 0}))

    @override
    def _on_paneA_selected(self, index=None):
        """Debounce selection and ignore stale lasso events right after source switches."""
        if self._now_ms() < self._ignore_selection_until_ms:
            return
        super()._on_paneA_selected(index)

    def _update_selection_overlay(self, pairs):
        """Inherited from base — red-dot overlay recomposition."""
        super()._update_selection_overlay(pairs)

    # --- Inactivity timer ---

    def _now_ms(self):
        return int(time.time() * 1000)

    def _check_inactivity(self):
        """Restore ROI after hover preview times out."""
        if self._nlls_result_active or self._nlls_clustering_active:
            if self._pc and self._pc.running:
                self._pc.stop()
            return
        if not self._region_pairs:
            if self._pc and self._pc.running:
                self._pc.stop()
            return
        if self._last_hover_ts is None:
            if self._pc and self._pc.running:
                self._pc.stop()
            return
        if self._now_ms() - self._last_hover_ts >= self._INACTIVITY_MS:
            app_state = CacheManager.get_cached_app_state()
            if (
                self._nlls_edge_preview_active
                and self._nlls_edge_preview_plot is not None
            ):
                self._update_paneB(self._nlls_edge_preview_plot)
            elif app_state.fitting_results is not None:
                self.plot_fitting(self._energy, app_state.fitting_results)
            else:
                self._update_paneB(self._figB_region(self._region_pairs))
            if self._pc and self._pc.running:
                self._pc.stop()

    # --- Overridden event handlers ---

    @override
    def _on_paneA_hover(self, x=None, y=None):
        if not self._inside_spatial_map(x, y):
            return
        self._queue_hover(x, y)

    def _handle_hover_render(self, point):
        if not self._inside_spatial_map(point.get("x"), point.get("y")):
            return
        if (
            self._hover_blocked
            or self._nlls_result_active
            or self._nlls_clustering_active
            or self._nlls_edge_preview_active
        ):
            return
        if not self._region_pairs and self._try_fast_hover_update(point):
            return
        if self._region_pairs:
            self._update_paneB(self._figB_hover(point))
            self._last_hover_ts = self._now_ms()
            if self._pc and not self._pc.running:
                self._pc.start()
        else:
            self._show_spectrum(point=point)

    @override
    def _on_paneA_click(self, x=None, y=None):
        if not self._inside_spatial_map(x, y):
            return
        if self._nlls_result_active or self._nlls_clustering_active:
            return
        self._last_hover_pixel = (round(y), round(x))
        if self._pending_selection_ts is not None or self._hover_blocked:
            return
        app_state = CacheManager.get_cached_app_state()
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            if (
                self._nlls_edge_preview_active
                and self._nlls_edge_preview_plot is not None
            ):
                self._update_paneB(self._nlls_edge_preview_plot)
            elif app_state.fitting_results is not None:
                self.plot_fitting(self._energy, app_state.fitting_results)
            else:
                self._last_hover_ts = self._now_ms()
                if self._pc and not self._pc.running:
                    self._pc.start()
        else:
            if self._pc and self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            if (
                self._nlls_edge_preview_active
                and self._nlls_edge_preview_plot is not None
            ):
                self._update_paneB(self._nlls_edge_preview_plot)
            else:
                self._show_spectrum(point=point)

    @override
    def _process_selection(self, index=None):
        """Commit selection: use fitting_results if available, else show ROI spectrum."""
        pairs = self._index_to_pairs(index)
        self._region_pairs = pairs
        self._update_selection_overlay(pairs)
        if not pairs:
            self._hover_blocked = False
            if self._pc and self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            if self._last_hover_point is not None:
                self._update_paneB(self._figB_hover(self._last_hover_point))
            if self.on_selection_change:
                self.on_selection_change(False)
            return
        app_state = CacheManager.get_cached_app_state()
        if self.on_region_committed:
            self.on_region_committed()
        elif app_state.fitting_results is not None:
            self.plot_fitting(self._energy, app_state.fitting_results)
        else:
            self._show_spectrum(region_pairs=pairs)
        if self._pc and self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None
        self._hover_blocked = True
        if self.on_selection_change:
            self.on_selection_change(True)

    @override
    def _on_paneA_double_tap(self, x=None, y=None):
        """Reset selection (base), stop inactivity timer, optionally show hover spectrum."""
        super()._on_paneA_double_tap(x, y)
        self._last_hover_ts = None
        if self._pc and self._pc.running:
            self._pc.stop()
        if x is not None and y is not None:
            point = {"x": x, "y": y}
            self._last_hover_point = point
            if (
                self._nlls_edge_preview_active
                and self._nlls_edge_preview_plot is not None
            ):
                self._update_paneB(self._nlls_edge_preview_plot)
            else:
                self._show_spectrum(point=point)

    # --- Cleanup ---

    @override
    def cleanup(self):
        self._pending_selection_index = None
        self._pending_selection_ts = None
        if self._pc is not None:
            try:
                if self._pc.running:
                    self._pc.stop()
            except Exception:
                pass
        super().cleanup()
