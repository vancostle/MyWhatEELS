from .managers import LayoutManager
from whateels.shared_state import AppState
from whateels.base.mvc.base_controller import BaseController
from .services.oos_loader_service import Loader_OOS
from xarray import Dataset
from whateels.helpers.constants import OOS_ROOT

import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import QuantificationModel
    from ..view import QuantificationView

class ElementItem:
    def __init__(self, element, shells, fit_range= None, quant_range= None):
        self.element = element
        self.shells = shells
        self.fit_range = fit_range
        self.quant_range = quant_range
        self.cross_sections = {}
        self.chemical_shift = 0.0  # Default chemical shift value

    def __str__(self):
        return f"{self.element} ({', '.join(self.shells)})"

    def set_fit_range(self, fit_range):
        self.fit_range = fit_range

    def set_quant_range(self, quant_range):
        self.quant_range = quant_range


class QuantificationController(BaseController):

    def __init__(self, model: "QuantificationModel", view: "QuantificationView"):
        view.set_controller(self)
        super().__init__(model, view)

        self._model = model
        self._view = view

        self._layout = LayoutManager(view, self, model)
        
        app_state = AppState()
        all_datasets = app_state.all_datasets
        self.loader_oos = Loader_OOS(dir_path = str(OOS_ROOT / "Hartree_Xsections_FSalvat"))

        if not isinstance(all_datasets, list) or not all_datasets:
            self.base_layout.empty_main()
            return
        
        eels = self._get_only_eels_datasets(all_datasets)
        self._layout.create_tab_and_dataset_info(eels)

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
        view.plot_elements_button.on_click(self.plot_elements)

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
                print("lets plot")
                
                self._layout.plot_quantification_element(element_item)
            else:
                print("Element already added.")
        return

    def plot_quantification_element(self, element_item: ElementItem):
        self._layout.plot_quantification_element(element_item)
        return

    def _run_quantification(self, event):
        print("Running quantification...")
        if not self._model.app_state.quantification_elements:
            print("No elements to quantify.")
        elif len(self._model.app_state.quantification_elements) < 2:
            print("At least two elements are required for quantification.")
        else:
            self._layout.plot_quantification_pie()
        return

    def plot_elements(self, event):
        if not self._model.app_state.quantification_elements:
            print("No elements to plot.")
        else:
            self._layout.plot_quantification_elements( self._model.app_state.quantification_elements, self.loader_oos)
        return
    
    def _get_only_eels_datasets(self, datasets: list["Dataset"]) -> list["Dataset"]:
        """Filter and return only EELS datasets from the provided list."""
        return [ds for ds in datasets if "Eloss" in ds.coords]