from .managers import LayoutManager
from whateels.state import CacheManager
from whateels.base.mvc.base_controller import BaseController
from xarray import Dataset
from whateels.helpers.safe_converter import SafeConverter
from ..model.component_item import ComponentItem
from ..view.components.component_item_view import ComponentItemView
from .nlls_controller import NLLSController

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

        # No longer needed: model.set_controller(self)
        
        # Get 'tab' query parameter from URL
        tab_param = self._get_query_param("tab")
        # Convert to integer with default -1
        tab_param = SafeConverter.to_int(tab_param, default=-1) # -1 indicates invalid index in this context
        
        # Validate dataset list and requested tab index.
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            self.base_layout.empty_main()
            return

        self.energy_map_active = False
        app_state.plot_dataset = all_datasets[tab_param]
        app_state.selected_tab_index_dataset = tab_param
        
        self._layout.create_tab_and_dataset_info([all_datasets[tab_param]])
        self._nlls_user_update(view)
        self._nlls_controller = NLLSController(self, view, app_state)

        # Keep the source selectors aligned with Home preprocessing and clustering
        # state while the page is open.
        self._preprocessed_dataset_watcher = app_state.param.watch(
            self._on_preprocessed_dataset_changed,
            'preprocessed_plot_dataset',
        )
        self._clustering_result_watcher = app_state.param.watch(
            self._on_clustering_result_changed,
            'last_clustering_result',
        )
        self._active_data_source: str | None = None
        self._sync_data_source_controls(select_preprocessed=True)

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

        # Enable/disable 'Add Component' reactively based on lasso selection
        if self._layout._chosen_visualizers:
            vis = self._layout._chosen_visualizers[0]
            def _on_selection_change(has_selection):
                self._view.fitting_add_component_button.disabled = not has_selection
                if not has_selection and hasattr(self, '_nlls_controller'):
                    self._nlls_controller.on_roi_changed()

            vis.on_selection_change = _on_selection_change

            def _on_region_committed():
                vis.update_plot()  # pushes new ROI to paneB, updates app_state.spectra
                if hasattr(self, '_nlls_controller'):
                    self._nlls_controller.on_roi_changed()
                if self._model.dictionary.get('components'):
                    try:
                        self._model.create_model()  # syncs model._spectra from app_state.spectra
                        ref = self._model.fit_reference()
                        self._layout.update_plot(ref)
                    except Exception:
                        pass  # plain ROI is already visible from update_plot() above

            vis.on_region_committed = _on_region_committed

        view.preprocessed_data_button.on_click(self._on_preprocessed_data_selected)
        view.clustering_data_button.on_click(self._on_clustering_data_selected)

        view._energy_map_toggle_button.on_click(self._energy_map_toggle_button_callback)

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

    def _energy_center_watcher(self, event):
        """Recenter the editable energy window whenever the center value changes."""
        self.view.component_input["energy_range"].start = event.new - self.COMPONENT_EAXIS_THRESHOLD
        self.view.component_input["energy_range"].end = event.new + self.COMPONENT_EAXIS_THRESHOLD
        self.view.component_input["energy_range"].value = (event.new - self.COMPONENT_EAXIS_THRESHOLD_VALUE, event.new + self.COMPONENT_EAXIS_THRESHOLD_VALUE)

    def _model_select_watcher(self, event):
        """Enable component creation after selecting a model type."""
        self.view.fitting_add_component_button.disabled = False

    def _add_component_item_button_callback(self, event):
        """Create a component from sidebar inputs, register it in the model, and render its editor card."""
        energy_center = self.view.component_input["energy_center"].value
        model_select = self.view.component_input["model_select"].value
        energy_range = self.view.component_input["energy_range"].value
        flexibility = self.view.component_input["flexibility"].value

        component_item = ComponentItem(energy_center, model_select, energy_range, str(flexibility))
        self._model.add_component(component_item, component_item.flexibility)

        component_item_view = ComponentItemView(self, component_item,   
                                                self._model, 
                                                self._layout.get_energy_range(), 
                                                self._view)
        self._layout.add_new_component_input(component_item_view)

        self._view.energy_map_toggle_button.disabled = False
        # After adding a component, update the plot
        self.update_plot(self._model.ref_results if hasattr(self._model, 'ref_results') else None)
        
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

    def _has_valid_preprocessed_data(self, notify: bool = False) -> bool:
        """Validate Home preprocessed dataset availability and basic spatial compatibility."""
        app_state = CacheManager.get_cached_app_state()

        preprocessed_dataset = app_state.preprocessed_plot_dataset
        if preprocessed_dataset is None:
            if notify:
                pn.state.notifications.warning(
                    "No preprocessed data available. Apply preprocessing in Home first.",
                    duration=5000,
                ) # type: ignore
            return False

        selected_idx = app_state.selected_tab_index_dataset
        if not (isinstance(app_state.all_datasets, list) and 0 <= selected_idx < len(app_state.all_datasets)):
            return False

        raw_dataset = app_state.all_datasets[selected_idx]
        try:
            raw_e = raw_dataset["ElectronCount"]
            pre_e = preprocessed_dataset["ElectronCount"]
            if len(pre_e.shape) != 3:
                raise ValueError("Expected a 3D preprocessed ElectronCount DataArray.")
            if pre_e.shape[0] != raw_e.shape[0] or pre_e.shape[1] != raw_e.shape[1]:
                raise ValueError(
                    f"Spatial shape mismatch. Raw={raw_e.shape[:2]}, preprocessed={pre_e.shape[:2]}"
                )
        except Exception as e:
            if notify:
                pn.state.notifications.warning(
                    f"Preprocessed data is not compatible with this tab. Using raw data. Details: {e}",
                    duration=6000,
                ) # type: ignore
            return False

        return True

    def _resolve_plot_dataset(self, use_preprocessed: bool):
        """Return raw or preprocessed dataset according to switch state and availability."""
        app_state = CacheManager.get_cached_app_state()
        selected_idx = app_state.selected_tab_index_dataset
        raw_dataset = app_state.all_datasets[selected_idx]

        if use_preprocessed and self._has_valid_preprocessed_data(notify=True):
            return app_state.preprocessed_plot_dataset

        return raw_dataset

    def _has_compatible_clustering_data(self) -> bool:
        """Return whether a current clustering can be used with the active tab."""
        if not self._has_valid_preprocessed_data(notify=False):
            return False
        nlls_controller = getattr(self, "_nlls_controller", None)
        if nlls_controller is not None:
            return nlls_controller.has_current_clustering_data()
        app_state = CacheManager.get_cached_app_state()
        try:
            labels = app_state.last_clustering_result["clustering"]["outputs"]["labels"]
            raw = app_state.all_datasets[app_state.selected_tab_index_dataset]
            return getattr(labels, "ndim", 0) == 2 and tuple(labels.shape) == tuple(raw["ElectronCount"].shape[:2])
        except (KeyError, TypeError, AttributeError, IndexError):
            return False

    def _sync_data_source_controls(self, *, select_preprocessed: bool = False) -> None:
        """Refresh source availability and keep the selected source visibly active."""
        preprocessed_available = self._has_valid_preprocessed_data(notify=False)
        preprocessed_button = self._view.preprocessed_data_button
        clustering_button = self._view.clustering_data_button

        # The NLLS workspace is constructed against the active plot dataset.
        # Select the Home-preprocessed source first, then validate clustering
        # against that new workspace. Checking it before this transition left
        # Clustering Data permanently disabled on first page load.
        if select_preprocessed and preprocessed_available:
            self._activate_preprocessed_data(notify=False)

        preprocessed_available = self._has_valid_preprocessed_data(notify=False)
        clustering_available = self._has_compatible_clustering_data()
        preprocessed_button.disabled = not preprocessed_available
        clustering_button.disabled = not clustering_available

        if self._active_data_source == "clustering" and not clustering_available:
            self._activate_preprocessed_data(notify=False)
            return
        if self._active_data_source == "preprocessed" and not preprocessed_available:
            self._active_data_source = None

        preprocessed_button.button_type = (
            "primary" if self._active_data_source == "preprocessed" else "default"
        )
        clustering_button.button_type = (
            "primary" if self._active_data_source == "clustering" else "default"
        )

    def _on_preprocessed_dataset_changed(self, event) -> None:
        """React to Home preprocessing publication/clear while fitting page is already open."""
        self._sync_data_source_controls(select_preprocessed=True)
        if hasattr(self, '_nlls_controller'):
            self._nlls_controller.on_source_changed(initial=True)

    def _on_clustering_result_changed(self, event) -> None:
        """Enable Clustering Data only for a compatible current result."""
        self._sync_data_source_controls()
    
    def update_plot(self, fitting_results = None):
        """Proxy plot updates to layout manager."""
        self.layout.update_plot(fitting_results)

    def remove_component(self, component_item):
        """Remove a component from the model and update the plot if needed."""
        should_update = self._model.remove_component(component_item)
        if should_update:
            has_components = bool(self._model.dictionary.get('components'))
            fit_result = getattr(self._model, 'ref_results', None) if has_components else None
            self.update_plot(fit_result)

    def _on_preprocessed_data_selected(self, event):
        """Activate the Home-preprocessed ROI source."""
        self._activate_preprocessed_data(notify=True)

    def _on_clustering_data_selected(self, event):
        """Activate the current clustering, always based on preprocessed data."""
        if not self._has_compatible_clustering_data():
            return
        self._activate_preprocessed_data(notify=False)
        try:
            self._nlls_controller.select_clustering_data()
            workspace = self._nlls_controller.workspace
            if workspace is not None and workspace.clustering_active:
                self._active_data_source = "clustering"
        finally:
            self._sync_data_source_controls()

    def _activate_preprocessed_data(self, *, notify: bool) -> None:
        """Switch to Home-preprocessed data and reset derived fitting state once."""
        app_state = CacheManager.get_cached_app_state()

        if not self._has_valid_preprocessed_data(notify=notify):
            return

        already_selected = app_state.plot_dataset is app_state.preprocessed_plot_dataset
        app_state.plot_dataset = app_state.preprocessed_plot_dataset

        if not already_selected:
            # Source changed: clear components and all derived fit state.
            self._model.reset_for_data_source_change()
            self._layout.clear_component_inputs_from_sidebar()
            app_state.spectra = None
            self.energy_map_active = False
            self._view.energy_map_toggle_button.disabled = True
            self._view.fitting_add_component_button.disabled = True
            self.layout.reset_for_data_source_change()
            if hasattr(self, '_nlls_controller'):
                self._nlls_controller.on_source_changed()

        if hasattr(self, '_nlls_controller'):
            self._nlls_controller.select_preprocessed_data()
        self._active_data_source = "preprocessed"
        self._view.preprocessed_data_button.button_type = "primary"
        self._view.clustering_data_button.button_type = "default"

        if notify and not already_selected:
            pn.state.notifications.info(
                "Fitting input switched to Home preprocessed data. Existing components and fit results were reset.",
                duration=4000,
            ) # type: ignore

    def get_energy_range(self):
        """Return the active energy range only when energy-map mode is enabled."""
        if not self.energy_map_active:
            return None
        return self._layout.get_energy_range()
