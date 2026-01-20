
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
        
        eloss = model.selected_dataset["Eloss"].values # Get Eloss values from the selected dataset
        eloss_min = float(eloss.min())
        eloss_max = float(eloss.max())
        
        # print(f"eloss: {model.selected_dataset["Eloss"]}")
        # print(f"eloss values: {eloss}")
        # print(f"Setting min/max cut signal to dataset Eloss range: {eloss_min} - {eloss_max}")
        
        view.right_sidebar.min_cut_signal.value = eloss_min
        view.right_sidebar.min_cut_signal.start = eloss_min
        view.right_sidebar.min_cut_signal.end = eloss_max
        
        view.right_sidebar.max_cut_signal.value = eloss_max
        view.right_sidebar.max_cut_signal.start = eloss_min
        view.right_sidebar.max_cut_signal.end = eloss_max