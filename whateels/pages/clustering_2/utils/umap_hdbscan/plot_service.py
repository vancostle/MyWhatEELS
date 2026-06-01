import numpy as np

import holoviews as hv
import xarray as xr
import panel as pn


class PlotService:
    """Encapsulates UMAP/HDBSCAN plotting logic."""

    def __init__(self, electron_count_data, eloss, data):
        self._electron_count_data = electron_count_data
        self._eloss = eloss
        self._data = data

    def plot_hdbscan_map(self, hdbscan_results, cmap_obj):
        """Create and return a Holoviews Image displaying the HDBSCAN clustering map."""
        shape = self._electron_count_data.shape
        clustering = hdbscan_results.labels_.reshape(shape[0], shape[1])

        img = hv.Image(
            xr.Dataset(
                {'Labels': (['y', 'x'], clustering)},
                coords={'x': np.arange(shape[1]), 'y': np.arange(shape[0])}
            ),
            kdims=['x', 'y']
        )

        def _integer_colorbar_hook(plot, element):
            fig = getattr(plot, 'state', None)
            if fig is None:
                return
            try:
                from bokeh.models import FixedTicker, NumeralTickFormatter
                min_label = int(np.nanmin(clustering))
                max_label = int(np.nanmax(clustering))
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

        img = img.opts(
            xaxis=None, yaxis=None, colorbar=True, tools=['hover'], toolbar='right',
            invert_yaxis=True, responsive=True, cmap=cmap_obj["colors"],
            title='HDBSCAN map', hooks=[_integer_colorbar_hook]
        )
        return pn.pane.HoloViews(img, margin=0, styles={'margin': 'auto'})

    def plot_mean_spectra_per_cluster(self, hdbscan_results, cmap_obj):
        """Create and return a Holoviews NdOverlay displaying mean spectra for each cluster."""
        shape = self._electron_count_data.shape
        clustering = hdbscan_results.labels_.reshape(shape[0], shape[1])

        energy_axis = self._eloss
        flat_clustering = clustering.reshape(-1)
        flat_spectra = self._data.reshape(-1, energy_axis.size)
        unique_labels = np.unique(flat_clustering)

        print('Shapes: flat_clustering', flat_clustering.shape, 'flat_spectra', flat_spectra.shape)

        mean_spectra_overlay = {}
        for idx, label in enumerate(unique_labels):
            cluster_mask = (flat_clustering == label)
            spectra_cluster = flat_spectra[cluster_mask]
            mean_spectrum = np.mean(spectra_cluster, axis=0)

            color = cmap_obj["colors"][idx]

            curve = hv.Curve(
                (energy_axis, mean_spectrum),
                'Eloss',
                f'Intensity (Label {label})'
            ).opts(color=color)
            mean_spectra_overlay[f'Label_{label}'] = curve

        overlay = hv.NdOverlay(mean_spectra_overlay).opts(
            legend_position='top_right',
            ylabel='Intensity (counts)',
            xlabel='Energy Loss (eV)',
            title='Centroids of HDBSCAN on the UMAP embedding',
            tools=['lasso_select', 'box_select'],
            responsive=True,
        )

        return pn.pane.HoloViews(overlay, sizing_mode='stretch_both', margin=0)

    def plot_umap_embedding_with_labels(self, embedding, labels, cmap_obj, min_samp, min_clust):
        """Create and return a Holoviews Points plot displaying the UMAP embedding colored by cluster labels."""
        zers = np.zeros((embedding.shape[0], 3))
        zers[:, :-1] = embedding
        zers[:, -1] = labels
        points = hv.Points(zers, vdims=['color']).opts(
            toolbar='right',
            fill_alpha=0.6,
            bgcolor='black',
            line_alpha=0,
            line_width=0.15,
            size=2.5,
            xaxis=None,
            yaxis=None,
            cmap=cmap_obj["colors"],
            show_legend=True,
            color='color',
            shared_axes=False,
            title=f'UMAP embedding min_samples={min_samp}, min_cluster_size={min_clust}',
            tools=['lasso_select', 'box_select'],
            responsive=True,
            frame_height=400,
        )
        return points

    def plot_cluster_heatmap(self, data, cmap='rainbow'):
        """Create a heatmap visualization of clustering results for different parameter combinations."""
        heatmap_data = []
        for d in data:
            min_samples = d[0]
            min_cluster_size = d[1]
            num_clusters = d[2]
            heatmap_data.append((min_cluster_size, min_samples, num_clusters))

        heatmap = hv.HeatMap(heatmap_data, kdims=['min_cluster_size', 'min_samples'], vdims=['num_clusters'])

        labels_data = [(d[1], d[0], str(int(d[2]))) for d in data]
        labels = hv.Labels(labels_data, kdims=['min_cluster_size', 'min_samples'], vdims=['text'])

        def _integer_axis_ticks_hook(plot, element):
            fig = getattr(plot, 'state', None)
            if fig is None:
                return
            try:
                from bokeh.models import FixedTicker, NumeralTickFormatter

                min_samples_ticks = sorted({int(d[0]) for d in data})
                if min_samples_ticks and getattr(fig, 'yaxis', None):
                    axis = fig.yaxis[0]
                    axis.ticker = FixedTicker(ticks=min_samples_ticks)
                    axis.formatter = NumeralTickFormatter(format='0')
            except Exception:
                return

        overlay = (heatmap * labels).opts(
            hv.opts.HeatMap(
                cmap=cmap,
                colorbar=True,
                toolbar='right',
                xlabel='min_cluster_size',
                ylabel='min_samples',
                title='Number of Clusters by Parameters',
                height=400,
                tools=['hover'],
                clabel='Number of Clusters',
                responsive=True,
                hooks=[_integer_axis_ticks_hook],
            ),
            hv.opts.Labels(
                text_color='black',
                text_font_size='9pt',
                text_align='center',
                text_baseline='middle'
            )
        )

        return overlay