
import copy, numpy as np, umap, hdbscan
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import holoviews as hv
import xarray as xr
import panel as pn

from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from xarray import DataArray
    
class UMAP_HDBSCAN:
    
    def __init__(self, electron_count_data : "DataArray"):

        self._electron_count_data = copy.deepcopy(electron_count_data) # Deep copy to avoid modifying original data
        self._eloss = self._electron_count_data.coords["Eloss"].values
        self._data = np.array(self._electron_count_data)
        
    def compute_umap_embedding(
        self,
        min_dist : float = 0.1,
        n_neighbors : int = 15,
        n_components : int = 2,
        metric : str = 'euclidean',
        random_state : int = 1
        
    ) -> tuple[Any, dict]:
        """ Compute UMAP embedding of the image spectra image. """
        data_2d = self._get_reshaped_data()
        
        mapper = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            n_components=n_components,
            random_state=random_state,
            metric=metric
        )
        embedding = mapper.fit_transform(data_2d)
        
        umap_data_dict = dict()
        umap_data_dict['umap_data_{}_{}'.format(min_dist, n_neighbors)] = mapper
        
        return embedding, umap_data_dict

    def _get_reshaped_data(self) -> Optional[np.ndarray]:
        """Reshape electron count data to 2D array for UMAP processing.

        NaN and Inf values are replaced with 0 so sklearn/UMAP never sees
        non-finite inputs (e.g. from Cut Range preprocessing on the home page).
        """
        try:
            shape = self._electron_count_data.shape
            if len(shape) == 2:
                arr = np.array(self._electron_count_data, dtype=float)
            elif len(shape) == 3:
                n_y, n_x, n_eloss = shape
                arr = np.array(self._electron_count_data, dtype=float).reshape(n_y * n_x, n_eloss)
            else:
                raise ValueError("Electron count data must be 2D or 3D.")
            # Replace NaN/Inf so UMAP/sklearn never sees non-finite values.
            if not np.all(np.isfinite(arr)):
                arr = np.where(np.isfinite(arr), arr, 0.0)
            return arr
        except Exception as e:
            print(f"Error processing electron count data: {e}")
            return None
        
        
    def compute_hdbscan_on_umap(self, umap_embedding, min_samples, min_cluster_size):
        """Compute HDBSCAN clustering on the provided UMAP embedding."""
        
        hdbscan_results = hdbscan.HDBSCAN(
            min_samples=min_samples,
            min_cluster_size=min_cluster_size
        ).fit(umap_embedding)
        
        return hdbscan_results  

    def get_nclusters_cmap(self, hdbscan_results, n_clusters, cmap='tab20b'):
        """
        Create a colormap with n_clusters colors based on a colormap with 20 colors, such as 'tab20b'.
        Returns a dict con .colors en formato hexadecimal para Bokeh/Holoviews.
        """
        original_cmap = plt.cm.get_cmap(cmap)
        hex_colors = []
        # Obtener las labels presentes en el clustering actual
        labels = getattr(hdbscan_results, 'labels_', None)
        if labels is not None and -1 in np.unique(labels):
            # Si hay outlier, el primer color es lightgray
            hex_colors.append('lightgray')
            n_valid = n_clusters - 1
        else:
            n_valid = n_clusters
        if n_valid > 0:
            indices = np.linspace(0, 19, n_valid, dtype=int)
            colors = [original_cmap(i) for i in indices]
            hex_colors.extend([mcolors.to_hex(c) for c in colors])

        return {"colors": hex_colors}
    
    def evaluate_umap(self, embedding) -> list[tuple[int, int, int, int, float]]:
        """ Evaluate UMAP embedding with HDBSCAN for a range of min_samples and min_cluster_size parameters, returning a list of results. """
        MIN_SAMPLE_START = 1
        MIN_SAMPLE_END = 8  
        MIN_CLUSTER_START = 100
        MIN_CLUSTER_END = 900
        MIN_CLUSTER_STEP = 100     

        data = []

        for i in range(MIN_SAMPLE_START, MIN_SAMPLE_END):
            for j in range(MIN_CLUSTER_START, MIN_CLUSTER_END + 1, MIN_CLUSTER_STEP):
                hdbscan_results = hdbscan.HDBSCAN(min_cluster_size=j, min_samples=i)
                hdbscan_results.fit(embedding)
                outliers = np.count_nonzero(hdbscan_results.labels_ == -1)
                total_points = hdbscan_results.labels_.size
                data.append((i, j, len(np.unique(hdbscan_results.labels_)), outliers, (outliers/total_points)*100))

        return data

    def plot_hdbscan_map(self, hdbscan_results, cmap_obj):
        """
        Create and return a Holoviews Image displaying the HDBSCAN clustering map.
        
        Args:
            hdbscan_results: HDBSCAN results object with labels_ attribute
            cmap_obj: dict with 'colors' key containing list of hex colors
            
        Returns:
            Holoviews Image object
        """
        # Reshape labels to 2D clustering array using electron count data shape
        shape = self._electron_count_data.shape
        clustering = hdbscan_results.labels_.reshape(shape[0], shape[1])
        
        # Create Holoviews Image
        img = hv.Image(
            xr.Dataset(
                {'Labels': (['y', 'x'], clustering)},
                coords={'x': np.arange(shape[1]),
                        'y': np.arange(shape[0])}
            ),
            kdims=['x', 'y']
        ).opts(
            xaxis=None, yaxis=None, colorbar=True, tools=['hover'], toolbar='right',
            invert_yaxis=True, responsive=True, cmap=cmap_obj["colors"],
            title='HDBSCAN map'
        )
        
        return pn.pane.HoloViews(img, margin=0, styles={'margin': 'auto'})
    
    def plot_mean_spectra_per_cluster(self, hdbscan_results, cmap_obj):
        """
        Create and return a Holoviews NdOverlay displaying mean spectra for each cluster.
        
        Args:
            hdbscan_results: HDBSCAN results object with labels_ attribute
            cmap_obj: dict with 'colors' key containing list of hex colors
            
        Returns:
            Holoviews NdOverlay object
        """
        # Reshape labels to clustering array
        shape = self._electron_count_data.shape
        clustering = hdbscan_results.labels_.reshape(shape[0], shape[1])
        
        energy_axis = self._eloss
        flat_clustering = clustering.reshape(-1)
        flat_spectra = self._data.reshape(-1, energy_axis.size)
        unique_labels = np.unique(flat_clustering)
        
        print('Shapes: flat_clustering', flat_clustering.shape, 'flat_spectra', flat_spectra.shape)
        
        # Create curves for each cluster
        mean_spectra_overlay = {}
        for idx, label in enumerate(unique_labels):
            cluster_mask = (flat_clustering == label)
            spectra_cluster = flat_spectra[cluster_mask]
            mean_spectrum = np.mean(spectra_cluster, axis=0)
            
            # Get color for this cluster
            color = cmap_obj["colors"][idx]
            
            # Create curve
            curve = hv.Curve(
                (energy_axis, mean_spectrum),
                'Eloss',
                f'Intensity (Label {label})'
            ).opts(color=color)
            mean_spectra_overlay[f'Label_{label}'] = curve
        
        # Create NdOverlay
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
        """
        Create and return a Holoviews Points plot displaying the UMAP embedding colored by cluster labels.
        
        Args:
            embedding: UMAP embedding array with shape (n_points, 2)
            labels: Cluster labels array with shape (n_points,)
            cmap_obj: dict with 'colors' key containing list of hex colors
            min_samp: min_samples parameter used in HDBSCAN
            min_clust: min_cluster_size parameter used in HDBSCAN
            
        Returns:
            Holoviews Points object
        """
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
        """
        Create a heatmap visualization of clustering results for different parameter combinations.
        
        Parameters:
        -----------
        data : list of tuples
            Each tuple should contain (min_samples, min_cluster_size, num_clusters, num_outliers, outlier_percentage)
        cmap : str, optional
            Colormap name for the heatmap. Default is 'rainbow'
            
        Returns:
        --------
        hv.HeatMap : Holoviews HeatMap object
            The created heatmap with labeled text annotations
        """
        # Build data list for HeatMap: (x, y, value) format
        # Holoviews automatically handles unique values and positioning
        heatmap_data = []
        for d in data:
            min_samples = d[0]
            min_cluster_size = d[1]
            num_clusters = d[2]
            heatmap_data.append((min_cluster_size, min_samples, num_clusters))

        # Create HeatMap
        heatmap = hv.HeatMap(heatmap_data, kdims=['min_cluster_size', 'min_samples'], vdims=['num_clusters'])
        
        # Add text labels overlay
        labels_data = [(d[1], d[0], str(int(d[2]))) for d in data]
        labels = hv.Labels(labels_data, kdims=['min_cluster_size', 'min_samples'], vdims=['text'])
        
        # Combine heatmap with labels
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
            ),
            hv.opts.Labels(
                text_color='black',
                text_font_size='9pt',
                text_align='center',
                text_baseline='middle'
            )
        )
        
        return overlay