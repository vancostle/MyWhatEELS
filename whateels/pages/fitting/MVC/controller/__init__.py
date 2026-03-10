from .managers import LayoutManager
from whateels.state import CacheManager
from whateels.base.mvc.base_controller import BaseController
from xarray import Dataset
from whateels.helpers.safe_converter import SafeConverter
from ..model.component_item import ComponentItem
from ..view.components.component_item_view import ComponentItemView

import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import FittingModel
    from ..view import FittingView


class FittingController(BaseController):
    """Controller that coordinates fitting UI events, model updates, and plot refreshes."""
    ELEMENT_EAXIS_THRESHOLD = 50
    COMPONENT_EAXIS_THRESHOLD = 50
    COMPONENT_EAXIS_THRESHOLD_VALUE = 4

    def __init__(self, model: "FittingModel", view: "FittingView"):
        """Initialize MVC wiring and bootstrap the fitting view for the selected tab dataset."""
        super().__init__(model, view)

        self._model = model
        self._view = view

        self._layout = LayoutManager(view, self, model)

        app_state = CacheManager.get_cached_app_state()

        all_datasets = app_state.all_datasets

        view.set_controller(self)
        model.set_controller(self)
        
        # Get 'tab' query parameter from URL
        tab_param = self._get_query_param("tab")
        # Convert to integer with default -1
        tab_param = SafeConverter.to_int(tab_param, default=-1) # -1 indicates invalid index in this context
        
        # Validate dataset list and requested tab index.
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            print(tab_param, len(all_datasets))
            self.base_layout.empty_main()
            return

        self.energy_map_active = False
        app_state.plot_dataset = all_datasets[tab_param]
        app_state.selected_tab_index_dataset = tab_param
        
        self._layout.create_tab_and_dataset_info([all_datasets[tab_param]])
        self._nlls_user_update(view)

    @property
    def view(self) -> "FittingView":
        """Access the ClusteringView instance."""
        return self._view
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout

    def _nlls_user_update(self, view: "FittingView"):
        """Attach widget watchers and button callbacks used by the fitting workflow."""
        view.component_input["energy_center"].param.watch(self._energy_center_watcher, 'value')
        view.component_input["model_select"].param.watch(self._model_select_watcher, 'value')

        view._fitting_add_compontent_button.on_click(self._add_component_item_button_callback)

        view._background_subtraction_switch.param.watch(self._background_subtraction_switch_watcher, 'value')

        view._energy_map_toggle_button.on_click(self._energy_map_toggle_button_callback)

    def _energy_center_watcher(self, event):
        """Recenter the editable energy window whenever the center value changes."""
        energy_center = self.view.component_input["energy_center"]
        self.view.component_input["energy_range"].start = event.new - self.COMPONENT_EAXIS_THRESHOLD
        self.view.component_input["energy_range"].end = event.new + self.COMPONENT_EAXIS_THRESHOLD
        self.view.component_input["energy_range"].value = (event.new - self.COMPONENT_EAXIS_THRESHOLD, event.new + self.COMPONENT_EAXIS_THRESHOLD_VALUE)
        self.view.component_input["energy_range"].value = (event.new - self.COMPONENT_EAXIS_THRESHOLD_VALUE, event.new + self.COMPONENT_EAXIS_THRESHOLD_VALUE)


    def _model_select_watcher(self, event):
        """Enable component creation after selecting a model type."""
        model_select = self.view.component_input["model_select"]
        self.view.fitting_add_component_button.disabled = False


    def _add_component_item_button_callback(self, event):
        """Create a component from sidebar inputs, register it in the model, and render its editor card."""
        energy_center = self.view.component_input["energy_center"].value
        model_select = self.view.component_input["model_select"].value
        energy_range = self.view.component_input["energy_range"].value
        flexibility = self.view.component_input["flexibility"].value

        component_item = ComponentItem(energy_center, model_select, energy_range, flexibility)
        self._model.add_component(component_item, component_item.flexibility)

        component_item_view = ComponentItemView(self, component_item,   
                                                self._model, 
                                                self._layout.get_energy_range(), 
                                                self._view)
        self._layout.add_new_component_input(component_item_view)

        self._view.energy_map_toggle_button.disabled = False
        

    def _test(self, event):
        """Internal helper kept for manual testing of model creation."""
        self._model._create_model(self._model.dataset, name_area='default', flex='medium')
    
    def show_nlls_config_popup(self, event):
        """Show the NLLS configuration popup."""
        #self._layout.show_nlls_config_popup(event)
        self._on_create_model(event)

    
    def _get_only_eels_datasets(self, datasets: list["Dataset"]) -> list["Dataset"]:
        """Filter and return only EELS datasets from the provided list."""
        return [ds for ds in datasets if "Eloss" in ds.coords]
    
    def _get_query_param(self, param_name: str) -> str | None:
        """Retrieve a specific query parameter from the URL, handling both list and single value cases."""
        params = pn.state.location.query_params if pn.state.location else {}
        value = params.get(param_name, None)
        if isinstance(value, list):
            return value[0]
        return value
    
    def update_plot(self, fitting_results = None):
        """Proxy plot updates to layout manager."""
        self.layout.update_plot(fitting_results)

    def _background_subtraction_switch_watcher(self, event):
        """Toggle multifit background subtraction mode and refit if needed."""
        app_state = CacheManager.get_cached_app_state()
        app_state.is_multifit = event.new
        self.layout.update_plot()
        self._model.create_model()
        self._model.fit_reference()

    def _energy_map_toggle_button_callback(self, event):
        """Switch between standard image view and computed energy-map overlay."""
        if not self.energy_map_active:
            try:
                self.layout.plot_energy_map()
                self.energy_map_active = True
            except Exception as e:
                print(f"Error occurred while plotting energy map: {e}")
                self.energy_map_active = False
                # Restore button state if plotting the energy map fails.
                self.view._energy_map_toggle_button.toggle()
            
        else:
            self.layout.plot_image()
            self.energy_map_active = False

    def get_energy_range(self):
        """Return the active energy range only when energy-map mode is enabled."""
        if not self.energy_map_active:
            return None
        return self._layout.get_energy_range()