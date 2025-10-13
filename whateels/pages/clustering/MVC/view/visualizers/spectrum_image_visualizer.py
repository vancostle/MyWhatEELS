"""
Spectrum image (datacube) visualization composer with KMeans clustering integration.
Integrates Vanessa's KMeans clustering functionality using Plotly for visualization.
"""

import panel as pn
import numpy as np
import plotly.graph_objs as go
from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans

from whateels.base.base_visualizer import BaseVisualizer
from typing import override, TYPE_CHECKING
from whateels.components import ResizableColumns, ToggleButton

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

        # Selection / hover / fitting state
        self._region_pairs = []
        self._last_hover_point = None
        self._last_hover_ts = None
        self._INACTIVITY_MS = 700
        self._fitting_active = False

        # Clustering state (Vanessa's functionality)
        self._clustering_results = None  # Will store (labels, centres) from clustering
        self._original_heatmap_data = None  # Store original heatmap for restoration
        self._clustering_active = False

        # Widgets / panes placeholders
        self.range_slider = None
        self.fitting_button = None
        self.clustering_button = None  # New clustering button
        self.restore_button = None     # Button to restore original view
        self.paneA = None  # Plotly heatmap pane
        self.paneB = None  # Plotly spectrum pane
        self._pc = None    # periodic callback handle

        # Setup widgets, plots and callbacks
        self._setup_widgets()
        self._setup_plots()
        self._setup_callbacks()

    # --- Vanessa's KMeans Clustering Implementation ---
    def kmeans_clustering(self, matrix, n_cluster, norma='l2'):
        '''
        Vanessa's KMeans clustering function adapted for the visualizer.
        
        Parameters:
        -----------
        matrix: numpy array. (x,y,eloss)
            Imagen de espectros.
        n_cluster: int.
            Número de clusters.
        norma: string, optional. (default='l2')
            Normalización que queremos aplicar. Opciones: 'l1', 'l2', 'max', 'None'.
            
        Returns:
        --------
        labels: numpy array. (x,y)
            Matriz con las etiquetas de cada cluster. 
        centres: numpy array. (n_cluster,eloss)
            Matriz que contiene los centroides de cada cluster identificado.
        '''
        allowed_norms = ['l1', 'l2', 'max', None, 'None']
        if norma not in allowed_norms:
            raise ValueError(f"norma debe ser uno de {allowed_norms}")
        
        # Convert string 'None' to actual None
        if norma == 'None' or norma is None:
            norm_to_use = None
        else:
            # Ensure norma is exactly one of the allowed literals
            if norma not in ('l1', 'l2', 'max'):
                raise ValueError("norma must be 'l1', 'l2', 'max', or None")
            norm_to_use = norma

        matrix_norm = matrix.copy()
        matrix_norm = matrix_norm.reshape(matrix.shape[0]*matrix.shape[1], matrix.shape[-1])
        if norm_to_use is None:
            sclust_norm = matrix_norm
        else:
            sclust_norm = normalize(matrix_norm, norm=norm_to_use, axis=1, copy=True)
        
        kmeans = KMeans(n_clusters=n_cluster, tol=1e-9, max_iter=700, random_state=13)
        fitted = kmeans.fit(sclust_norm)
        centres = fitted.cluster_centers_
        labels = fitted.labels_.reshape(matrix.shape[:-1])
        return labels, centres

    def plot_kmeans_labels_plotly(self, labels, title="KMeans Clustering Labels", colorscale="Viridis"):
        """
        Plot the clustering labels using Plotly for interactive visualization.
        Adapted from Vanessa's code for integration into the visualizer.
        """
        fig = go.Figure(go.Heatmap(
            z=labels, 
            colorscale=colorscale, 
            colorbar=dict(title="Cluster"),
            hovertemplate='x: %{x}<br>y: %{y}<br>Cluster: %{z}<extra></extra>'
        ))
        fig.update_layout(
            title=title, 
            xaxis_title="X", 
            yaxis_title="Y", 
            yaxis_autorange='reversed'
        )
        return fig

    def apply_clustering_kmeans(self, n_clusters=6, norma='l2'):
        """
        Apply KMeans clustering to the spectrum image data and update visualization.
        """
        try:
            # Get the 3D data cube (x, y, energy)
            data_cube = np.asarray(self._electron_count_data.fillna(0.0))
            print("DEBUG: data_cube shape:", data_cube.shape)
            
            # Store original heatmap data if not already stored
            if self._original_heatmap_data is None:
                self._original_heatmap_data = data_cube.sum(axis=-1)
                print("DEBUG: stored original heatmap data")
            
            # Apply clustering
            print("DEBUG: calling kmeans_clustering")
            labels, centres = self.kmeans_clustering(data_cube, n_clusters, norma)
            print("DEBUG: kmeans_clustering completed, labels shape:", labels.shape, "centres shape:", centres.shape)
            
            self._clustering_results = (labels, centres)
            
            # Create clustering visualization
            print("DEBUG: creating clustering visualization")
            clustering_fig = self.plot_kmeans_labels_plotly(labels, f"KMeans Clustering (n={n_clusters})")
            print("DEBUG: clustering figure created")
            
            # Update the heatmap pane with clustering results
            if self.paneA is not None:
                print("DEBUG: updating paneA with clustering results")
                # Force the update by setting object and triggering param updates
                self.paneA.object = clustering_fig
                self.paneA.param.trigger('object')  # Force parameter update
                print("DEBUG: paneA updated and triggered")
                # Alternative: recreate the pane entirely if needed
                # self.paneA = pn.pane.Plotly(clustering_fig, sizing_mode='stretch_both')
            
            # Update spectrum pane to show cluster centers
            print("DEBUG: updating spectrum with clusters")
            self._update_spectrum_with_clusters(centres)
            
            self._clustering_active = True
            print("DEBUG: apply_clustering completed successfully")
            
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
            showlegend=True
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
            self.fitting_button,
            self.clustering_button,
            self.restore_button,
            self.range_slider, 
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
        # Range slider
        self.range_slider = pn.widgets.RangeSlider(
            name="Range",
            start=float(self._e_axis[0]) if len(self._e_axis) > 0 else 0.0,
            end=float(self._e_axis[-1]) if len(self._e_axis) > 0 else 1.0,
            value=(float(self._e_axis[0]), float(self._e_axis[-1])),
            sizing_mode=self._STRETCH_WIDTH,
        )
        self.range_slider.param.watch(self._on_range_changed, 'value')

        # Fitting toggle button
        self.fitting_button = pn.widgets.Button(name="fitting: OFF", button_type="primary")
        self.fitting_button.on_click(self._on_fitting_clicked)
        
        # Clustering button
        self.clustering_button = ToggleButton(
            initial_state=True,
            states={
                'on': {'label': 'Clustering: ON', 'on_click': lambda: print("Clustering started"), 'button_type': 'success'},
                'off': {'label': 'Cleaning clustering', 'on_click': lambda: print("Clustering stopped"), 'button_type': 'danger'}
            },
        )
        
        self.clustering_button.on_click_by_state(
            state=True,
            on_click=self._on_run_clustering_clicked
        )
        
        self.clustering_button.on_click_by_state(
            state=False,
            on_click=self._on_stop_clustering_clicked
        )
        
        # Restore button
        # self.restore_button = pn.widgets.Button(
        #     name="Restore Original", 
        #     button_type="light",
        #     sizing_mode=self._STRETCH_WIDTH
        # )
        # self.restore_button.on_click(self._on_stop_clustering_clicked)
        
        if self._controller.view.run_button is not None:
            self._controller.view.run_button.on_click_by_state(
                state=True, 
                on_click=self._on_run_clustering_clicked
            )
            self._controller.view.run_button.on_click_by_state(
                state=False, 
                on_click=self._on_stop_clustering_clicked
            )

        self.range_slider.visible = False

    def _on_run_clustering_clicked(self):
        """Handle clustering button click."""
        kmeans_input = self._controller.view.kmeans_input
        
        n_clusters = self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS
        if kmeans_input is not None:
            n_clusters = kmeans_input["n_clusters"].value

        self.apply_clustering_kmeans(n_clusters=n_clusters, norma='l2')

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

        # Build Plotly heatmap (figA)
        heat = go.Heatmap(
            z=m_image,
            x=np.arange(nx),
            y=np.arange(ny),
            colorscale="Greys_r",
            showscale=False,
            hovertemplate='x: %{x}<br>y: %{y}<br>Intensity: %{z}<extra></extra>'
        )

        figA = go.Figure(data=[heat])
        figA.update_layout(
            title="Spectrum Image",
            xaxis_title="X",
            yaxis_title="Y",
            yaxis_autorange='reversed',
            dragmode='select'
        )

        # Initial spectrum (center pixel)
        center_x, center_y = nx // 2, ny // 2
        initial_spectrum = self._electron_count_data.isel(x=center_x, y=center_y)
        spectrum_data = np.asarray(initial_spectrum.fillna(0.0))

        trace = go.Scatter(
            x=energy,
            y=spectrum_data,
            mode='lines',
            name='Spectrum',
            line=dict(color='blue', width=2)
        )

        figB = go.Figure(data=[trace])
        figB.update_layout(
            title="Spectrum at Selected Pixel",
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)"
        )

        # Create Panel panes
        self.paneA = pn.pane.Plotly(figA, sizing_mode='stretch_both')
        self.paneB = pn.pane.Plotly(figB, sizing_mode='stretch_both')

    def _setup_callbacks(self):
        """Setup callbacks for interactive functionality."""
        if self.paneA is not None:
            self.paneA.param.watch(self._on_paneA_click, "click_data")

    def _on_paneA_click(self, event):
        """Handle clicks on the heatmap to update spectrum."""
        if event.new is None or not self._clustering_active:
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

    def _on_fitting_clicked(self, event):
        """Handle fitting button clicks."""
        pass  # Placeholder for fitting functionality