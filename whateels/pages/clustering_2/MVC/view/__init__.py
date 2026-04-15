from .layouts import (
    Clustering2MainLayout,
    Clustering2LeftSidebarLayout,
    Clustering2RightSidebarLayout, 
    UmapEmbeddingPlaceholder,
)
from whateels.components import ModalManager
import panel as pn
import holoviews as hv
import numpy as np

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate
    from ...MVC import Clustering2PageModel
    
class Clustering2PageView:
    
    # Define stretch constants for consistent sizing modes
    _STRETCH_BOTH = 'stretch_both'
    
    def __init__(self, model: "Clustering2PageModel", custom_page: "GeneralPageTemplate") -> None:

        # Set notification position
        pn.state.notifications.position = 'bottom-left' # type: ignore
        
        pn.config.css_files.append('/assets/css/clustering_2.css') # type: ignore

        self._modal_manager = ModalManager(custom_page)

        self._main = Clustering2MainLayout(sizing_mode=self._STRETCH_BOTH)
        self._left_sidebar = Clustering2LeftSidebarLayout(model) 
        self._right_sidebar = Clustering2RightSidebarLayout(model, custom_page, self._modal_manager)
        
        self._result_panels = []  # Store as instance variable
        self._result_rows = []  # Store rows for easy access
        self._result_columns = []  # Store column wrappers for isolated updates

    @property
    def main(self):
        return self._main
    @property
    def left_sidebar(self):
        return self._left_sidebar
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
            sizing_mode=self._STRETCH_BOTH, 
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
                sizing_mode=self._STRETCH_BOTH,
                is_loading=False
            )
            # Wrap in a Column for isolated updates (optional, for compatibility)
            column_wrapper = pn.Column(
                placeholder,
                sizing_mode=self._STRETCH_BOTH,
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

        self._main.append(self._main.umap_wrapper) # Ensure the UMAP wrapper is in the main layout
        self._main.umap_wrapper.append(grid)
        return self._result_panels

    def replace_placeholder_with_umap_embedding(self, index, min_dist, n_neighbors, umap_data_dict: dict):
        """Replace a placeholder at the given index with a UMAP plot."""
        
        if index < len(self._result_columns):
            emb = umap_data_dict[f'umap_data_{min_dist}_{n_neighbors}'].embedding_
            
            # Create Holoviews Points plot
            zers = np.zeros((emb.shape[0], 3))
            zers[:, :-1] = emb
            
            points = hv.Points(zers, vdims=['color']).opts(
                toolbar='right',
                fill_alpha=0.7,
                bgcolor='white',
                line_alpha=0,
                line_width=0,
                size=3,
                xaxis=None,
                yaxis=None,
                color='steelblue',
                show_legend=False,
                shared_axes=False,
                title=f'UMAP on min_dist={min_dist}, n_neighbors={n_neighbors}',
                responsive=True
            )
            
            plot_panel = pn.pane.HoloViews(points, sizing_mode=self._STRETCH_BOTH, margin=0)
            column_wrapper = self._result_columns[index]
            column_wrapper.objects = [plot_panel]
            self._result_panels[index] = plot_panel

    def disappear_non_loading_placeholders(self, delay_increment=0.125):
        """Trigger disappear animation for all non-loading UmapEmbeddingPlaceholder in the grid, staggered by CSS."""
        non_loading = [ph for ph in self._result_panels if isinstance(ph, UmapEmbeddingPlaceholder) and not ph.is_loading]
        for i, ph in enumerate(non_loading):
            ph.disappear(delay=i * delay_increment)