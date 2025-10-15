"""
Spectrum image (datacube) visualization composer with KMeans clustering integration.
Integrates Vanessa's KMeans clustering functionality using Plotly for visualization.
"""

import panel as pn
import numpy as np
import plotly.graph_objs as go

from whateels.helpers import SpectrumExtractor

from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans
from whateels.base.base_visualizer import BaseVisualizer
from typing import override, TYPE_CHECKING, Literal
from whateels.components import ResizableColumns

if TYPE_CHECKING:
    from ...model import ClusteringModel
    from ...controller import ClusteringController
    from xarray import Dataset

class SpectrumImageVisualizer(BaseVisualizer):
    """
    Enhanced Spectrum Image Visualizer with integrated KMeans clustering.
    Combines the original visualizer functionality with Vanessa's clustering code.
    """
    
    # Panel sizing modes
    _STRETCH_WIDTH = "stretch_width"
    
    # CSS classes and constants for dataset info panel
    _DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
    _DATASET_INFO_CLASS = ["dataset-info", "animated"]
    _DATASET_INFO_TITLE = "<h5 class=\"dataset-info-title\">Dataset Information</h5>"
    
    _NOT_AVAILABLE = 'N/A'
    
    # Define a shared color palette for clusters (max 20 colors)
    _CLUSTER_COLORS = [
        "rgb(255, 0, 0)",      # red
        "rgb(0, 0, 255)",      # blue
        "rgb(0, 255, 0)",      # green
        "rgb(255, 165, 0)",    # orange
        "rgb(128, 0, 128)",    # purple
        "rgb(165, 42, 42)",    # brown
        "rgb(255, 192, 203)",  # pink
        "rgb(128, 128, 128)",  # gray
        "rgb(128, 128, 0)",    # olive
        "rgb(0, 255, 255)",    # cyan
        "rgb(255, 0, 255)",    # magenta
        "rgb(0, 255, 0)",      # lime
        "rgb(0, 0, 128)",      # navy
        "rgb(0, 128, 128)",    # teal
        "rgb(128, 0, 0)",      # maroon
        "rgb(255, 215, 0)",    # gold
        "rgb(75, 0, 130)",     # indigo
        "rgb(255, 127, 80)",   # coral
        "rgb(220, 20, 60)",    # crimson
        "rgb(238, 130, 238)"   # violet
    ]

    def __init__(self, model: "ClusteringModel", controller: "ClusteringController", dataset: "Dataset"):
        super().__init__(model, dataset)

        self._model = model
        self._dataset = dataset
        self._controller = controller

        # Energy axis (eje de energía)
        self._e_axis = self._dataset.coords[self._model.constants.ELOSS].values

        # ElectronCount data cube
        self._electron_count_data: "Dataset" = self._dataset.ElectronCount

        # Last selected pixel (x,y)
        self._last_selected = {"x": 0, "y": 0}

        # Range state for paneB (to preserve zoom/pan)
        self._current_x_range = None
        self._current_y_range = None
        self._current_x_autorange = None
        self._current_y_autorange = None

        # Selection / hover / state
        self._region_pairs = []
        self._last_hover_point = None
        self._last_hover_ts = None
        self._INACTIVITY_MS = 700

        # Clustering state (Vanessa's functionality)
        self._clustering_results = None  # Will store (labels, centres) from clustering
        self._original_heatmap_data = None  # Store original heatmap for restoration
        self._clustering_active = False

        # Widgets / panes placeholders
        self.clustering_button = None  # New clustering button
        self.restore_button = None     # Button to restore original view
        self.paneA = None  # Plotly heatmap pane
        self.paneB = None  # Plotly spectrum pane
        self._pc = None    # periodic callback handle
        self._kmeans_run_button = None  # KMeans run button

        # Setup widgets, plots and callbacks
        self._setup_widgets()
        self._setup_plots()
        self._setup_callbacks()

    # --- Vanessa's KMeans Clustering Implementation ---
    def _kmeans_clustering(self, matrix, n_cluster, available_norm, n_init=10, max_iter=300, init_method='k-means++'):
        '''
        Vanessa's KMeans clustering function adapted for the visualizer.
        
        Parameters:
        -----------
        matrix: numpy array. (x,y,eloss)
            Imagen de espectros.
        n_cluster: int.
            Número de clusters.
        available_norm: string, optional. (default='l2')
            Normalización que queremos aplicar. Opciones: 'l1', 'l2', 'max'.
        n_init: int, optional. (default=10)
            Number of times the k-means algorithm is run with different centroid seeds.
        max_iter: int, optional. (default=300)
            Maximum number of iterations of the k-means algorithm for a single run.
        init_method: string, optional. (default='k-means++')
            Method for initialization: 'k-means++', 'random', or an ndarray.
            
        Returns:
        --------
        labels: numpy array. (x,y)
            Matriz con las etiquetas de cada cluster. 
        centres: numpy array. (n_cluster,eloss)
            Matriz que contiene los centroides de cada cluster identificado.
        '''
        allowed_norms = self._model.constants.AVAILABLE_NORMS
        if available_norm not in allowed_norms:
            raise ValueError(f"norma debe ser uno de {allowed_norms}")

        matrix_norm = matrix.copy()
        matrix_norm = matrix_norm.reshape(matrix.shape[0]*matrix.shape[1], matrix.shape[-1])

        sclust_norm = normalize(matrix_norm, norm=available_norm, axis=1, copy=True)

        # Determine initialization method
        allowed_init_methods: tuple[Literal['k-means++'], Literal['random']] = ('k-means++', 'random')
        init_value: Literal['k-means++', 'random'] = init_method if init_method in allowed_init_methods else 'k-means++'

        kmeans = KMeans(
            n_clusters=n_cluster, 
            init=init_value,
            n_init=n_init,
            max_iter=max_iter,
            tol=1e-9, 
            random_state=13
        )
        fitted = kmeans.fit(sclust_norm)
        centres = fitted.cluster_centers_
        labels = fitted.labels_.reshape(matrix.shape[:-1])
        return labels, centres

    def _plot_kmeans_labels_plotly(self, labels, title="KMeans Clustering Labels"):
        """
        Plot the clustering labels using Plotly for interactive visualization.
        Adapted from Vanessa's code for integration into the visualizer.
        """
        n_clusters = len(np.unique(labels))
        # Create discrete colorscale by repeating each color at start and end of its range
        discrete_colorscale = []
        for i in range(n_clusters):
            color = self._CLUSTER_COLORS[i % len(self._CLUSTER_COLORS)]
            if i == 0:
                discrete_colorscale.append([0.0, color])
            else:
                prev_boundary = i / n_clusters
                discrete_colorscale.append([prev_boundary, discrete_colorscale[-1][1]])
                discrete_colorscale.append([prev_boundary, color])
            if i == n_clusters - 1:
                discrete_colorscale.append([1.0, color])
        
        fig = go.Figure(go.Heatmap(
            z=labels,
            colorscale=discrete_colorscale,
            colorbar=dict(title="Cluster", tickmode='linear', tick0=0, dtick=1),
            hovertemplate='x: %{x}<br>y: %{y}<br>Cluster: %{z}<extra></extra>',
            zmin=0,
            zmax=n_clusters-1
        ))
        # Keep same layout and aspect locking as the unclustered figA
        fig.update_layout(
            title=title,
            height=400,
            margin=dict(l=16, r=16, t=50, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_yaxes(autorange='reversed', scaleanchor='x', scaleratio=1, constrain='domain',
                         showgrid=False, zeroline=False, showticklabels=False)
        fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain='domain')
        return fig

    def _apply_kmeans_clustering(self, n_clusters=6, available_norm='l2', n_init=10, max_iter=300, init_method='k-means++'):
        """
        Apply KMeans clustering to the spectrum image data and update visualization.
        """

        try:
            # Get the 3D data cube (x, y, energy)
            data_cube = np.asarray(self._electron_count_data.fillna(0.0))
            
            # Store original heatmap data if not already stored
            if self._original_heatmap_data is None:
                self._original_heatmap_data = data_cube.sum(axis=-1)
            
            # Apply clustering with all parameters
            labels, centres = self._kmeans_clustering(
                data_cube, 
                n_clusters, 
                available_norm,
                n_init=n_init,
                max_iter=max_iter,
                init_method=init_method
            )
            
            self._clustering_results = (labels, centres)
            
            # Try to preserve the current paneB height so the clustering view
            # initially appears with the same vertical size as the current spectrum figure.
            current_b_height = None
            try:
                if self.paneB is not None and getattr(self.paneB, 'object', None) is not None:
                    obj = self.paneB.object
                    # obj can be a go.Figure or a dict (plotly json). Read layout.height if available.
                    if isinstance(obj, go.Figure):
                        current_b_height = obj.layout.height
                    elif isinstance(obj, dict):
                        current_b_height = obj.get('layout', {}).get('height')
                    if current_b_height is not None:
                        try:
                            current_b_height = int(current_b_height)
                        except Exception:
                            pass
            except Exception:
                current_b_height = None

            # Create clustering visualization
            clustering_fig = self._plot_kmeans_labels_plotly(labels, f"KMeans Clustering (n={n_clusters})")
            # If we were able to capture the current paneB height, apply it to the
            # clustering figure so it doesn't jump to a different vertical size.
            try:
                if current_b_height is not None:
                    clustering_fig.update_layout(height=current_b_height)
            except Exception:
                # best-effort only; do not fail clustering because of layout setting
                pass

            # Update the heatmap pane with clustering results (convert to plotly json)
            if self.paneA is not None:
                self.paneA.object = self._to_plotly(clustering_fig)
                self.paneA.param.trigger('object')  # Force parameter update
                # Alternative: recreate the pane entirely if needed
                # self.paneA = pn.pane.Plotly(self._to_plotly(clustering_fig), sizing_mode='stretch_both')
            
            # Update spectrum pane to show cluster centers
            self._update_spectrum_with_clusters(centres)
            
            self._clustering_active = True
            
        except Exception as e:
            print(f"DEBUG: Error applying clustering: {e}")
            import traceback
            traceback.print_exc()

    def _update_spectrum_with_clusters(self, centres):
        """Update the spectrum pane to show cluster centers."""
        if self.paneB is None:
            return
            
        # Create traces for each cluster center
        traces = []
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
        
        for i, center in enumerate(centres):
            color = colors[i % len(colors)]
            traces.append(go.Scatter(
                x=self._energy,
                y=center,
                mode='lines',
                name=f'Cluster {i}',
                line=dict(color=color, width=2)
            ))
        
        fig = go.Figure(data=traces)
        fig.update_layout(
            title="Cluster Centers",
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)",
            showlegend=True,
            legend=dict(
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.6)',
                bordercolor='rgba(0,0,0,0.1)',
                borderwidth=1,
            )
        )
        
        self.paneB.object = fig
        self.paneB.param.trigger('object')  # Force parameter update

    def _restore_original_view(self):
        """Restore the original heatmap view before clustering."""
        if self._original_heatmap_data is not None and self.paneA is not None:
            # Create original heatmap
            ny, nx = self._original_heatmap_data.shape
            heat = go.Heatmap(
                z=self._original_heatmap_data,
                x=np.arange(nx),
                y=np.arange(ny),
                colorscale="Greys_r",
                showscale=False,
                hovertemplate='x: %{x}<br>y: %{y}<br>Intensity: %{z}<extra></extra>'
            )
            
            fig = go.Figure(data=[heat])
            fig.update_layout(
                title="Original Spectrum Image",
                xaxis_title="X",
                yaxis_title="Y",
                yaxis_autorange='reversed'
            )
            
            self.paneA.object = fig
            self.paneA.param.trigger('object')  # Force parameter update
            self._clustering_active = False
            print("Restored original view")

    # --- Public layout builders (used by controller) ---
    @override
    def create_plots(self):
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both'
        )
        
        right_column = pn.Column(
            self.paneB, 
            self.clustering_button,
            self.restore_button,
            sizing_mode='stretch_both'
        )
        
        resizable_columns = ResizableColumns(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )
 
        return resizable_columns

    @override
    def create_dataset_info(self):
        return super().create_dataset_info()

    # --- Widget Setup ---
    def _setup_widgets(self):
       
        if kmeans_run_button := getattr(self._controller.view, "kmeans_run_button", None):
            self._kmeans_clustering_button = kmeans_run_button # Store reference
            kmeans_run_button.on_click(self._on_run_clustering_clicked)


    def _on_run_clustering_clicked(self, event):
        """Handle clustering button click."""
        
        if self._kmeans_clustering_button is not None:
            self._kmeans_clustering_button.disabled = True  # Disable to prevent multiple clicks
        
        kmeans_input = self._controller.view.kmeans_input
        
        n_clusters = self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS
        available_norm = self._model.constants.DEFAULT_SELECTED_NORM
        n_init = self._model.constants.DEFAULT_NUMBER_OF_INIT
        max_iter = self._model.constants.DEFAULT_MAX_ITER
        init_method = self._model.constants.DEFAULT_INIT_METHOD

        if kmeans_input is not None:
            n_clusters = kmeans_input["n_clusters"].value
            available_norm = kmeans_input["available_norms"].value
            n_init = kmeans_input["n_init"].value
            max_iter = kmeans_input["max_iter"].value
            init_method = kmeans_input["init_method"].value

        try:
            self._apply_kmeans_clustering(
                n_clusters=n_clusters, 
                available_norm=available_norm, 
                n_init=n_init, 
                max_iter=max_iter, 
                init_method=init_method
            )
        finally:
            if self._kmeans_clustering_button is not None:
                self._kmeans_clustering_button.disabled = False  # Re-enable button after processing
        

    def _on_stop_clustering_clicked(self):
        """Handle restore button click."""
        self._restore_original_view()

    # --- Plot / Pane Setup (Plotly) ---
    def _setup_plots(self):
        # Build image (m_image) from data cube
        m_image_da = self._electron_count_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Se esperaba imagen 2D integrada, recibido shape={m_image.shape}")

        ny, nx = m_image.shape
        # Store original data
        self._original_heatmap_data = m_image
        
        # energy axis
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # Build Plotly heatmap (figA) and selectors to enable lasso/box selection
        heat = go.Heatmap(
            z=m_image,
            x=np.arange(nx),
            y=np.arange(ny),
            colorscale="Greys_r",
            showscale=False,
            name="m_image",
            hovertemplate="i=%{y}, j=%{x}<br>I=%{z}<extra></extra>",
        )

        # Create an invisible selectors layer (Scattergl) so Plotly emits selected/hover points
        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        selectors = go.Scattergl(
            x=XX.ravel(),
            y=YY.ravel(),
            mode="markers",
            name="selectors",
            marker=dict(size=6, opacity=0.01),
            hoverinfo="skip",
            selected=dict(marker=dict(opacity=0.3, size=8)),
            unselected=dict(marker=dict(opacity=0.01)),
        )

        figA = go.Figure(data=[heat, selectors])
        figA.update_layout(
            title=" ",
            height=400,
            margin=dict(l=16, r=16, t=50, b=20),
            dragmode="lasso",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        # Keep origin top-left and preserve 1:1 pixel aspect to avoid deformation
        figA.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1, constrain="domain",
                           showgrid=False, zeroline=False, showticklabels=False)
        figA.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain")

        # Initial spectrum (center pixel)
        center_x, center_y = nx // 2, ny // 2
        initial_spectrum = self._electron_count_data.isel(x=center_x, y=center_y)
        spectrum_data = np.asarray(initial_spectrum.fillna(0.0))

        trace = go.Scatter(
            x=energy,
            y=spectrum_data,
            mode='lines',
            name='Spectrum',
        )

        figB = go.Figure(data=[trace])
        figB.update_layout(
            title="Spectrum at Selected Pixel",
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)",
            legend=dict(
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.6)',
                bordercolor='rgba(0,0,0,0.1)',
                borderwidth=1,
            )
        )

        # Create Panel panes (use _to_plotly to avoid Panel<->Plotly relayout issues)
        self.paneA = pn.pane.Plotly(self._to_plotly(figA), config={"responsive": True}, sizing_mode='stretch_both')
        # Pane B initial message: use the center-spectrum figure but keep responsive config
        self.paneB = pn.pane.Plotly(self._to_plotly(figB), config={"responsive": True}, sizing_mode='stretch_both')

    def _setup_callbacks(self):
        """Setup callbacks for interactive functionality."""
        if self.paneA is not None:
            # Watch click, hover and selection so lasso/box selection works
            self.paneA.param.watch(self._on_paneA_click, "click_data")
            self.paneA.param.watch(self._on_paneA_hover, "hover_data")
            self.paneA.param.watch(self._on_paneA_selected, "selected_data")

    def _to_plotly(self, obj):
        """Convert go.Figure to dict to avoid Panel<->Plotly relayout issues."""
        try:
            if isinstance(obj, go.Figure):
                return obj.to_plotly_json()
        except Exception:
            pass
        try:
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        return obj

    def _on_paneA_click(self, event):
        """Handle clicks on the heatmap to update spectrum."""
        if event.new is None:
            return
            
        try:
            point = event.new['points'][0]
            x, y = int(point['x']), int(point['y'])
            
            # Update spectrum for selected pixel
            spectrum = self._electron_count_data.isel(x=x, y=y)
            spectrum_data = np.asarray(spectrum.fillna(0.0))
            
            trace = go.Scatter(
                x=self._energy,
                y=spectrum_data,
                mode='lines',
                name=f'Spectrum at ({x},{y})',
                line=dict(color='red', width=2)
            )
            
            fig = go.Figure(data=[trace])
            fig.update_layout(
                title=f"Spectrum at Pixel ({x}, {y})",
                xaxis_title="Energy Loss (eV)",
                yaxis_title="Intensity (AU)"
            )
            
            if hasattr(self, 'paneB') and self.paneB is not None:
                self.paneB.object = fig
            
        except Exception as e:
            print(f"Error updating spectrum: {e}")

    def _on_range_changed(self, event):
        """Handle range slider changes."""
        pass  # Placeholder for range functionality

    def _on_paneA_hover(self, event):
        """Handle hover on the heatmap to show single-pixel spectrum."""
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        # If a region is selected, don't override the region spectrum
        if self._region_pairs:
            return
        i, j = int(point['y']), int(point['x'])
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        if spec is None:
            return
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode='lines', name=f"(i={i}, j={j})"))
        fig.update_layout(
            title="Hover",
            margin=dict(l=16, r=16, t=48, b=16),
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)"
        )
        if self.paneB is not None:
            self.paneB.object = fig

    def _on_paneA_selected(self, event):
        """Handle lasso/box selection and show summed spectrum for selected pixels."""
        pairs = SpectrumExtractor.extract_region(event)
        self._region_pairs = pairs
        if not pairs:
            # no selection: show hover or default
            if self._last_hover_point is not None:
                i, j = int(self._last_hover_point['y']), int(self._last_hover_point['x'])
                spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
                if spec is not None:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=self._energy, y=spec, mode='lines', name=f"(i={i}, j={j})"))
                    fig.update_layout(title="Hover", xaxis_title="Energy Loss (eV)", yaxis_title="Intensity (AU)",
                                      legend=dict(x=0.98, y=0.98, xanchor='right', yanchor='top', bgcolor='rgba(255,255,255,0.6)', bordercolor='rgba(0,0,0,0.1)', borderwidth=1))
                    if self.paneB is not None:
                        self.paneB.object = fig
            return

        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)
        if res is None:
            return
        spec, n_points = res
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode='lines', name=f"sum (points={n_points})"))
        fig.update_layout(
            title=f"ROI — sum (points={n_points})",
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)",
            legend=dict(
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.6)',
                bordercolor='rgba(0,0,0,0.1)',
                borderwidth=1,
            )
        )
        if self.paneB is not None:
            self.paneB.object = fig