"""
Base spectrum image (datacube) visualization component.

This is a shared component for basic 3D EELS datacube visualization using Plotly.
It provides:
- Integrated 2D heatmap showing summed intensity
- Interactive spectrum display for selected pixels
- Hover, click, and region selection interactions
- Resizable two-column layout

Page-specific features (like clustering) should extend this base component.
"""

import panel as pn
import numpy as np
import plotly.graph_objs as go

from whateels.helpers import SpectrumExtractor
from whateels.components import SplitJs
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xarray import Dataset

class BaseSpectrumImagePlot:
    """
    Base component for spectrum image (datacube) visualization.
    
    Displays a 2D heatmap of integrated intensity alongside an interactive
    spectrum viewer. Supports hover, click, and region selection.
    
    Can be extended by page-specific visualizers for additional features
    like clustering, fitting, etc.
    """
    
    # Panel sizing modes
    _STRETCH_WIDTH = "stretch_width"
    
    # CSS classes and constants for dataset info panel
    _DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
    _DATASET_INFO_CLASS = ["dataset-info", "animated"]
    _DATASET_INFO_TITLE = "<h5 class=\"dataset-info-title\">Dataset Information</h5>"
    
    _NOT_AVAILABLE = 'N/A'
    
    # Default axis names
    _DEFAULT_ELOSS = 'Eloss'
    _DEFAULT_AXIS_X = 'x'
    _DEFAULT_AXIS_Y = 'y'

    def __init__(self, dataset: "Dataset", eloss_name: str = _DEFAULT_ELOSS):
        """
        Initialize spectrum image visualizer.
        
        Args:
            dataset: xarray Dataset containing the EELS datacube
            eloss_name: Name of the energy loss axis (default: 'Eloss')
        """
        self._dataset = dataset
        self._eloss_name = eloss_name
        
        # Energy axis (eje de energía)
        self._e_axis = self._dataset.coords[self._eloss_name].values

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
        self._frozen_pixel = None  # Store frozen pixel from single click

        # Widgets / panes placeholders
        self.paneA = None  # Plotly heatmap pane
        self.paneB = None  # Plotly spectrum pane

        # Setup plots and callbacks
        self._setup_plots()
        self._setup_callbacks()

    # --- Public layout builders ---
    def create_plots(self) -> pn.Column:
        """
        Create the resizable two-column layout with heatmap and spectrum.
        
        Returns:
            ResizableColumns: Two-column layout with heatmap (left) and spectrum (right)
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
            margin=0
        )

        container = pn.Column( 
            splitjs,
            sizing_mode='stretch_both'
        )

        return container

    def create_dataset_info(self, dataset_attrs: dict | None = None):
        """
        Create dataset information panel.
        
        Args:
            dataset_attrs: Optional dictionary of dataset attributes. 
                         If not provided, uses self._dataset.attrs
        
        Returns:
            pn.Column: Panel column with dataset info
        """
        # Use provided attrs or fall back to dataset attrs
        attrs = dataset_attrs if dataset_attrs is not None else (self._dataset.attrs if self._dataset is not None else {})
        
        # Constants
        SHAPE = 'shape'
        BEAM_ENERGY = 'beam_energy'
        COLLECTION_ANGLE = 'collection_angle'
        CONVERGENCE_ANGLE = 'convergence_angle'
        NOT_AVAILABLE = 'N/A'
        ENERGY_UNIT = " keV"
        ANGLE_UNIT = " mrad"
        
        shape = attrs.get(SHAPE, NOT_AVAILABLE)
        beam_energy = attrs.get(BEAM_ENERGY, NOT_AVAILABLE)
        convergence_angle = attrs.get(CONVERGENCE_ANGLE, NOT_AVAILABLE)
        collection_angle = attrs.get(COLLECTION_ANGLE, NOT_AVAILABLE)
        
        # Build info panel
        dataset_info = pn.Column(
            pn.pane.HTML("<h5>Dataset Information</h5>"),
            pn.Row(
                pn.pane.HTML("<strong>Shape:</strong>"),
                pn.pane.Str(shape)
            ),
            pn.Row(
                pn.pane.HTML("<strong>Beam Energy:</strong>"),
                pn.pane.Str(f"{beam_energy}{ENERGY_UNIT}")
            ),
            pn.Row(
                pn.pane.HTML("<strong>Convergence Angle:</strong>"),
                pn.pane.Str(f"{convergence_angle}{ANGLE_UNIT}")
            ),
            pn.Row(
                pn.pane.HTML("<strong>Collection Angle:</strong>"),
                pn.pane.Str(f"{collection_angle}{ANGLE_UNIT}")
            ),
            sizing_mode="stretch_width"
        )
        
        return dataset_info

    # --- Plot / Pane Setup (Plotly) ---
    def _setup_plots(self):
        """
        Initialize the heatmap and spectrum panes.
        
        Creates:
        - paneA: 2D heatmap of integrated intensity with selection support
        - paneB: Spectrum plot for selected pixel
        """
        # Build image (m_image) from data cube by summing along energy axis
        m_image_da = self._electron_count_data.sum(self._eloss_name)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Expected 2D integrated image, got shape={m_image.shape}")

        ny, nx = m_image.shape
        
        # energy axis
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # Build Plotly heatmap (figA) with selectors to enable lasso/box selection
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
        figA.update_yaxes(
            autorange="reversed", 
            scaleanchor="x", 
            scaleratio=1, 
            constrain="domain",
            showgrid=False, 
            zeroline=False, 
            showticklabels=False
        )
        figA.update_xaxes(
            showgrid=False, 
            zeroline=False, 
            showticklabels=False, 
            constrain="domain"
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
        self.paneA = pn.pane.Plotly(
            figA, 
            config={"responsive": True}, 
            sizing_mode='stretch_both',
            margin=0
        )
        self.paneB = pn.pane.Plotly(
            figB, 
            config={"responsive": True}, 
            sizing_mode='stretch_both',
            margin=0
        )

    def _setup_callbacks(self):
        """Setup callbacks for interactive functionality."""
        if self.paneA is not None:
            # Watch click, hover and selection
            self.paneA.param.watch(self._on_paneA_click, "click_data")
            self.paneA.param.watch(self._on_paneA_hover, "hover_data")
            self.paneA.param.watch(self._on_paneA_selected, "selected_data")

    # --- Protected Helper Methods ---

    def _on_paneA_hover(self, event):
        """
        Handle hover on the heatmap to show single-pixel spectrum.
        
        If a pixel is frozen (via single click) or a region is selected, hover is ignored.
        """
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        
        # If a region is selected or pixel is frozen, don't override
        if self._region_pairs or self._frozen_pixel is not None:
            return
        
        i, j = int(point['y']), int(point['x'])
        
        # Plot the spectrum for the hovered pixel
        fig = self._plot_pixel_spectrum(i, j, title_prefix="Hover")
        if fig is not None and self.paneB is not None:
            self.paneB.object = fig

    def _plot_pixel_spectrum(self, i, j, title_prefix="Hover"):
        """
        Plot spectrum for a specific pixel (i, j).
        
        This is a basic implementation that shows only the original spectrum.
        Subclasses can override to add normalized, fitted, or cluster spectra.
        
        Args:
            i, j: Pixel coordinates
            title_prefix: Prefix for the plot title (e.g., "Hover", "Click")
            
        Returns:
            go.Figure or None: Plotly figure or None if spectrum cannot be retrieved
        """
        # Get original spectrum
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        if spec is None:
            return None
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self._energy,
            y=spec,
            mode='lines',
            name=f"Spectrum (i={i}, j={j})",
        ))
        
        fig.update_layout(
            title=f"{title_prefix} at (i={i}, j={j})",
            margin=dict(l=16, r=16, t=48, b=16),
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (AU)",
            legend=dict(
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(0,0,0,0.2)',
                borderwidth=1,
            )
        )
        
        return fig

    def _on_paneA_click(self, event):
        """
        Handle single click on the heatmap.
        
        Single click: Freezes the current pixel so hovering doesn't change the view.
        """
        if event.new is None:
            return
        
        try:
            point = event.new['points'][0]
            i, j = int(point['y']), int(point['x'])
            
            # Freeze the pixel
            self._frozen_pixel = (i, j)
            
            # Plot the frozen pixel spectrum
            fig = self._plot_pixel_spectrum(i, j, title_prefix="Click (Frozen)")
            if fig is not None and self.paneB is not None:
                self.paneB.object = fig
                
        except Exception as e:
            print(f"Error handling click: {e}")

    def _on_paneA_selected(self, event):
        """
        Handle lasso/box selection and show summed spectrum for selected pixels.
        
        Unfreezes any frozen pixel when a region is selected.
        """
        pairs = SpectrumExtractor.extract_region(event)
        self._region_pairs = pairs
        
        if not pairs:
            # no selection: unfreeze pixel and return to hover mode
            self._frozen_pixel = None
            if self._last_hover_point is not None:
                i, j = int(self._last_hover_point['y']), int(self._last_hover_point['x'])
                spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
                if spec is not None:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=self._energy, 
                        y=spec, 
                        mode='lines', 
                        name=f"(i={i}, j={j})"
                    ))
                    fig.update_layout(
                        title="Hover", 
                        xaxis_title="Energy Loss (eV)", 
                        yaxis_title="Intensity (AU)",
                        legend=dict(
                            x=0.98, 
                            y=0.98, 
                            xanchor='right', 
                            yanchor='top', 
                            bgcolor='rgba(255,255,255,0.6)', 
                            bordercolor='rgba(0,0,0,0.1)', 
                            borderwidth=1
                        )
                    )
                    if self.paneB is not None:
                        self.paneB.object = fig
            return

        # Unfreeze pixel when a region is selected
        self._frozen_pixel = None
        
        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)
        if res is None:
            return
        spec, n_points = res
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=self._energy, 
            y=spec, 
            mode='lines', 
            name=f"sum (points={n_points})"
        ))
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
