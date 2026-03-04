"""
NLLS Controller

Coordinates Model and View for NLLS fitting operations.
Handles user interactions and manages the fitting workflow.
"""

from whateels.base.mvc import BaseController
from whateels.shared_state import get_cached_app_state
from whateels.helpers.logging import Logger

_logger = Logger.get_logger("nlls_controller.log", __name__)


class NLLSController(BaseController):
    """
    NLLS Controller class for managing NLLS fitting workflow.
    
    Coordinates between NLLSModel and NLLSView, handling user interactions
    and orchestrating the fitting process.
    """
    
    def __init__(self, model, view):
        super().__init__(model, view)
        
        self._model = model
        self._view = view
        self._app_state = get_cached_app_state()
        
        # Connect view widgets to controller methods
        self._connect_widgets()
        
        # Initialize the page
        self._initialize_page()
        
    def _connect_widgets(self):
        """Connect view widgets to controller callback methods"""
        self._view.add_element_button.on_click(self._on_add_element)
        self._view.create_model_button.on_click(self._on_create_model)
        self._view.fit_references_button.on_click(self._on_fit_references)
        self._view.multifit_button.on_click(self._on_multifit)
        self._view.element_selector.param.watch(self._on_element_changed, 'value')
    
    def _initialize_page(self):
        """Initialize the NLLS page on load"""
        # Check if dataset is available
        _logger.info(f"Initializing NLLS page, has_dataset: {self._model.has_dataset}")
        
        if not self._model.has_dataset:
            self.base_layout.empty_main()
            self._view.update_status(
                'No dataset loaded. Please load a dataset from the Home page.',
                'warning'
            )
            _logger.warning("No dataset available in AppState")
            return
        
        # Initialize model from dataset
        if self._model.initialize_from_dataset():
            self._view.update_status(
                f'Dataset loaded: {self._model._im_type} type. Select elements to begin fitting.',
                'success'
            )
            
            # Populate element selector
            elements = self._model.get_available_elements()
            self._view.element_selector.options = elements
            if elements:
                self._view.element_selector.value = elements[0]
            
            # Update main layout
            self.base_layout.update_main(self._view.build_main_content())
            
            _logger.info("NLLS page initialized successfully")
        else:
            self.base_layout.error_main()
            self._view.update_status(
                'Failed to initialize from dataset. Check dataset format.',
                'error'
            )
            _logger.error("Failed to initialize model from dataset")
    
    def _on_element_changed(self, event):
        """Handle element selection change"""
        element = event.new
        if element:
            # Update subshell options
            subshells = self._model.get_subshells_for_element(element)
            self._view.subshell_selector.options = subshells
            self._view.subshell_selector.value = []
            _logger.debug(f"Element changed to {element}, subshells: {subshells}")
    
    def _on_add_element(self, event):
        """Handle add element button click"""
        element = self._view.element_selector.value
        subshells = self._view.subshell_selector.value
        
        print(f"NLLS: Adding element {element} with subshells {subshells}")
        
        if not element:
            self._view.update_status('Please select an element.', 'warning')
            return
        
        if not subshells:
            self._view.update_status('Please select at least one subshell.', 'warning')
            return
        
        # Add element to model
        self._model.add_element(element, subshells)
        
        # Update selected elements display using the new method
        self._view.update_selected_elements_display(self._model.fitting_elements)
        
        print(f"NLLS: Element added. Total elements: {list(self._model.fitting_elements.keys())}")
        
        self._view.update_status(
            f'Added {element} with subshells: {", ".join(subshells)}',
            'success'
        )
        _logger.info(f"Added element {element} with subshells {subshells}")
    
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
    
    def _on_fit_references(self, event):
        """Handle fit references button click"""
        self._view.fit_references_button.disabled = True
        self._view.update_status('Fitting reference spectra...', 'info')
        self._view.show_progress(0, 100)
        
        try:
            # Fit the reference spectrum
            self._model.fit_reference(name_area='default')
            
            self._view.show_progress(100, 100)
            self._view.update_status('Reference fitting complete! You can now run multifit.', 'success')
            
            # Enable multifit button
            self._view.multifit_button.disabled = False
            
            _logger.info("Reference fitting completed")
        except Exception as e:
            self._view.update_status(f'Error fitting references: {str(e)}', 'error')
            _logger.error(f"Reference fitting failed: {e}", exc_info=True)
        finally:
            self._view.fit_references_button.disabled = False
            self._view.hide_progress()
    
    def _on_multifit(self, event):
        """Handle multifit button click"""
        self._view.multifit_button.disabled = True
        self._view.update_status('Running multifit across dataset...', 'info')
        self._view.show_progress(0, 100)
        
        try:
            # Define progress callback
            def update_progress(current, total):
                progress = int((current / total) * 100)
                self._view.show_progress(progress, 100)
                if current % 10 == 0:  # Update status every 10 pixels
                    self._view.update_status(
                        f'Fitting pixels: {current}/{total} ({progress}%)',
                        'info'
                    )
            
            # Run multifit with progress updates
            self._model.multifit_area(name_area='default', progress_callback=update_progress)
            
            self._view.show_progress(100, 100)
            self._view.update_status('Multifit complete! Extracting results...', 'success')
            
            # Extract and display results
            print("NLLS Controller: Extracting results...")
            element_maps = self._model.get_element_maps(name_area='default')
            chi2_map = self._model.get_fit_quality_map(name_area='default')
            eloss, ref_spectrum, ref_fit = self._model.get_reference_fit(name_area='default')
            
            print(f"  - Element maps: {list(element_maps.keys())}")
            print(f"  - Chi2 map shape: {chi2_map.shape if chi2_map is not None else None}")
            print(f"  - Reference fit available: {ref_fit is not None}")
            
            # Display results in view
            self._view.display_results(element_maps, chi2_map, eloss, ref_spectrum, ref_fit)
            self._view.update_status('Results displayed! Scroll down to see maps and plots.', 'success')
            
            _logger.info("Multifit completed and results displayed")
        except Exception as e:
            self._view.update_status(f'Error during multifit: {str(e)}', 'error')
            _logger.error(f"Multifit failed: {e}", exc_info=True)
        finally:
            self._view.multifit_button.disabled = False
            self._view.hide_progress()