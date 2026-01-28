from .layouts import (
    Clustering2MainLayout, 
    Clustering2RightSidebarLayout, 
    UmapEmbeddingPlaceholder, 
    UmapEmbeddingSuccessPlaceholder
)
from whateels.components import ModalManager
import panel as pn

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

    @property
    def main(self):
        return self._main
    
    @property
    def right_sidebar(self):
        return self._right_sidebar
    
    @property
    def modals(self):
        return self._modal_manager.modals
            
    def display_all_combinations_placeholder(self, combinations):
        """Display placeholders for all parameter combinations in the main view, 3 per row."""
        self._main.clear()
        
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
                    sizing_mode='stretch_width',
                    is_loading=False  # Start in waiting state
                )
                self._result_panels.append(placeholder)
                row.append(placeholder)
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
        
        # Find which row this placeholder is in
        row_index = index // 3
        col_index = index % 3
        
        if row_index < len(self._result_rows) and col_index < len(self._result_rows[row_index]):
            success_placeholder = UmapEmbeddingSuccessPlaceholder(
                min_dist,
                n_neighbors,
                sizing_mode='stretch_width'
            )
            self._result_rows[row_index][col_index] = success_placeholder
            self._result_panels[index] = success_placeholder