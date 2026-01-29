from .layouts import (
    Clustering2MainLayout, 
    Clustering2RightSidebarLayout, 
    UmapEmbeddingPlaceholder, 
    UmapEmbeddingSuccessPlaceholder
)
from whateels.components import ModalManager
import panel as pn, numpy as np, holoviews as hv

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate
    from ...MVC import Clustering2PageModel
    
class Clustering2PageView:
    
    def __init__(self, model: "Clustering2PageModel", custom_page: "GeneralPageTemplate") -> None:
        # Set notification position
        pn.state.notifications.position = 'bottom-left' # type: ignore

        self._main = Clustering2MainLayout()
        self._right_sidebar = Clustering2RightSidebarLayout()
        
        self._modal_manager = ModalManager(custom_page)
        
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
            
    def display_all_combination_placeholders(self, combinations):
        """Display placeholders for all parameter combinations in the main view, 3 per row."""
        self._main.clear()
        
        # Reset instance variables
        self._result_panels = []
        self._result_rows = []
        self._result_columns = []
        
        # Group combinations into rows of 3
        MAX_COLS = 3

        delay = 0 # Initial delay for staggered animation
        delay_increment = 0.125  # Seconds between each placeholder animation
        
        for i in range(0, len(combinations), MAX_COLS):
            row_combinations = combinations[i:i+MAX_COLS]
            row = pn.Row(sizing_mode='stretch_width', styles={'gap': '10px'})
            for min_dist, n_neighbors in row_combinations:
                placeholder = UmapEmbeddingPlaceholder(
                    min_dist, 
                    n_neighbors, 
                    delay=delay,
                    sizing_mode='stretch_both',
                    is_loading=False  # Start in waiting state
                )
                # Wrap each placeholder in a Column for isolated updates
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
                row.append(column_wrapper)
                delay += delay_increment
            self._result_rows.append(row)
        
        parent_column = pn.Column(
            *[pn.Column(
                row, 
                sizing_mode='stretch_width', 
                margin=0
            ) for row in self._result_rows], 
            sizing_mode='stretch_both'
        )
        self._main.append(parent_column)
        
        return self._result_panels
    
    def replace_placeholder_with_success(self, index, min_dist, n_neighbors):
        """Replace a placeholder at the given index with a success placeholder."""
        
        if index < len(self._result_columns):
            success_placeholder = UmapEmbeddingSuccessPlaceholder(
                min_dist,
                n_neighbors,
                sizing_mode='stretch_both'
            )
            
            # Replace content in the column wrapper (isolated update)
            column_wrapper = self._result_columns[index]
            column_wrapper.objects = [success_placeholder]
            
            # Update the reference in result_panels
            self._result_panels[index] = success_placeholder

    def replace_placeholder_with_umap_embedding(self, index, min_dist, n_neighbors, umap_data_dict: dict):
        """Replace a placeholder at the given index with a UMAP plot."""
        
        if index < len(self._result_columns):
            emb = umap_data_dict[f'umap_data_{min_dist}_{n_neighbors}'].embedding_
            zers = np.zeros((emb.shape[0], 3))
            zers[:, :-1] = emb
            points = hv.Points(zers, vdims=['color']).opts(
                toolbar=None, 
                fill_alpha=0.1, 
                bgcolor='black',
                line_alpha=0, 
                line_width=0.15, 
                size=2.5, 
                xaxis=None, 
                yaxis=None,
                show_legend=True, 
                color='color', 
                shared_axes=False,
                title=f'UMAP on masked data, min_dist={min_dist}, n_neighbors={n_neighbors}'
            )
            plot_panel = pn.panel(points, sizing_mode='stretch_both')
            column_wrapper = self._result_columns[index]
            column_wrapper.objects = [plot_panel]
            self._result_panels[index] = plot_panel