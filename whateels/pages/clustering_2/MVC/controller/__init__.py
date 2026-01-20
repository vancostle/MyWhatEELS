
from whateels.helpers import SafeConverter, URLUtils

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...MVC import Clustering2PageModel, Clustering2PageView

class Clustering2PageController:
    
    def __init__(self, model: "Clustering2PageModel", view: "Clustering2PageView") -> None:
        TAB_PARAM = "tab"
        tab_param = URLUtils.get_query_param(TAB_PARAM) # Get tab index from URL
        tab_param = SafeConverter.to_int(tab_param, default=-1) # Get tab index as int, default to -1 if invalid
        all_datasets = model.app_state.all_datasets

        # Display nothing if no valid tab or datasets
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            print("No valid datasets or tab index.")
            return

        # Set selected dataset in the model
        model.selected_dataset = all_datasets[tab_param]