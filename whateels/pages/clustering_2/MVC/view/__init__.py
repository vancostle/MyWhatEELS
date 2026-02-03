from .layouts import (
    Clustering2MainLayout, 
    Clustering2RightSidebarLayout, 
    UmapEmbeddingPlaceholder, 
)
from whateels.components import ModalManager
import panel as pn
import plotly.graph_objs as go

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate
    from ...MVC import Clustering2PageModel
    
class Clustering2PageView:
    
    def __init__(self, model: "Clustering2PageModel", custom_page: "GeneralPageTemplate") -> None:
        # Set notification position
        pn.state.notifications.position = 'bottom-left' # type: ignore

        self._modal_manager = ModalManager(custom_page)

        self._main = Clustering2MainLayout()
        self._right_sidebar = Clustering2RightSidebarLayout(model, self._modal_manager)
        
        self._result_panels = []  # Store as instance variable
        self._result_rows = []  # Store rows for easy access
        self._result_columns = []  # Store column wrappers for isolated updates

    @property
    def main(self):
        return self._main
    
    @property
    def right_sidebar(self):
        return self._right_sidebar
    
    @property
    def modals(self):
        return self._modal_manager.modals
            
    def display_all_combination_placeholders(self, combinations : list[tuple[float, int]]):
        """Display placeholders for all parameter combinations in a Panel GridSpec."""
        self._main.clear()

        # Reset instance variables
        self._result_panels = []
        self._result_columns = []

        MAX_COLS = 3
        grid = pn.GridSpec(
            sizing_mode='stretch_both', 
            mode='override',
            styles={'grid-gap': '10px'},
        )

        delay = 0
        delay_increment = 0.125

        for idx, (min_dist, n_neighbors) in enumerate(combinations):
            row = idx // MAX_COLS
            col = idx % MAX_COLS
            placeholder = UmapEmbeddingPlaceholder(
                min_dist,
                n_neighbors,
                delay=delay,
                sizing_mode='stretch_both',
                is_loading=False
            )
            # Wrap in a Column for isolated updates (optional, for compatibility)
            column_wrapper = pn.Column(
                placeholder,
                sizing_mode='stretch_both',
                margin=0,
                styles={
                    'aspect-ratio': '1',
                    'margin-bottom': '10px',
                    'height': '100%'
                }
            )
            self._result_panels.append(placeholder)
            self._result_columns.append(column_wrapper)
            grid[row, col] = column_wrapper
            delay += delay_increment

        self._main.append(grid)
        return self._result_panels

    def replace_placeholder_with_umap_embedding(self, index, min_dist, n_neighbors, umap_data_dict: dict):
        """Replace a placeholder at the given index with a UMAP plot."""
        
        if index < len(self._result_columns):
            emb = umap_data_dict[f'umap_data_{min_dist}_{n_neighbors}'].embedding_
            
            # Create Plotly scatter plot
            fig = go.Figure(data=go.Scatter(
                x=emb[:, 0],
                y=emb[:, 1],
                mode='markers',
                marker=dict(
                    size=3,
                    color='steelblue',
                    opacity=0.7,
                    line=dict(width=0)
                )
            ))
            
            fig.update_layout(
                title=f'UMAP on min_dist={min_dist}, n_neighbors={n_neighbors}',
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                plot_bgcolor='white',
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            plot_panel = pn.pane.Plotly(fig, sizing_mode='stretch_both')
            column_wrapper = self._result_columns[index]
            column_wrapper.objects = [plot_panel]
            self._result_panels[index] = plot_panel

    def disappear_non_loading_placeholders(self, delay_increment=0.125):
        """Trigger disappear animation for all non-loading UmapEmbeddingPlaceholder in the grid, staggered by CSS."""
        non_loading = [ph for ph in self._result_panels if isinstance(ph, UmapEmbeddingPlaceholder) and not ph.is_loading]
        for i, ph in enumerate(non_loading):
            ph.disappear(delay=i * delay_increment)