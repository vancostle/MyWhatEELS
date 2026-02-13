
import copy, numpy as np, umap, hdbscan
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

from typing import TYPE_CHECKING, Optional, Any
if TYPE_CHECKING:
    from xarray import DataArray
    
class UMAP_HDBSCAN:
    
    def __init__(self, electron_count_data : "DataArray"):
        
        self._saved_electron_count_data = copy.deepcopy(electron_count_data) # Keep a copy of original data for resetting if needed
        self._electron_count_data = copy.deepcopy(electron_count_data) # Deep copy to avoid modifying original data
        self._eloss = self._electron_count_data.coords["Eloss"].values
        self._data = np.array(self._electron_count_data)

    def cut_signal(self, min_eloss, max_eloss) -> bool:
        """Cuts the signal range based on min and max eloss values."""
        
        self._electron_count_data = self._saved_electron_count_data.copy() # Reset to original data before cutting
        
        try:
            self._electron_count_data = self._electron_count_data.sel(Eloss=slice(min_eloss, max_eloss)) # Overwrite data with cut signal range
            self._eloss = self._electron_count_data.coords["Eloss"].values # Update eloss values accordingly
            self._data = np.array(self._electron_count_data) # Update data array with cut signal range
            return True
        except Exception:
            return False
        
    def get_original_eloss_range(self) -> tuple[float, float]:
        """Get the minimum and maximum eloss values from the electron count data before any cutting is applied."""
        try:
            eloss_values = self._saved_electron_count_data.coords["Eloss"].values
            return float(eloss_values.min()), float(eloss_values.max())
        except Exception:
            return 0.0, 0.0
        
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
        """Reshape electron count data to 2D array for UMAP processing."""
        try:
            shape = self._electron_count_data.shape
            if len(shape) == 2:
                return np.array(self._electron_count_data)
            elif len(shape) == 3:
                n_y, n_x, n_eloss = shape
                return np.array(self._electron_count_data).reshape(n_y * n_x, n_eloss)
            else:
                raise ValueError("Electron count data must be 2D or 3D.")
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
    
    def plot_hdbscan_map(self, hdbscan_results, cmap_obj) -> go.Figure:
        """
        Create and return a Plotly figure displaying the HDBSCAN clustering map.
        
        Args:
            hdbscan_results: HDBSCAN results object with labels_ attribute
            cmap_obj: dict with 'colors' key containing list of hex colors
            
        Returns:
            Plotly figure object
        """
        # Reshape labels to 2D clustering array using electron count data shape
        shape = self._electron_count_data.shape
        clustering = hdbscan_results.labels_.reshape(shape[0], shape[1])
        
        color_list = cmap_obj["colors"]
        n_colors = len(color_list)
        
        # Create a discrete color scale for Plotly
        color_scale = []
        for i, color in enumerate(color_list):
            frac = i / max(n_colors - 1, 1)
            color_scale.append([frac, color])
        
        # Create the figure
        fig = px.imshow(
            clustering,
            color_continuous_scale=color_scale,
            aspect="equal",
            origin="upper",
            title="HDBSCAN Map"
        )
        
        # Update layout
        fig.update_layout(
            coloraxis_colorbar=dict(title="Cluster"),
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            margin=dict(l=0, r=0, t=30, b=0),
            title=dict(text="HDBSCAN Map", x=0.5, xanchor='center', y=0.98, yanchor='top', font=dict(size=14)),
        )
        
        return fig
    
    def plot_mean_spectra_per_cluster(self, hdbscan_results, cmap_obj) -> go.Figure:
        """
        Create and return a Plotly figure displaying mean spectra for each cluster.
        
        Args:
            hdbscan_results: HDBSCAN results object with labels_ attribute
            cmap_obj: dict with 'colors' key containing list of hex colors
            
        Returns:
            Plotly figure object
        """
        # Reshape labels to clustering array
        shape = self._electron_count_data.shape
        clustering = hdbscan_results.labels_.reshape(shape[0], shape[1])
        
        energy_axis = self._eloss
        flat_clustering = clustering.reshape(-1)
        flat_spectra = self._data.reshape(-1, energy_axis.size)
        unique_labels = np.unique(flat_clustering)
                
        # Create figure
        fig = go.Figure()
        
        for idx, label in enumerate(unique_labels):
            cluster_mask = (flat_clustering == label)
            spectra_cluster = flat_spectra[cluster_mask]
            mean_spectrum = np.mean(spectra_cluster, axis=0)
            
            # Get color for this cluster
            color = cmap_obj["colors"][idx]
            
            # Add trace for this cluster
            fig.add_trace(go.Scatter(
                x=energy_axis,
                y=mean_spectrum,
                mode='lines',
                name=f'Label {label}',
                line=dict(color=color)
            ))
        
        # Update layout
        fig.update_layout(
            title=dict(text='Centroids of HDBSCAN on the UMAP embedding', x=0.5, xanchor='center', y=0.98, yanchor='top', font=dict(size=14)),
            xaxis_title='Energy Loss (eV)',
            yaxis_title='Intensity (counts)',
            plot_bgcolor='black',
            paper_bgcolor='black',
            font=dict(color='white'),
            showlegend=True,
            legend=dict(orientation='v', x=1.02, y=1),
            margin=dict(l=50, r=100, t=40, b=40)
        )
        
        # Update axes styling
        fig.update_xaxes(showgrid=True, gridcolor='gray')
        fig.update_yaxes(showgrid=True, gridcolor='gray')
        
        return fig

    def plot_umap_embedding_with_labels(self, embedding, labels, cmap_obj, min_samp, min_clust) -> go.Figure:
        """
        Create and return a Plotly figure displaying the UMAP embedding colored by cluster labels.
        
        Args:
            embedding: UMAP embedding array with shape (n_points, 2)
            labels: Cluster labels array with shape (n_points,)
            cmap_obj: dict with 'colors' key containing list of hex colors
            min_samp: min_samples parameter used in HDBSCAN
            min_clust: min_cluster_size parameter used in HDBSCAN
            
        Returns:
            Plotly figure object
        """
        # Extract x and y coordinates from embedding
        x = embedding[:, 0]
        y = embedding[:, 1]
        
        # Get unique labels and create color mapping
        unique_labels = np.unique(labels)
        color_list = cmap_obj["colors"]
        
        # Create figure
        fig = go.Figure()
        
        # Add scatter trace for each cluster
        for idx, label in enumerate(unique_labels):
            mask = (labels == label)
            color = color_list[idx] if idx < len(color_list) else color_list[-1]
            
            fig.add_trace(go.Scatter(
                x=x[mask],
                y=y[mask],
                mode='markers',
                name=f'Cluster {label}' if label != -1 else 'Cluster -1 (outliers)',
                marker=dict(
                    color=color,
                    size=4,
                    opacity=0.6,
                    line=dict(width=0, color=color)
                ),
                showlegend=True
            ))
        
        # Update layout to match original styling
        fig.update_layout(
            title=dict(
                text=f'UMAP embedding min_samples={min_samp}, min_cluster_size={min_clust}',
                x=0.5,
                xanchor='center',
                y=0.98,
                yanchor='top',
                font=dict(size=14)
            ),
            width=650,
            height=300,
            plot_bgcolor='black',
            paper_bgcolor='black',
            font=dict(color='white'),
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
            showlegend=True,
            legend=dict(orientation='v', x=1.02, y=1),
            margin=dict(l=0, r=100, t=40, b=0)
        )
        
        return fig