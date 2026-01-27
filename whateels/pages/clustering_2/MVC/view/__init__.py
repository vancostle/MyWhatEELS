from .layouts import Clustering2MainLayout, Clustering2RightSidebarLayout, UmapEmbeddingPlaceholder
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
        columns = []
        delay = 0
        delay_increment = 0.125  # Seconds between each placeholder animation
        is_first = True
        result_panels = []
        
        for i in range(0, len(combinations), MAX_COLS):
            row_combinations = combinations[i:i+MAX_COLS]
            row = pn.Row(sizing_mode='stretch_width', styles={'gap': '10px'})
            for min_dist, n_neighbors in row_combinations:
                placeholder = UmapEmbeddingPlaceholder(
                    min_dist, 
                    n_neighbors, 
                    delay=delay,
                    sizing_mode='stretch_width'
                )
                result_panels.append(placeholder) # For later use
                row.append(placeholder) # Add placeholder to the row
                delay += delay_increment
                if is_first:
                    is_first = False
            columns.append(pn.Column(
                row, 
                sizing_mode='stretch_width', 
                margin=0
            ))

        # Change state after 2 seconds
        pn.state.add_periodic_callback(
            lambda: setattr(result_panels[0], 'is_loading', True), 
            period=2000, 
            count=1
        )
        
        parent_column = pn.Column()
        self._main.append(parent_column)