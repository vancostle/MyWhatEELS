from .managers import LayoutManager
from whateels.shared_state import AppState
from whateels.base.mvc.base_controller import BaseController
from .services.oos_loader_service import Loader_OOS
from xarray import Dataset
from whateels.helpers.constants import OOS_ROOT
from whateels.helpers.safe_converter import SafeConverter


import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import QuantificationModel
    from ..view import QuantificationView
    

class ElementItem:
    def __init__(self, element, shells, element_name, fit_range= None, quant_range= None):
        self.element = element
        self.shells = shells
        self.element_name = element_name
        self.fit_range = fit_range
        self.quant_range = quant_range
        self.cross_sections = {}
        self.chemical_shift = 0.0  # Default chemical shift value

    def __str__(self):
        return f"{self.element_name} ({self.element}) ({', '.join(self.shells)})"

    def set_fit_range(self, fit_range):
        self.fit_range = fit_range

    def set_quant_range(self, quant_range):
        self.quant_range = quant_range


class QuantificationController(BaseController):

    def __init__(self, model: "QuantificationModel", view: "QuantificationView"):
        
        
        super().__init__(model, view)

        self._model = model
        self._view = view

        

        self._layout = LayoutManager(view, self, model)

        all_datasets = AppState().all_datasets

        self.loader_oos = Loader_OOS(dir_path = str(OOS_ROOT / "Hartree_Xsections_FSalvat"))
        view.set_controller(self)
        
        # Get 'tab' query parameter from URL
        tab_param = self._get_query_param("tab")
        # Convert to integer with default -1
        tab_param = SafeConverter.to_int(tab_param, default=-1) # -1 indicates invalid index in this context
        
        # Validate datasets and tab index
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            self.base_layout.empty_main()
            return
        
        self._layout.create_tab_and_dataset_info([all_datasets[tab_param]])

        

        self._quanti_active =  False
        
        
        self._quantification_user_update(view)

    @property
    def view(self) -> "QuantificationView":
        """Access the ClusteringView instance."""
        return self._view
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout

    def _quantification_user_update(self, view: "QuantificationView"):
        """Debug method to print the Quantification input widgets."""
        view.quanti_input["element_num"].param.watch(self._element_num_watcher, 'value')
        view.quanti_add_element_button.on_click(self._add_element_item_button_callback)
        view.quanti_run_button.on_click(self._run_quantification)
        view.quanti_toggle_button.on_click(self._toggle_quantification)

    def _element_num_watcher(self, event):
        """Watcher for changes in the element number selection."""
        self.view.quanti_input['shells_multiselect'].value = []
        self.view.quanti_input['shells_multiselect'].options = self.loader_oos.avaibable_subshells(self.view.quanti_input['element_num'].value) if self.view.quanti_input['element_num'].value else []
    
    def _add_element_item_button_callback(self, event):
        if not self.view.quanti_input['element_num'].value:
            print("No element selected.")
        elif not self.view.quanti_input['shells_multiselect'].value:
            print("No shells selected.")
        else:
            element=self.view.quanti_input['element_num'].value
            repeted = any(element_i.element == element for element_i in self._model.app_state.quantification_elements)
            if not repeted:
                element_item = ElementItem(
                element=self.view.quanti_input['element_num'].value,
                shells=self.view.quanti_input['shells_multiselect'].value,
                element_name= self.loader_oos.element_name(self.view.quanti_input['element_num'].value)
                )
                min_eaxis_cs = None
                for ishell in element_item.shells:
                    eaxis, counts, onset = self.loader_oos.oos_reader(element_item.element, ishell)
                    V = self._layout.get_active_dataset().attrs['beam_energy']
                    b = self._layout.get_active_dataset().attrs['collection_angle']
                    element_item.cross_sections[ishell] = [eaxis, counts, onset, self.loader_oos.df_cross_section(element_item.element, ishell, V = V, b = b,), V, b]

                    min_eaxis_cs = eaxis[0] if min_eaxis_cs is None else min(min_eaxis_cs, eaxis[0])                

                element_item_view, element_item = self._view.get_new_element_item_view(element_item, (self._layout.get_energy_range()[0], min_eaxis_cs, self._layout.get_energy_range()[-1]))
                self._model.app_state.quantification_elements.append(element_item)
                self._layout.add_new_element_input(element_item_view)
                self.view.quanti_input['shells_multiselect'].value = []
                self._layout.plot_quantification_elements()
            else:
                print("Element already added.")
        return
    def add_element_item(self, element_item: ElementItem):
        min_eaxis_cs = None
        for ishell in element_item.shells:
            eaxis, counts, onset = self.loader_oos.oos_reader(element_item.element, ishell)
            V = self._layout.get_active_dataset().attrs['beam_energy']
            b = self._layout.get_active_dataset().attrs['collection_angle']
            element_item.cross_sections[ishell] = [eaxis, counts, onset, self.loader_oos.df_cross_section(element_item.element, ishell, V = V, b = b,), V, b]

            min_eaxis_cs = eaxis[0] if min_eaxis_cs is None else min(min_eaxis_cs, eaxis[0])                

        element_item_view, element_item = self._view.get_new_element_item_view(element_item, (self._layout.get_energy_range()[0], min_eaxis_cs, self._layout.get_energy_range()[-1]))
        self._layout.add_new_element_input(element_item_view)
        self.view.quanti_input['shells_multiselect'].value = []
        print("Element added programmatically.")
        return


    def _run_quantification(self, event):
        if not self._model.app_state.quantification_elements:
            print("No elements to quantify.")
        elif len(self._model.app_state.quantification_elements) < 2:
            print("At least two elements are required for quantification.")
        else:
            self._layout.plot_quantification_pie()
        return
    

    def _toggle_quantification(self, event):
        print(self._quanti_active)
        if not self._quanti_active:
            if not self._model.app_state.quantification_elements:
                self.view.quanti_toggle_button.toggle()  # Revert the toggle state
                print("No elements to quantify.")
            elif len(self._model.app_state.quantification_elements) < 2:
                self.view.quanti_toggle_button.toggle()  # Revert the toggle state
                print("At least two elements are required for quantification.")
                
            else:
                try:
                    self._layout.plot_quantification_pie()
                    self._quanti_active = True
                except Exception as e:
                    self.view.quanti_toggle_button.toggle()
                    print(f"Error plotting quantification pie chart: {e}")
                
            
        else:
            self.plot_elements()
            self._quanti_active = False

    def plot_elements(self):
        if not self._model.app_state.quantification_elements:
            print("No elements to plot.")
        else:
            self._layout.plot_quantification_elements()
        return
    
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