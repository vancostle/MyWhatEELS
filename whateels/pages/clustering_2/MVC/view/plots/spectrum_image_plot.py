"""Clustering-2 spectrum image visualizer.

Extends BaseSpectrumImagePlot for the UMAP + HDBSCAN workflow.

Initially shows the integrated intensity heatmap. After HDBSCAN runs,
``update_hdbscan_results()`` replaces:
  - paneA → HDBSCAN cluster label map
  - paneB → mean spectra per cluster

Hover on paneA shows the hovered pixel's raw spectrum overlaid with the
corresponding cluster-centre spectrum.
"""

import numpy as np
import holoviews as hv
import xarray as xr
from holoviews import streams as hv_streams

from whateels.base.plots import BaseSpectrumImagePlot
from typing import override, TYPE_CHECKING

if TYPE_CHECKING:
    from xarray import Dataset


class Clustering2SpectrumImagePlot(BaseSpectrumImagePlot):
    """
    Spectrum image visualizer for the clustering_2 (UMAP + HDBSCAN) page.

    Extends ``BaseSpectrumImagePlot`` with:
    - Hover-only interaction on paneA (no lasso/box selection).
    - ``update_hdbscan_results()``: swaps paneA to the HDBSCAN cluster label map
      and paneB to mean spectra per cluster.
    - Hover shows the hovered pixel's raw spectrum overlaid with its cluster
      centre spectrum (once HDBSCAN results are available).
    """

    def __init__(self, dataset: "Dataset", eloss_name: str = 'Eloss') -> None:
        # HDBSCAN state — must exist before super().__init__ triggers _setup_plots()
        self._cluster_labels_2d: np.ndarray | None = None   # (ny, nx) int labels
        self._cluster_centers: dict[int, np.ndarray] = {}   # label → mean spectrum (1-D)
        self._cmap_colors: list[str] = []                    # hex colour per unique label
        self._current_norm: str = 'none'                     # normalization used for paneB spectra
        self._paneB_hover_frozen = False
        self._hover_disabled = False
        self._paneB_view_mode = 'spectrum'
        self._last_hover_cluster_label: int | None = None
        self._last_paneA_click_ts: int | None = None
        self._last_paneA_click_pixel: tuple[int, int] | None = None
        self._suppress_click_until_ms = 0
        self._suppress_double_tap_until_ms = 0
        self._suppress_hover_until_ms = 0
        self._DOUBLE_CLICK_MS = 450
        self._DOUBLE_CLICK_PIXEL_TOLERANCE = 2

        super().__init__(dataset, eloss_name, paneA_select_tools=[])
        self._rewire_paneA_event_streams()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def update_hdbscan_results(self, hdbscan_results, cmap_obj: dict, electron_count_data=None, available_norm: str = 'none') -> None:
        """
        Swap paneA to the HDBSCAN cluster label map and paneB to mean spectra.

        Args:
            hdbscan_results:     Fitted HDBSCAN object with a ``labels_`` attribute.
            cmap_obj:            Dict with a ``'colors'`` key — list of hex colours,
                                 one per unique label (including noise label −1 if present).
            electron_count_data: The ElectronCount DataArray that was actually fed to
                                 UMAP/HDBSCAN (may differ from the raw dataset when the
                                 "use preprocessed" switch is on). When provided, the
                                 plot's internal data and energy axis are updated to match
                                 so that mean spectra are drawn with the correct Eloss range.
            available_norm:      Normalization method used before UMAP/HDBSCAN.
        """
        self._current_norm = str(available_norm).lower()

        if electron_count_data is not None:
            self._electron_count_data = electron_count_data
            try:
                self._energy = np.asarray(electron_count_data.coords[self._eloss_name].values)
            except Exception:
                self._energy = np.arange(electron_count_data.shape[-1])

        data_np = np.asarray(self._electron_count_data.fillna(0.0))
        ny, nx = data_np.shape[0], data_np.shape[1]

        labels_flat = np.asarray(hdbscan_results.labels_)
        labels_2d = labels_flat.reshape(ny, nx)
        self._cluster_labels_2d = labels_2d
        self._cmap_colors = list(cmap_obj.get('colors', []))

        # Pre-compute mean spectrum per unique cluster label
        flat_data = data_np.reshape(-1, data_np.shape[2])
        self._cluster_centers = {
            int(label): flat_data[labels_flat == label].mean(axis=0)
            for label in np.unique(labels_flat)
        }
        self._paneB_hover_frozen = False
        self._hover_disabled = False
        self._last_paneA_click_ts = None
        self._last_paneA_click_pixel = None
        self._suppress_click_until_ms = 0
        self._suppress_double_tap_until_ms = 0
        self._suppress_hover_until_ms = 0

        self._update_paneA_cluster_map(labels_2d, nx, ny)
        self._update_paneB_mean_spectra()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _update_paneA_cluster_map(self, labels_2d: np.ndarray, nx: int, ny: int) -> None:
        """Replace paneA content with an HDBSCAN cluster-label heatmap."""
        cmap = self._cmap_colors if self._cmap_colors else 'Category20'
        def _integer_colorbar_hook(plot, element):
            fig = getattr(plot, 'state', None)
            if fig is None:
                return
            try:
                from bokeh.models import FixedTicker, NumeralTickFormatter
                min_label = int(np.nanmin(labels_2d))
                max_label = int(np.nanmax(labels_2d))
                ticks = list(range(min_label, max_label + 1))
                for cb in getattr(fig, 'right', []) or []:
                    try:
                        if hasattr(cb, 'ticker'):
                            cb.ticker = FixedTicker(ticks=ticks)
                        if hasattr(cb, 'formatter'):
                            cb.formatter = NumeralTickFormatter(format='0')
                    except Exception:
                        continue
            except Exception:
                return

        img = hv.Image(
            xr.Dataset(
                {'Labels': (['y', 'x'], labels_2d)},
                coords={'x': np.arange(nx), 'y': np.arange(ny)},
            ),
            kdims=['x', 'y'],
        ).opts(
            xaxis=None,
            yaxis=None,
            colorbar=True,
            invert_yaxis=True,
            responsive=True,
            shared_axes=False,
            cmap=cmap,
            hooks=[_integer_colorbar_hook],
            title='HDBSCAN cluster map',
        )
        self._hover_source = img
        self._paneA_base_overlay = img * self._selectors  # type: ignore[operator]
        self._update_selection_overlay([])
        self._rewire_paneA_event_streams()

    def _update_paneB_mean_spectra(self) -> None:
        """Push mean-spectra-per-cluster through the paneB pipe."""
        if not self._cluster_centers or self._paneB_pipe is None:
            return

        curves = []
        for idx, (label, center) in enumerate(self._cluster_centers.items()):
            color = (
                self._cmap_colors[idx % len(self._cmap_colors)]
                if self._cmap_colors
                else 'steelblue'
            )
            curves.append(hv.Curve(
                (self._energy, center),
                kdims=['x'],
                vdims=['y'],
                label=f'Cluster {label}',
            ).opts(
                color=color,
                line_width=2,
                responsive=True,
                shared_axes=False,
                framewise=True,
            ))

        overlay = hv.Overlay(curves).opts(
            xlabel='Energy Loss (eV)',
            ylabel=self._get_intensity_ylabel(),
            title='All cluster centers',
            legend_position='top_right',
            responsive=True,
            shared_axes=False,
            framewise=True,
            show_legend=True,
        )
        # Reset ranges so the view autoscales on the centroid overview.
        self._current_x_range = None
        self._current_y_range = None
        self._paneB_view_mode = 'centroids'
        self._last_hover_cluster_label = None
        self._push_paneB_figure(overlay)

    def _push_paneB_figure(self, fig) -> None:
        """Keep paneB on the Pipe-backed DynamicMap, then send the new figure."""
        if (
            self.paneB is not None
            and self._paneB_dmap is not None
            and self.paneB.object is not self._paneB_dmap
        ):
            self.paneB.object = self._paneB_dmap
        self._update_paneB(fig)

    def _get_intensity_ylabel(self) -> str:
        """Return the paneB intensity label for the active normalization."""
        if self._current_norm and self._current_norm != 'none':
            return f'Normalized intensity ({self._current_norm})'
        return 'Intensity (a.u.)'

    def _cluster_color_for_label(self, label: int) -> str:
        """Return the colour assigned to a cluster label."""
        if not self._cmap_colors:
            return 'steelblue'
        labels = list(self._cluster_centers.keys())
        try:
            idx = labels.index(int(label))
        except ValueError:
            idx = 0
        return self._cmap_colors[idx % len(self._cmap_colors)]

    def _cluster_point_info(self, point):
        if not point or self._cluster_labels_2d is None:
            return None
        i, j = round(point["y"]), round(point["x"])
        if i < 0 or j < 0:
            return None
        try:
            label = int(self._cluster_labels_2d[i, j])
        except Exception:
            return None
        return i, j, label

    def _figB_cluster_hover(self, point):
        """Return hovered pixel spectrum overlaid with its cluster centroid."""
        if not point:
            point = {"x": 0, "y": 0}
        if self._cluster_labels_2d is None or not self._cluster_centers:
            return self._figB_hover(point)

        point_info = self._cluster_point_info(point)
        if point_info is None:
            return None
        i, j, label = point_info

        center = self._cluster_centers.get(label)
        if center is None:
            return None

        data_values = self._get_display_numpy()
        try:
            spec = data_values[i, j, :]
        except Exception:
            try:
                spec = data_values[j, i, :]
            except Exception:
                return None

        pixel_curve = hv.Curve(
            (self._energy, spec),
            kdims=['x'],
            vdims=['y'],
            label=f'Pixel x={j}, y={i}',
        ).opts(
            color='black',
            line_width=1.5,
            alpha=0.75,
            responsive=True,
            shared_axes=False,
            framewise=True,
        )
        centroid_curve = hv.Curve(
            (self._energy, center),
            kdims=['x'],
            vdims=['y'],
            label=f'Cluster {label} centroid',
        ).opts(
            color=self._cluster_color_for_label(label),
            line_width=2.5,
            responsive=True,
            shared_axes=False,
            framewise=True,
        )

        return hv.Overlay([pixel_curve, centroid_curve]).opts(
            xlabel='Energy Loss (eV)',
            ylabel=self._get_intensity_ylabel(),
            title=f'Pixel spectrum and cluster {label} centroid',
            legend_position='top_right',
            responsive=True,
            shared_axes=False,
            framewise=True,
            show_legend=True,
        )

    def _show_cluster_hover(self, point) -> None:
        point_info = self._cluster_point_info(point)
        if point_info is None:
            return
        _, _, label = point_info
        if self._try_fast_cluster_hover_update(point, label):
            return

        fig = self._figB_cluster_hover(point)
        if fig is not None:
            self._push_paneB_figure(fig)
            self._paneB_view_mode = 'cluster_hover'
            self._last_hover_cluster_label = label

    def _try_fast_cluster_hover_update(self, point, label: int) -> bool:
        """Update the pixel curve in-place while staying inside the same cluster."""
        if (
            self._paneB_view_mode != 'cluster_hover'
            or self._last_hover_cluster_label != int(label)
        ):
            return False

        bokeh_plot = self._get_live_paneB_bokeh_plot()
        if bokeh_plot is None:
            return False

        point_info = self._cluster_point_info(point)
        if point_info is None:
            return False
        i, j, _ = point_info

        try:
            data_values = self._get_display_numpy()
            try:
                spec = data_values[i, j, :]
            except Exception:
                spec = data_values[j, i, :]

            line_renderers = []
            for candidate in getattr(bokeh_plot, 'renderers', []) or []:
                source = getattr(candidate, 'data_source', None)
                if source is not None and 'x' in source.data and 'y' in source.data:
                    line_renderers.append(candidate)
            if not line_renderers:
                return False

            line_renderers[0].data_source.data = {
                'x': self._energy,
                'y': spec,
            }
            return True
        except Exception:
            return False

    def _clear_hover_queue(self) -> None:
        self._hover_pending_point = None
        self._hover_last_event_ts = None
        self._hover_last_render_ts = None
        if self._hover_pc is not None:
            try:
                if self._hover_pc.running:
                    self._hover_pc.stop()
            except Exception:
                pass

    def _clear_stream(self, attr_name: str, callback) -> None:
        stream = getattr(self, attr_name, None)
        if stream is not None:
            try:
                stream.remove_subscriber(callback)
            except Exception:
                pass
            try:
                stream.clear()
            except Exception:
                pass
        setattr(self, attr_name, None)

    def _rewire_paneA_event_streams(self) -> None:
        """Listen for tap/double-tap on the image layer, not invisible points."""
        source = self._hover_source if self._hover_source is not None else self._selectors
        self._clear_stream('_tap_stream', self._on_paneA_click)
        self._clear_stream('_double_tap_stream', self._on_paneA_double_tap)
        self._clear_stream('_selection_stream', self._on_paneA_selected)
        if source is None:
            return

        self._tap_stream = hv_streams.Tap(source=source)
        self._tap_stream.add_subscriber(self._on_paneA_click)
        self._double_tap_stream = hv_streams.DoubleTap(source=source)
        self._double_tap_stream.add_subscriber(self._on_paneA_double_tap)

    def _is_manual_double_click(self, now_ms: int, pixel: tuple[int, int]) -> bool:
        if self._last_paneA_click_ts is None or self._last_paneA_click_pixel is None:
            return False
        if now_ms - self._last_paneA_click_ts > self._DOUBLE_CLICK_MS:
            return False
        prev_y, prev_x = self._last_paneA_click_pixel
        y, x = pixel
        return max(abs(y - prev_y), abs(x - prev_x)) <= self._DOUBLE_CLICK_PIXEL_TOLERANCE

    def _show_all_cluster_centers(self, x=None, y=None) -> None:
        """Show only centroids and absorb tap/hover events produced by the gesture."""
        now = self._now_ms()
        self._paneB_hover_frozen = False
        self._hover_disabled = True
        self._last_paneA_click_ts = None
        self._last_paneA_click_pixel = None
        self._suppress_click_until_ms = now + 350
        self._suppress_hover_until_ms = now + 350
        self._clear_hover_queue()
        if x is not None and y is not None:
            current_pixel = (round(y), round(x))
            self._last_hover_pixel = current_pixel
            self._hover_last_event_pixel = current_pixel
            self._hover_last_event_xy = (float(x), float(y))
        if self._cluster_centers:
            self._update_paneB_mean_spectra()

    def _enable_hover_mode(self, x=None, y=None) -> None:
        self._paneB_hover_frozen = False
        self._hover_disabled = False
        self._last_paneA_click_ts = None
        self._last_paneA_click_pixel = None
        self._suppress_click_until_ms = self._now_ms() + 350
        self._suppress_hover_until_ms = 0
        self._clear_hover_queue()
        self._paneB_view_mode = 'centroids'
        self._last_hover_cluster_label = None

        if x is not None and y is not None:
            point = {"x": x, "y": y}
        elif self._last_hover_point is not None:
            point = self._last_hover_point
        else:
            point = {"x": 0, "y": 0}

        self._last_hover_point = point
        self._last_hover_pixel = None
        self._hover_last_event_pixel = None
        self._hover_last_event_xy = None
        if self._cluster_centers:
            self._show_cluster_hover(point)
        else:
            self._show_spectrum(point=point)

    # ------------------------------------------------------------------ #
    # HoloViews stream overrides                                           #
    # ------------------------------------------------------------------ #

    @override
    def _on_paneA_hover(self, x=None, y=None) -> None:
        """Queue hover updates when PointerXY is used instead of the JS gate."""
        if self._now_ms() < self._suppress_hover_until_ms:
            return
        if self._hover_disabled or self._paneB_hover_frozen or x is None or y is None:
            return
        self._queue_hover(x, y)

    @override
    def _handle_hover_render(self, point) -> None:
        if self._now_ms() < self._suppress_hover_until_ms:
            return
        if self._hover_disabled or self._paneB_hover_frozen:
            return
        if self._cluster_labels_2d is None or not self._cluster_centers:
            super()._handle_hover_render(point)
            return
        self._show_cluster_hover(point)

    @override
    def _on_paneA_click(self, x=None, y=None) -> None:
        if x is None or y is None:
            return
        now = self._now_ms()
        if now < self._suppress_click_until_ms:
            return
        current_pixel = (round(y), round(x))
        if self._is_manual_double_click(now, current_pixel):
            self._suppress_double_tap_until_ms = now + 350
            if self._hover_disabled:
                self._enable_hover_mode(x, y)
            else:
                self._show_all_cluster_centers(x, y)
            return

        if self._hover_disabled:
            self._last_paneA_click_ts = now
            self._last_paneA_click_pixel = current_pixel
            return

        point = {"x": x, "y": y}
        self._last_paneA_click_ts = now
        self._last_paneA_click_pixel = current_pixel
        self._paneB_hover_frozen = True
        self._last_hover_point = point
        self._last_hover_pixel = current_pixel
        self._clear_hover_queue()
        if self._cluster_labels_2d is None or not self._cluster_centers:
            self._show_spectrum(point=point)
            return
        self._show_cluster_hover(point)

    @override
    def _on_paneA_double_tap(self, x=None, y=None) -> None:
        """Toggle between hover mode and all-cluster-centers display."""
        if self._now_ms() < self._suppress_double_tap_until_ms:
            return
        super()._on_paneA_double_tap(x, y)
        if self._hover_disabled:
            self._enable_hover_mode(x, y)
        else:
            self._show_all_cluster_centers(x, y)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def cleanup(self) -> None:
        """Release HDBSCAN arrays and delegate to base cleanup."""
        self._cluster_labels_2d = None
        self._cluster_centers = {}
        self._cmap_colors = []
        self._current_norm = 'none'
        self._paneB_hover_frozen = False
        self._hover_disabled = False
        self._paneB_view_mode = 'spectrum'
        self._last_hover_cluster_label = None
        self._last_paneA_click_ts = None
        self._last_paneA_click_pixel = None
        self._suppress_click_until_ms = 0
        self._suppress_double_tap_until_ms = 0
        self._suppress_hover_until_ms = 0
        super().cleanup()
