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

        super().__init__(dataset, eloss_name, paneA_select_tools=['hover'])

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def update_hdbscan_results(self, hdbscan_results, cmap_obj: dict) -> None:
        """
        Swap paneA to the HDBSCAN cluster label map and paneB to mean spectra.

        Args:
            hdbscan_results: Fitted HDBSCAN object with a ``labels_`` attribute.
            cmap_obj:        Dict with a ``'colors'`` key — list of hex colours,
                             one per unique label (including noise label −1 if present).
        """
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

        self._update_paneA_cluster_map(labels_2d, nx, ny)
        self._update_paneB_mean_spectra()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _update_paneA_cluster_map(self, labels_2d: np.ndarray, nx: int, ny: int) -> None:
        """Replace paneA content with an HDBSCAN cluster-label heatmap."""
        cmap = self._cmap_colors if self._cmap_colors else 'Category20'
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
            title='HDBSCAN cluster map',
        )
        self._paneA_base_overlay = img * self._selectors  # type: ignore[operator]
        self._update_selection_overlay([])

    def _update_paneB_mean_spectra(self) -> None:
        """Push mean-spectra-per-cluster through the paneB pipe."""
        if not self._cluster_centers or self._paneB_pipe is None:
            return

        curves_dict: dict = {}
        for idx, (label, center) in enumerate(self._cluster_centers.items()):
            color = (
                self._cmap_colors[idx % len(self._cmap_colors)]
                if self._cmap_colors
                else 'steelblue'
            )
            curves_dict[f'Cluster {label}'] = hv.Curve(
                (self._energy, center),
                kdims=['x'],
                vdims=['y'],
            ).opts(
                color=color,
                line_width=2,
                responsive=True,
                shared_axes=False,
                framewise=True,
            )

        overlay = hv.NdOverlay(curves_dict).opts(
            xlabel='Energy Loss (eV)',
            ylabel='Intensity (a.u.)',
            title='Centroids of HDBSCAN on the UMAP embedding',
            legend_position='top_right',
            responsive=True,
            shared_axes=False,
            framewise=True,
        )
        # Send directly to the pipe — bypassing _update_paneB's hv.Overlay wrapping,
        # which would hide the NdOverlay's 'Element' dimension label (legend group title).
        # Also reset ranges so the view autoscales on the new data.
        self._current_x_range = None
        self._current_y_range = None
        self._paneB_pipe.send(overlay)

    # ------------------------------------------------------------------ #
    # HoloViews stream overrides                                           #
    # ------------------------------------------------------------------ #

    @override
    def _on_paneA_hover(self, x=None, y=None) -> None:
        """No-op — paneB stays static (mean spectra). No hover-driven updates."""
        pass

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def cleanup(self) -> None:
        """Release HDBSCAN arrays and delegate to base cleanup."""
        self._cluster_labels_2d = None
        self._cluster_centers = {}
        self._cmap_colors = []
        super().cleanup()
