from .layouts import Clustering2MainLayout, Clustering2LeftSidebarLayout, Clustering2RightSidebarLayout
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
        # self._left_sidebar = Clustering2LeftSidebarLayout()
        self._right_sidebar = Clustering2RightSidebarLayout()
        
        self._modal_manager = ModalManager(custom_page)

    @property
    def main(self):
        return self._main
    
    # @property
    # def left_sidebar(self):
    #     return self._left_sidebar
    
    @property
    def right_sidebar(self):
        return self._right_sidebar
    
    @property
    def modals(self):
        return self._modal_manager.modals
    
    def show_notification(self, message: str, type: str = "info", duration: int = 3000) -> None:
        """Helper to show notifications."""
        if type == "info":
            pn.state.notifications.info(message, duration=duration) # type: ignore
        elif type == "success":
            pn.state.notifications.success(message, duration=duration) # type: ignore
        elif type == "warning":
            pn.state.notifications.warning(message, duration=duration) # type: ignore
        elif type == "error":
            pn.state.notifications.error(message, duration=duration) # type: ignore
            
    def display_all_combinations_placeholder(self, combinations) -> None:
        """Display placeholders for all parameter combinations in the main view, 3 per row."""
        self._main.clear()
        
        # Group combinations into rows of 3
        MAX_COLS = 3
        columns = []
        for i in range(0, len(combinations), MAX_COLS):
            row_combinations = combinations[i:i+MAX_COLS]
            row = pn.Row(sizing_mode='stretch_width', styles={'gap': '10px'})
            for min_dist, n_neighbors in row_combinations:
                # Create a placeholder with loading spinner
                placeholder = pn.Column(
                    pn.Row(
                        pn.indicators.LoadingSpinner(value=True, size=50),
                        sizing_mode='stretch_width',
                        styles={'justify-content': 'center'}
                    ),
                    pn.pane.Markdown(
                        f"min_dist={min_dist}, n_neighbors={n_neighbors}",
                        align='center',
                    ),
                    align='center',
                    sizing_mode='stretch_width',
                    styles={'border': '1px solid #ccc', 'padding': '20px', 'border-radius': '5px', 'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center', 'align-items': 'center'}
                )
                row.append(placeholder)
            columns.append(pn.Column(
                row, 
                sizing_mode='stretch_width', 
                styles={'gap': '10px'},
                margin=0
            ))

        parent_column = pn.Column(*columns, sizing_mode='stretch_both')
        self._main.append(parent_column)