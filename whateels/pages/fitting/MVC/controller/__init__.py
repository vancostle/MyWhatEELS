from .managers import LayoutManager
from whateels.shared_state import AppState
from whateels.base.mvc.base_controller import BaseController
from .services.oos_loader_service import Loader_OOS
from xarray import Dataset
from whateels.helpers.constants import OOS_ROOT
from whateels.helpers.safe_converter import SafeConverter
from ..model.element_item import ElementItem
from ..model.component_item import ComponentItem
from ..view.components.element_item_view import ElementItemView
from ..view.components.component_item_view import ComponentItemView

import panel as pn

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..model import FittingModel
    from ..view import FittingView


class FittingController(BaseController):
    ELEMENT_EAXIS_THRESHOLD = 50

    def __init__(self, model: "FittingModel", view: "FittingView"):
        print("Initializing Fitting Controller...")
        
        super().__init__(model, view)

        self._model = model
        self._view = view

        self._layout = LayoutManager(view, self, model)

        all_datasets = AppState().all_datasets

        self.loader_oos = Loader_OOS(dir_path = str(OOS_ROOT / "Hartree_Xsections_FSalvat"))
        view.set_controller(self)
        model.set_controller(self)
        print("Loader_OOS initialized.")
        
        # Get 'tab' query parameter from URL
        tab_param = self._get_query_param("tab")
        # Convert to integer with default -1
        tab_param = SafeConverter.to_int(tab_param, default=-1) # -1 indicates invalid index in this context
        
        # Validate datasets and tab index, es queda aqui
        if not (isinstance(all_datasets, list) and all_datasets and 0 <= tab_param < len(all_datasets)):
            print(tab_param, len(all_datasets))
            self.base_layout.empty_main()
            return
        print("Datasets and tab parameter validated.")
        
        self._layout.create_tab_and_dataset_info([all_datasets[tab_param]])
        print("Tab and dataset info created.")
        self._nlls_user_update(view)
        print("NLLS Controller initialized.")

    @property
    def view(self) -> "FittingView":
        """Access the ClusteringView instance."""
        return self._view
    @property
    def layout(self) -> LayoutManager:
        """Access the LayoutManager instance."""
        return self._layout

    def _nlls_user_update(self, view: "FittingView"):
        """Debug method to print the Nlls input widgets."""
        print("NLLS User Update Called")
        view.component_input["energy_center"].param.watch(self._energy_center_watcher, 'value')
        view.component_input["model_select"].param.watch(self._model_select_watcher, 'value')

        view._fitting_add_compontent_button.on_click(self._add_component_item_button_callback)

        view._background_subtraction_switch.param.watch(self._background_subtraction_switch_watcher, 'value')

    def _energy_center_watcher(self, event):
        energy_center = self.view.component_input["energy_center"]

    def _model_select_watcher(self, event):
        model_select = self.view.component_input["model_select"]
        self.view.fitting_add_component_button.disabled = False


    def _add_component_item_button_callback(self, event):
        # crear lelement del component del model
        energy_center = self.view.component_input["energy_center"].value
        model_select = self.view.component_input["model_select"].value

        component_item = ComponentItem(energy_center, model_select)
        component_item_view = ComponentItemView(self, component_item, self.model, (self._layout.get_energy_range()[0], self._layout.get_energy_range()[-1]), self.view)

        #self._layout.add_new_component_input(component_item_view) # modificar aquesta funcio per que els components
        print("Element added programmatically.")
        self._model.add_component(model_select, energy_center)

    def _test(self, event):
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
    
    def update_plot(self, fitting_results):
        self.layout.update_plot(fitting_results)

    def _background_subtraction_switch_watcher(self, event):
        AppState().is_multifit = event.new
    
    def _run_model_nlls_fitting(self):
        """Trigger the NLLS fitting process in the model."""

        # Step 1: Calculate GOS curves for selected elements pq ja esta a quanti
        """
        self._view.update_status('Calculating GOS surfaces and curves...', 'info')
        self._view.show_progress(20, 100)
        
        self._model.ready_elements(
            type_surface='F-factor',  # Use F-factor corrected surfaces
            extension=True,
            max_Eloss=3000,
            mesh_p=250
        )
        
        self._view.show_progress(50, 100)
        self._view.update_status('Creating model components...', 'info')
        """
        
        # Step 2: Get reference spectrum (middle third of dataset)
        ds = self._model.dataset
        if self._model._im_type == 'single':
            ref_spectrum = ds.ElectronCount.values
        elif self._model._im_type == 'SLine':
            # Use middle third of line
            if ds.x.size == 1:
                sli0 = int(ds.y.size / 3)
                sli1 = int(2 * ds.y.size / 3)
                ref_spectrum = ds.isel(x=0, y=slice(sli0, sli1)).sum('y').ElectronCount.values / (sli1 - sli0)
            else:
                sli0 = int(ds.x.size / 3)
                sli1 = int(2 * ds.x.size / 3)
                ref_spectrum = ds.isel(y=0, x=slice(sli0, sli1)).sum('x').ElectronCount.values / (sli1 - sli0)
        else:  # SImage
            # Use middle region
            xlen, ylen = ds.x.size, ds.y.size
            slix0, slix1 = int(2 * xlen / 5), int(3 * xlen / 5)
            sliy0, sliy1 = int(2 * ylen / 5), int(3 * ylen / 5)
            ref_spectrum = ds.sel(x=slice(slix0, slix1), y=slice(sliy0, sliy1)).sum(
                dim=['x', 'y']
            ).ElectronCount.values / ((slix1 - slix0) * (sliy1 - sliy0))
        
        # Step 3: Create components (continuum + ELNES)
        self._model.create_components(
            spectrum=ref_spectrum,
            default_compo_type='gaussian',
            flex='medium',
            name_area='default',
            excluded_elements=[],
            soften=False,
            soften_val=None
        )
        
        self._view.update_status('Building composite model...', 'info')
        
        # Step 4: Create composite lmfit model
        dataset = self._layout.get_active_dataset()
        self._model.create_model(dataset = dataset, name_area='default', flex='medium')

    def _on_create_model(self, event):
        """Handle create model button click"""
        print("=" * 80)
        print("NLLS: Create Model button clicked")
        print("=" * 80)
        
        self._view.create_model_button.disabled = True
        self._view.update_status('Creating model components...', 'info')
        self._view.show_progress(10, 100)
        
        try:
            # Ensure dataset is initialized
            print(f"NLLS: Checking dataset status...")
            print(f"  - has_dataset: {self._model.has_dataset}")
            print(f"  - _exp_param: {self._model._exp_param}")
            print(f"  - AppState.plot_dataset: {self._app_state.plot_dataset}")
            print(f"  - AppState.all_datasets length: {len(self._app_state.all_datasets) if self._app_state.all_datasets else 0}")
            
            _logger.info(f"Create model: has_dataset={self._model.has_dataset}, _exp_param={self._model._exp_param}")
            
            if not self._model.has_dataset or self._model._exp_param is None:
                print("NLLS: Dataset not initialized, attempting to initialize...")
                _logger.info("Dataset not initialized, attempting to initialize from AppState")
                
                if not self._model.initialize_from_dataset():
                    print("NLLS: ERROR - Failed to initialize dataset from AppState")
                    self._view.update_status(
                        'No dataset loaded. Please load a dataset from the Home page.',
                        'error'
                    )
                    self._view.create_model_button.disabled = False
                    self._view.hide_progress()
                    _logger.error("Failed to initialize dataset")
                    return
                
                print(f"NLLS: Dataset initialized successfully!")
                print(f"  - _exp_param: {self._model._exp_param}")
                print(f"  - _im_type: {self._model._im_type}")
                _logger.info(f"Dataset initialized successfully, _exp_param={self._model._exp_param}")
            
            print(f"NLLS: Starting GOS calculations for elements: {list(self._model.fitting_elements.keys())}")
            
            # Step 1: Calculate GOS curves for selected elements
            self._view.update_status('Calculating GOS surfaces and curves...', 'info')
            self._view.show_progress(20, 100)
            
            self._model.ready_elements(
                type_surface='F-factor',  # Use F-factor corrected surfaces
                extension=True,
                max_Eloss=3000,
                mesh_p=250
            )
            
            self._view.show_progress(50, 100)
            self._view.update_status('Creating model components...', 'info')
            
            # Step 2: Get reference spectrum (middle third of dataset)
            ds = self._model.dataset
            if self._model._im_type == 'single':
                ref_spectrum = ds.ElectronCount.values
            elif self._model._im_type == 'SLine':
                # Use middle third of line
                if ds.x.size == 1:
                    sli0 = int(ds.y.size / 3)
                    sli1 = int(2 * ds.y.size / 3)
                    ref_spectrum = ds.isel(x=0, y=slice(sli0, sli1)).sum('y').ElectronCount.values / (sli1 - sli0)
                else:
                    sli0 = int(ds.x.size / 3)
                    sli1 = int(2 * ds.x.size / 3)
                    ref_spectrum = ds.isel(y=0, x=slice(sli0, sli1)).sum('x').ElectronCount.values / (sli1 - sli0)
            else:  # SImage
                # Use middle region
                xlen, ylen = ds.x.size, ds.y.size
                slix0, slix1 = int(2 * xlen / 5), int(3 * xlen / 5)
                sliy0, sliy1 = int(2 * ylen / 5), int(3 * ylen / 5)
                ref_spectrum = ds.sel(x=slice(slix0, slix1), y=slice(sliy0, sliy1)).sum(
                    dim=['x', 'y']
                ).ElectronCount.values / ((slix1 - slix0) * (sliy1 - sliy0))
            
            self._view.show_progress(60, 100)
            
            # Step 3: Create components (continuum + ELNES)
            self._model.create_components(
                spectrum=ref_spectrum,
                default_compo_type='gaussian',
                flex='medium',
                name_area='default',
                excluded_elements=[],
                soften=False,
                soften_val=None
            )
            
            self._view.show_progress(80, 100)
            self._view.update_status('Building composite model...', 'info')
            
            # Step 4: Create composite lmfit model
            self._model.create_model(name_area='default', flex='medium')
            
            self._view.show_progress(100, 100)
            self._view.update_status(
                f'Model ready for {len(self._model.fitting_elements)} elements. '
                'You can now fit reference spectra.',
                'success'
            )
            
            # Enable fitting buttons
            self._view.fit_references_button.disabled = False
            
            _logger.info("Model creation completed successfully")
        except Exception as e:
            import traceback
            error_details = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            print(f"\n{'='*80}")
            print(f"NLLS Controller: Exception caught in _on_create_model:")
            print(f"{'='*80}")
            print(error_details)
            print(f"{'='*80}\n")
            
            error_msg = f'Error creating model: {type(e).__name__}: {str(e)}'
            self._view.update_status(error_msg, 'error')
            _logger.error(f"Model creation failed: {e}", exc_info=True)
        finally:
            self._view.create_model_button.disabled = False
            self._view.hide_progress()