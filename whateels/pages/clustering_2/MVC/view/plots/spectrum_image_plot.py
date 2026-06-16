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
import panel as pn
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
        self._cluster_label_order: list[int] = []
        self._active_cluster_label: int | None = None
        self._current_norm: str = 'none'                     # normalization used for paneB spectra
        self._frozen_pixel: tuple[int, int] | None = None
        self._hover_disabled = False
        self._paneB_view_mode = 'spectrum'
        self._last_hover_cluster_label: int | None = None
        self._last_rendered_pixel: tuple[int, int] | None = None
        self._suppress_click_until_ms = 0
        self._color_picker = None
        self._color_picker_watcher = None
        self._color_change_callback = None
        self._suppress_color_picker_callbacks = False

        super().__init__(dataset, eloss_name, paneA_select_tools=[])
        self._paneB_structure: tuple | None = (('Curve', ''),)
        self._rewire_paneA_event_streams()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def bind_color_picker(self, color_picker, on_colors_changed=None) -> None:
        """Bind a sidebar color picker to the currently selected cluster."""
        if self._color_picker is not None and self._color_picker_watcher is not None:
            try:
                self._color_picker.param.unwatch(self._color_picker_watcher)
            except Exception:
                pass

        self._color_picker = color_picker
        self._color_change_callback = on_colors_changed
        self._color_picker_watcher = color_picker.param.watch(
            self._on_color_picker_changed,
            'value',
        )

    @property
    def cmap_obj(self) -> dict:
        """Return the current colors in the cmap object format used by UMAP plots."""
        return {"colors": list(self._cmap_colors)}

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
            self._display_numpy_cache = None
            self._display_numpy_cache_source = None

        data_np = np.asarray(self._electron_count_data.fillna(0.0))
        ny, nx = data_np.shape[0], data_np.shape[1]

        labels_flat = np.asarray(hdbscan_results.labels_, dtype=int)
        labels_2d = labels_flat.reshape(ny, nx)
        self._cluster_labels_2d = labels_2d
        self._cmap_colors = list(cmap_obj.get('colors', []))
        self._cluster_label_order = [int(label) for label in np.unique(labels_flat)]
        self._ensure_color_count()

        # Pre-compute mean spectrum per unique cluster label
        flat_data = data_np.reshape(-1, data_np.shape[2])
        self._cluster_centers = {
            int(label): flat_data[labels_flat == label].mean(axis=0)
            for label in self._cluster_label_order
        }
        self._frozen_pixel = None
        self._hover_disabled = False
        self._hover_blocked = False
        self._active_cluster_label = None
        self._last_rendered_pixel = None
        self._suppress_click_until_ms = 0
        self._clear_hover_queue()

        self._update_paneA_cluster_map(labels_2d, nx, ny)
        self._update_paneB_mean_spectra()
        self._init_color_picker_from_default_pixel()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _ensure_color_count(self) -> None:
        """Keep one color for each label in ``_cluster_label_order``."""
        if not self._cluster_label_order:
            self._cmap_colors = []
            return

        if not self._cmap_colors:
            self._cmap_colors = ['steelblue'] * len(self._cluster_label_order)
            return

        if len(self._cmap_colors) < len(self._cluster_label_order):
            self._cmap_colors.extend(
                ['steelblue'] * (len(self._cluster_label_order) - len(self._cmap_colors))
            )
        elif len(self._cmap_colors) > len(self._cluster_label_order):
            self._cmap_colors = self._cmap_colors[:len(self._cluster_label_order)]

    def _label_to_color_index(self, label: int) -> int | None:
        try:
            return self._cluster_label_order.index(int(label))
        except ValueError:
            return None

    def _set_color_picker_from_label(self, label: int) -> None:
        idx = self._label_to_color_index(label)
        if idx is None or idx >= len(self._cmap_colors):
            return

        self._active_cluster_label = int(label)
        if self._color_picker is None:
            return

        self._suppress_color_picker_callbacks = True
        try:
            self._color_picker.name = f"Cluster {label}"
            self._color_picker.value = self._cmap_colors[idx]
            self._color_picker.disabled = False
        finally:
            self._suppress_color_picker_callbacks = False

    def _init_color_picker_from_default_pixel(self) -> None:
        if self._cluster_labels_2d is None:
            return
        try:
            self._set_color_picker_from_label(int(self._cluster_labels_2d[0, 0]))
        except Exception:
            pass

    def _refresh_cluster_visuals(self) -> None:
        """Rebuild the cluster map and active spectrum view with current colors."""
        if self._cluster_labels_2d is None or not self._cluster_centers:
            return

        ny, nx = self._cluster_labels_2d.shape
        self._update_paneA_cluster_map(self._cluster_labels_2d, nx, ny)

        if self._hover_disabled:
            self._update_paneB_mean_spectra(
                title='All cluster centers (Double Click again to re-enable hover)',
            )
        elif self._frozen_pixel is not None:
            i, j = self._frozen_pixel
            self._show_cluster_hover(
                {"x": j, "y": i},
                title_prefix='Click (Frozen)',
                allow_fast=False,
            )
        elif self._last_hover_point is not None:
            self._show_cluster_hover(self._last_hover_point, title_prefix='Hover', allow_fast=False)
        else:
            self._update_paneB_mean_spectra()

    def _on_color_picker_changed(self, event) -> None:
        """Apply the picked color to the selected cluster and refresh all local plots."""
        if self._suppress_color_picker_callbacks:
            return
        if self._cluster_labels_2d is None or self._active_cluster_label is None:
            return

        idx = self._label_to_color_index(self._active_cluster_label)
        if idx is None or idx >= len(self._cmap_colors):
            return

        self._cmap_colors[idx] = event.new
        self._refresh_cluster_visuals()
        if self._color_change_callback is not None:
            self._color_change_callback(list(self._cmap_colors))

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

    def _update_paneB_mean_spectra(self, title: str = 'All cluster centers', defer: bool = False) -> None:
        """Push mean-spectra-per-cluster through the paneB pipe."""
        if not self._cluster_centers or self._paneB_pipe is None:
            return

        def _send() -> None:
            if defer and not self._hover_disabled:
                return

            curves = []
            label_order = self._cluster_label_order or list(self._cluster_centers.keys())
            for label in label_order:
                center = self._cluster_centers.get(label)
                if center is None:
                    continue
                curves.append(hv.Curve(
                    (self._energy, center),
                    kdims=['x'],
                    vdims=['y'],
                    label=f'Cluster {label}',
                ).opts(
                    color=self._cluster_color_for_label(label),
                    line_width=2,
                    responsive=True,
                    shared_axes=False,
                    framewise=True,
                ))

            overlay = hv.Overlay(curves).opts(
                xlabel='Energy Loss (eV)',
                ylabel=self._get_intensity_ylabel(),
                title=title,
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
            self._last_rendered_pixel = None
            self._push_paneB_figure(overlay)

        if defer:
            doc = pn.state.curdoc
            if doc is not None:
                doc.add_next_tick_callback(_send)
                return
        _send()

    def _push_paneB_figure(self, fig) -> None:
        """Keep paneB on the Pipe-backed DynamicMap, then send the new figure."""
        if (
            self.paneB is not None
            and self._paneB_dmap is not None
            and self.paneB.object is not self._paneB_dmap
        ):
            self.paneB.object = self._paneB_dmap
        self._update_paneB(fig)

    @staticmethod
    def _paneB_fig_signature(fig):
        """Return a lightweight structure signature for paneB overlays."""
        try:
            elements = list(fig.values()) if isinstance(fig, hv.Overlay) else [fig]
            return tuple((type(el).__name__, getattr(el, 'label', '')) for el in elements)
        except Exception:
            return None

    def _rebuild_paneB_pipe(self, seed_fig) -> None:
        """Replace the Pipe/DynamicMap so Bokeh renders the current overlay shape."""
        if self._rangexy_stream is not None:
            try:
                self._rangexy_stream.remove_subscriber(self._on_paneB_range_changed)
            except Exception:
                pass
            try:
                self._rangexy_stream.clear()
            except Exception:
                pass
            self._rangexy_stream = None

        self._paneB_pipe = hv_streams.Pipe(data=None)
        self._paneB_dmap = hv.DynamicMap(lambda data: data, streams=[self._paneB_pipe])
        self._paneB_pipe.send(self._set_ranges_and_convert(seed_fig))
        self._rangexy_stream = hv_streams.RangeXY(source=self._paneB_dmap)
        self._rangexy_stream.add_subscriber(self._on_paneB_range_changed)
        if self.paneB is not None:
            self.paneB.object = self._paneB_dmap

    def _send_paneB_fig(self, fig) -> None:
        if fig is None:
            return
        if not isinstance(fig, hv.Overlay):
            fig = hv.Overlay([fig])
        signature = self._paneB_fig_signature(fig)
        if (
            signature is not None
            and signature == self._paneB_structure
            and self._paneB_pipe is not None
        ):
            self._paneB_pipe.send(self._set_ranges_and_convert(fig))
        else:
            self._paneB_structure = signature
            self._rebuild_paneB_pipe(fig)

    @override
    def _update_paneB(self, fig) -> None:
        self._send_paneB_fig(fig)

    def _get_intensity_ylabel(self) -> str:
        """Return the paneB intensity label for the active normalization."""
        if self._current_norm and self._current_norm != 'none':
            return f'Normalized intensity ({self._current_norm})'
        return 'Intensity (a.u.)'

    def _cluster_color_for_label(self, label: int) -> str:
        """Return the colour assigned to a cluster label."""
        if not self._cmap_colors:
            return 'steelblue'
        idx = self._label_to_color_index(label)
        if idx is None:
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

    def _figB_cluster_hover(self, point, title_prefix: str = 'Hover'):
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
            alpha=0.2,
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
            title=f'{title_prefix}: pixel spectrum and cluster {label} centroid',
            legend_position='top_right',
            responsive=True,
            shared_axes=False,
            framewise=True,
            show_legend=True,
        )

    def _show_cluster_hover(self, point, title_prefix: str = 'Hover', allow_fast: bool = True) -> None:
        point_info = self._cluster_point_info(point)
        if point_info is None:
            return
        _, _, label = point_info
        if allow_fast and self._try_fast_cluster_hover_update(point, label):
            return

        fig = self._figB_cluster_hover(point, title_prefix=title_prefix)
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

    def _show_all_cluster_centers(self, defer: bool = False) -> None:
        """Show only centroids until the next double-click re-enables hover."""
        self._frozen_pixel = None
        self._hover_disabled = True
        self._clear_hover_queue()
        if self._cluster_centers:
            self._update_paneB_mean_spectra(
                title='All cluster centers (Double Click again to re-enable hover)',
                defer=defer,
            )

    def _enable_hover_mode(self, x=None, y=None) -> None:
        self._frozen_pixel = None
        self._hover_disabled = False
        self._hover_blocked = False
        self._clear_hover_queue()
        self._paneB_view_mode = 'centroids'
        self._last_hover_cluster_label = None

        if self._last_hover_point is not None:
            point = self._last_hover_point
        elif x is not None and y is not None:
            point = {"x": x, "y": y}
        else:
            point = {"x": 0, "y": 0}

        self._last_hover_point = point
        self._last_hover_pixel = None
        self._hover_last_event_pixel = None
        self._hover_last_event_xy = None
        if self._cluster_centers:
            self._show_cluster_hover(point, title_prefix='Hover', allow_fast=False)
        else:
            self._show_spectrum(point=point)

    # ------------------------------------------------------------------ #
    # HoloViews stream overrides                                           #
    # ------------------------------------------------------------------ #

    @override
    def _on_paneA_hover(self, x=None, y=None) -> None:
        """Queue hover updates when PointerXY is used instead of the JS gate."""
        if self._hover_disabled or self._frozen_pixel is not None or x is None or y is None:
            return
        self._queue_hover(x, y)

    @override
    def _handle_hover_render(self, point) -> None:
        self._last_hover_point = point
        if self._hover_blocked or self._hover_disabled:
            return
        if self._cluster_labels_2d is None or not self._cluster_centers:
            super()._handle_hover_render(point)
            return
        if self._frozen_pixel is not None:
            return
        current_pixel = (round(point["y"]), round(point["x"]))
        if current_pixel == self._last_rendered_pixel:
            return
        self._last_rendered_pixel = current_pixel
        self._show_cluster_hover(point)

    @override
    def _on_paneA_click(self, x=None, y=None) -> None:
        if x is None or y is None:
            return
        now = self._now_ms()
        if now < self._suppress_click_until_ms:
            return
        current_pixel = (round(y), round(x))
        self._last_hover_pixel = current_pixel
        if self._cluster_labels_2d is None or not self._cluster_centers:
            super()._on_paneA_click(x, y)
            return

        i, j = int(y), int(x)
        point = {"x": j, "y": i}
        point_info = self._cluster_point_info(point)
        if point_info is not None:
            _, _, label = point_info
            self._set_color_picker_from_label(label)
        self._frozen_pixel = (i, j)
        self._hover_blocked = True
        self._hover_pending_point = None
        self._last_hover_point = point
        self._last_rendered_pixel = (i, j)
        self._clear_hover_queue()
        self._show_cluster_hover(point, title_prefix='Click (Frozen)', allow_fast=False)

    @override
    def _on_paneA_double_tap(self, x=None, y=None) -> None:
        """Toggle between hover mode and all-cluster-centers display."""
        was_hover_disabled = self._hover_disabled
        super()._on_paneA_double_tap(x, y)
        self._frozen_pixel = None
        self._suppress_click_until_ms = self._now_ms() + 900
        self._clear_hover_queue()

        if self._cluster_labels_2d is None or not self._cluster_centers:
            return

        if was_hover_disabled:
            self._enable_hover_mode(x, y)
        else:
            self._show_all_cluster_centers(defer=True)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def cleanup(self) -> None:
        """Release HDBSCAN arrays and delegate to base cleanup."""
        self._cluster_labels_2d = None
        self._cluster_centers = {}
        self._cmap_colors = []
        self._cluster_label_order = []
        self._active_cluster_label = None
        self._current_norm = 'none'
        self._frozen_pixel = None
        self._hover_disabled = False
        self._paneB_view_mode = 'spectrum'
        self._last_hover_cluster_label = None
        self._last_rendered_pixel = None
        self._paneB_structure = None
        self._suppress_click_until_ms = 0
        if self._color_picker is not None and self._color_picker_watcher is not None:
            try:
                self._color_picker.param.unwatch(self._color_picker_watcher)
            except Exception:
                pass
        self._color_picker = None
        self._color_picker_watcher = None
        self._color_change_callback = None
        super().cleanup()
