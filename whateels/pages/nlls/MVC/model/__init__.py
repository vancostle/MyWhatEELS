"""
NLLS Model

Handles NLLS (Non-Linear Least Squares) fitting logic adapted from the legacy
nlls_functions.py. This model manages GOS calculations, element/subshell selection,
model creation, and fitting operations.
"""

from whateels.base.mvc import BaseModel
from whateels.state import CacheManager
from whateels.helpers.logging import Logger
import numpy as np
import copy as cp
from scipy.interpolate import InterpolatedUnivariateSpline

# Import from relocated Library modules
from whateels.helpers.nlls_library.database.elements import elements
from whateels.helpers.nlls_library.cross_sections import bethe_surface

_logger = Logger.get_logger("nlls_model.log", __name__)


class NLLSModel(BaseModel):
    """
    NLLS Model class for managing fitting operations.
    
    This is a simplified adaptation of the NLLS_fitting class from nlls_functions.py,
    integrated with the WhatEELS application architecture.
    """
    
    def __init__(self):
        super().__init__()
        
        # Access shared application state
        self._app_state = CacheManager.get_cached_app_state()
        
        # NLLS fitting state
        self._fitting_elements = dict()  # Selected elements and subshells
        self._bethe = dict()  # GOS calculations per element
        self._gos_curves = dict()  # GOS curves for fitting
        self._scaling_factor = dict()  # Scaling factors for cross-sections
        self._models_components = dict()  # Model components per area
        self._models = dict()  # Composite models for fitting
        self._pars = dict()  # Parameters for fitting
        self._ref_spectra = dict()  # Reference spectra per area
        self._ref_matrices = dict()  # Position matrices per area
        self._ref_results = dict()  # Reference fitting results
        self._results = dict()  # Multifit results
        
        # Dataset properties
        self._ds = None
        self._Eloss = None
        self._spec = None
        self._exp_param = None  # [E0, beta, alpha]
        self._im_type = None  # 'single', 'SLine', 'SImage'
        
        _logger.info("NLLSModel initialized")
    
    @property
    def dataset(self):
        """Get the current dataset from AppState"""
        if self._ds is None:
            # Try plot_dataset first, then fall back to all_datasets[0]
            if self._app_state.plot_dataset is not None:
                self._ds = self._app_state.plot_dataset
            elif self._app_state.all_datasets and len(self._app_state.all_datasets) > 0:
                self._ds = self._app_state.all_datasets[0]
                print(f"NLLS Model: Using all_datasets[0] as dataset")
        return self._ds
    
    @property
    def fitting_elements(self):
        """Dictionary of selected elements and their subshells"""
        return self._fitting_elements
    
    @property
    def has_dataset(self):
        """Check if a valid dataset is available"""
        # Check plot_dataset first, then all_datasets
        ds = self._app_state.plot_dataset
        if ds is None and self._app_state.all_datasets and len(self._app_state.all_datasets) > 0:
            ds = self._app_state.all_datasets[0]
        
        _logger.debug(f"has_dataset check: dataset is {type(ds)}")
        return ds is not None
    
    def initialize_from_dataset(self):
        """
        Initialize the model from the current dataset in AppState.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        print("NLLS Model: initialize_from_dataset() called")
        
        # Try plot_dataset first, then fall back to all_datasets[0]
        ds = self._app_state.plot_dataset
        print(f"  - plot_dataset: {type(ds)}")
        
        if ds is None:
            print("  - plot_dataset is None, checking all_datasets...")
            if self._app_state.all_datasets and len(self._app_state.all_datasets) > 0:
                ds = self._app_state.all_datasets[0]
                print(f"  - Using all_datasets[0]: {type(ds)}")
            else:
                print("  - ERROR: all_datasets is also empty!")
        
        if ds is None:
            print("  - ERROR: No dataset available!")
            _logger.warning("No dataset available in AppState")
            return False
        
        try:
            # Store the dataset
            self._ds = ds
            print(f"  - Dataset stored, type: {type(self._ds)}")
            
            # Extract dataset properties
            self._Eloss = ds.Eloss.values
            self._spec = ds.ElectronCount.values
            print(f"  - Eloss shape: {self._Eloss.shape}")
            print(f"  - Spectrum shape: {self._spec.shape}")
            
            # Extract experimental parameters from metadata
            self._exp_param = [
                ds.attrs.get('beam_energy', 200),  # keV
                ds.attrs.get('collection_angle', 10),  # mrad
                ds.attrs.get('convergence_angle', 10),  # mrad
            ]
            
            print(f"  - Experimental parameters extracted:")
            print(f"    * E0 (beam_energy): {self._exp_param[0]} keV")
            print(f"    * beta (collection_angle): {self._exp_param[1]} mrad")
            print(f"    * alpha (convergence_angle): {self._exp_param[2]} mrad")
            
            _logger.info(f"Extracted experimental parameters: E0={self._exp_param[0]} keV, "
                        f"beta={self._exp_param[1]} mrad, alpha={self._exp_param[2]} mrad")
            
            # Determine image type
            xlen = ds.x.values.size
            ylen = ds.y.values.size
            
            if xlen == ylen == 1:
                self._im_type = 'single'
            elif xlen != ylen and any([i == 1 for i in [xlen, ylen]]):
                self._im_type = 'SLine'
            else:
                self._im_type = 'SImage'
            
            print(f"  - Image type: {self._im_type} (x={xlen}, y={ylen})")
            print("  - Initialization SUCCESS!")
            
            _logger.info(f"Model initialized with {self._im_type} dataset, shape: x={xlen}, y={ylen}")
            return True
            
        except Exception as e:
            print(f"  - ERROR during initialization: {e}")
            import traceback
            traceback.print_exc()
            _logger.error(f"Failed to initialize from dataset: {e}", exc_info=True)
            return False
    
    def add_element(self, element: str, subshells: list):
        """
        Add an element with selected subshells to the fitting model.
        
        Args:
            element: Element symbol (e.g., 'Ce', 'Fe')
            subshells: List of subshell identifiers (e.g., ['M54', 'M32'])
                      Can include paired labels like 'L32' which will be expanded to ['L3', 'L2']
        """
        # Expand paired subshell labels (e.g., 'L32' -> ['L3', 'L2'])
        expanded_subshells = []
        for ssh in subshells:
            if len(ssh) == 3 and ssh[-2:] in ['54', '32']:
                # Paired subshell label (e.g., 'M54', 'L32')
                shell = ssh[0]  # e.g., 'M', 'L'
                if ssh[-2:] == '54':
                    expanded_subshells.extend([f'{shell}5', f'{shell}4'])
                else:  # '32'
                    expanded_subshells.extend([f'{shell}3', f'{shell}2'])
            else:
                # Single subshell (e.g., 'K', 'L1')
                expanded_subshells.append(ssh)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_subshells = []
        for ssh in expanded_subshells:
            if ssh not in seen:
                seen.add(ssh)
                unique_subshells.append(ssh)
        
        self._fitting_elements[element] = {'subshells': unique_subshells}
        print(f"NLLS Model: Added element {element}")
        print(f"  - Input subshells: {subshells}")
        print(f"  - Expanded to: {unique_subshells}")
        _logger.info(f"Added element {element} with subshells {unique_subshells}")
    
    def get_available_elements(self):
        """
        Get list of available elements from the database.
        
        Returns:
            list: Sorted list of element symbols
        """
        return sorted(elements.keys())
    
    def get_subshells_for_element(self, element: str):
        """
        Get available subshells for a given element.
        
        Args:
            element: Element symbol
            
        Returns:
            list: List of available subshell identifiers
        """
        if element not in elements:
            return []
        
        atomic_props = elements[element].get('Atomic_properties', {})
        binding_energies = atomic_props.get('Binding_energies', {})
        return sorted(binding_energies.keys()) if binding_energies else []
    
    def get_available_elements(self):
        """
        Get list of elements available for fitting.
        
        Returns:
            list: Sorted list of element symbols
        """
        # Use the relocated elements database
        available = sorted([el for el in elements.keys() 
                          if 'Atomic_properties' in elements[el] 
                          and 'Binding_energies' in elements[el]['Atomic_properties']])
        return available
    
    def get_subshells_for_element(self, element: str):
        """
        Get available subshells for a given element.
        
        Args:
            element: Element symbol
            
        Returns:
            list: List of available subshell identifiers
        """
        if element not in elements:
            _logger.warning(f"Element {element} not in database")
            return []
        
        binding_energies = elements[element]['Atomic_properties']['Binding_energies']
        subshells = []
        
        for ssh in binding_energies:
            if ssh[-1] == '5':
                subshells.append('{}54'.format(ssh[0]))
            elif ssh[-1] == '3':
                subshells.append('{}32'.format(ssh[0]))
            elif ssh[-1] not in ['2', '4']:
                subshells.append(ssh)
        
        return subshells
    
    def clear_fitting_elements(self):
        """Clear all selected elements and reset the model"""
        self._fitting_elements.clear()
        self._models_components.clear()
        self._models.clear()
        _logger.info("Cleared all fitting elements")
    
    def ready_elements(self, type_surface='theoretical', extension=True, max_Eloss=3000, mesh_p=250):
        """
        Calculate GOS curves for all selected elements and subshells.
        
        This method performs the core Bethe surface calculations and generates
        the GOS curves used for fitting. Adapted from nlls_functions.py.
        
        Args:
            type_surface: Type of surface ('theoretical', 'beta-cut', or 'F-factor')
            extension: Whether to extend curves with powerlaw extrapolation
            max_Eloss: Maximum energy loss for extrapolation (eV)
            mesh_p: Number of mesh points for surface interpolation
        """
        from lmfit.models import PowerLawModel
        
        print(f"NLLS Model: ready_elements() called")
        print(f"  - Elements to process: {list(self._fitting_elements.keys())}")
        print(f"  - type_surface: {type_surface}")
        print(f"  - extension: {extension}")
        print(f"  - _exp_param: {self._exp_param}")
        
        pwlaw_A = 1  # Powerlaw amplitude for extension
        pwlaw_exp = -2  # Powerlaw exponent for extension  
        fromonset = 100  # Distance from onset to start powerlaw (eV)
        
        for element, elem_data in self._fitting_elements.items():
            print(f"NLLS Model: Processing element {element}...")
            
            # Get subshells list from the dictionary structure
            element_subshells = elem_data['subshells']
            print(f"  - Subshells: {element_subshells}")
            
            # Initialize bethe_surface calculator for this element
            print(f"  - Creating bethe_surface calculator...")
            bethe_calc = bethe_surface(element, verbose=False)
            
            # Get subshells to exclude (veto list)
            all_subshells = bethe_calc.subshells
            veto_list = [ssh for ssh in all_subshells 
                        if ssh not in element_subshells]
            print(f"  - Veto list: {veto_list}")
            
            # Run GOS curve calculations
            print(f"  - Running autorun_gosCurves (this may take 10-30 seconds)...")
            gos_arrays = bethe_calc.autorun_gosCurves(
                exp_param=self._exp_param,
                veto_sshell_list=veto_list,
                Erange=100,
                surfaceTOuse=type_surface,
                ret_gos_curve=True,
                mesh_p=mesh_p
            )
            print(f"  - GOS curves calculated, keys: {list(gos_arrays.keys()) if gos_arrays else 'None'}")
            
            # Store GOS curves and scaling factors
            self._gos_curves[element] = dict()
            self._scaling_factor[element] = dict()
            self._bethe[element] = bethe_calc
            
            for sshell in element_subshells:
                key = f'{element}_{sshell}'
                
                # Optional extrapolation with powerlaw
                if extension and key in gos_arrays:
                    step_E = (gos_arrays[key]['Eax'][1] - 
                             gos_arrays[key]['Eax'][0])
                    E_bckg_0 = gos_arrays[key]['Eax'][-1] - 50
                    
                    if E_bckg_0 < gos_arrays[key]['Eax'][0] + fromonset:
                        E_bckg_0 = gos_arrays[key]['Eax'][0] + fromonset
                    
                    idx = np.searchsorted(gos_arrays[key]['Eax'], E_bckg_0)
                    
                    # Fit powerlaw to tail
                    mod = PowerLawModel()
                    pars = mod.make_params(amplitude=pwlaw_A, exponent=pwlaw_exp)
                    pars['exponent'].min = -3
                    pars['exponent'].max = -1.5
                    
                    mod_res = mod.fit(
                        gos_arrays[key]['gos'][idx:],
                        params=pars,
                        x=gos_arrays[key]['Eax'][idx:]
                    )
                    
                    # Extend arrays
                    extra_E = np.arange(
                        gos_arrays[key]['Eax'][idx+1],
                        max_Eloss,
                        step_E
                    )
                    
                    gos_arrays[key]['gos'] = np.append(
                        gos_arrays[key]['gos'][:idx],
                        mod_res.eval(x=extra_E)
                    )
                    gos_arrays[key]['Eax'] = np.append(
                        gos_arrays[key]['Eax'][:idx],
                        extra_E
                    )
                
                # Create interpolated spline for GOS curve
                if key in gos_arrays:
                    self._gos_curves[element][sshell] = InterpolatedUnivariateSpline(
                        gos_arrays[key]['Eax'],
                        gos_arrays[key]['gos'],
                        k=3,
                        ext=1
                    )
                    
                    # Store scaling factor
                    self._scaling_factor[element][sshell] = (
                        bethe_calc.factor_subshell.get(key, 1.0)
                    )
                    
                    _logger.info(f"Prepared GOS curve for {element}-{sshell}")
        
        _logger.info(f"Ready elements calculation complete for {len(self._fitting_elements)} elements")
    
    def create_components(self, spectrum, default_compo_type='gaussian', 
                         flex='medium', name_area='default', excluded_elements=None,
                         soften=None, soften_val=None):
        """
        Create model components (continuum + ELNES) for fitting.
        
        Args:
            spectrum: Reference spectrum for component initialization
            default_compo_type: Type of ELNES component ('gaussian', 'lorentzian', etc.)
            flex: Constraint flexibility ('low', 'medium', 'high', 'maximum')
            name_area: Label for this model area
            excluded_elements: Elements to exclude from this area
            soften: Whether to apply Gaussian smoothing to cross-sections
            soften_val: Sigma value for Gaussian filter
        """
        from lmfit.models import GaussianModel, LorentzianModel, PseudoVoigtModel, SplitLorentzianModel
        from scipy.ndimage import gaussian_filter1d
        
        print(f"NLLS Model: create_components() called for area '{name_area}'")
        print(f"  - Elements to fit: {list(self._fitting_elements.keys())}")
        print(f"  - Excluded elements: {excluded_elements}")
        print(f"  - Spectrum shape: {spectrum.shape}")
        
        if excluded_elements is None:
            excluded_elements = []
        
        self._models_components[name_area] = dict()
        self._ref_spectra[name_area] = cp.deepcopy(spectrum)
        dictionary = self._models_components[name_area]
        
        print(f"NLLS Model: Creating continuum components...")
        # Create continuum components (GOS-based)
        self._create_continuum_components(dictionary, excluded_elements, soften, soften_val)
        
        print(f"NLLS Model: Adding ELNES components...")
        # Add ELNES (white line) components
        self._add_ELNES(spectrum, dictionary, default_compo_type, flex, excluded_elements)
        
        # Add reference matrix for default area
        if name_area == 'default':
            ref = np.ones(self._ds.ElectronCount.values.shape[:-1])
            self._ref_matrices[name_area] = ref
        
        print(f"NLLS Model: Components created successfully for area '{name_area}'")
        
        _logger.info(f"Created components for area '{name_area}'")
    
    def _create_continuum_components(self, dictionary, excluded_elements, soften, soften_val):
        """Create GOS-based continuum components"""
        from scipy.ndimage import gaussian_filter1d
        
        dictio_data_soft = dict()
        dob_sshells = ['L', 'M', 'N', 'O']
        sin_sshells = ['K']
        el_lista = [el for el in self._fitting_elements.keys() if el not in excluded_elements]
        
        for el in el_lista:
            dictionary[el] = dict()
            dictionary[el]['continuum'] = dict()
            dictionary[el]['continuum_init_const'] = dict()
            
            # Get subshells list from dictionary structure
            element_subshells = self._fitting_elements[el]['subshells']
            
            for ssh in element_subshells:
                func = None
                
                # Paired subshells (M54, M32, etc.)
                if ssh[0] in dob_sshells and ssh[-1] == '5':
                    clav = ''.join([ssh[0], '54'])
                    ssh2 = ''.join([ssh[0], '4'])
                    
                    if soften and soften_val:
                        # Apply Gaussian smoothing
                        data_c = (self._gos_curves[el][ssh](self._Eloss) * self._scaling_factor[el][ssh] +
                                 self._gos_curves[el][ssh2](self._Eloss) * self._scaling_factor[el][ssh2])
                        sigma = 4 * soften_val / np.sqrt(np.log(256))
                        dat = gaussian_filter1d(data_c, sigma=sigma)
                        
                        if el not in dictio_data_soft:
                            dictio_data_soft[el] = dict()
                        dictio_data_soft[el][clav] = InterpolatedUnivariateSpline(self._Eloss, dat)
                        # Capture variables in closure
                        _el, _clav = el, clav
                        _interp = dictio_data_soft[_el][_clav]
                        func = lambda x, A=1, chem=0: A * _interp(x + chem)
                    else:
                        # Capture variables in closure
                        _el, _ssh, _ssh2 = el, ssh, ssh2
                        _gos1 = self._gos_curves[_el][_ssh]
                        _gos2 = self._gos_curves[_el][_ssh2]
                        _scale1 = self._scaling_factor[_el][_ssh]
                        _scale2 = self._scaling_factor[_el][_ssh2]
                        func = lambda x, A=1, chem=0: A * (
                            _gos1(x + chem) * _scale1 + _gos2(x + chem) * _scale2
                        )
                    
                    dictionary[el]['continuum'][clav] = cp.deepcopy(func)
                    
                elif ssh[0] in dob_sshells and ssh[-1] == '3':
                    clav = ''.join([ssh[0], '32'])
                    ssh2 = ''.join([ssh[0], '2'])
                    
                    if soften and soften_val:
                        data_c = (self._gos_curves[el][ssh](self._Eloss) * self._scaling_factor[el][ssh] +
                                 self._gos_curves[el][ssh2](self._Eloss) * self._scaling_factor[el][ssh2])
                        sigma = 4 * soften_val / np.sqrt(np.log(256))
                        dat = gaussian_filter1d(data_c, sigma=sigma)
                        
                        if el not in dictio_data_soft:
                            dictio_data_soft[el] = dict()
                        dictio_data_soft[el][clav] = InterpolatedUnivariateSpline(self._Eloss, dat)
                        # Capture variables in closure
                        _el, _clav = el, clav
                        _interp = dictio_data_soft[_el][_clav]
                        func = lambda x, A=1, chem=0: A * _interp(x + chem)
                    else:
                        # Capture variables in closure
                        _el, _ssh, _ssh2 = el, ssh, ssh2
                        _gos1 = self._gos_curves[_el][_ssh]
                        _gos2 = self._gos_curves[_el][_ssh2]
                        _scale1 = self._scaling_factor[_el][_ssh]
                        _scale2 = self._scaling_factor[_el][_ssh2]
                        func = lambda x, A=1, chem=0: A * (
                            _gos1(x + chem) * _scale1 + _gos2(x + chem) * _scale2
                        )
                    
                    dictionary[el]['continuum'][clav] = cp.deepcopy(func)
                
                # Single subshells (K, L1)
                elif ssh[0] in sin_sshells or (ssh[0] in dob_sshells and ssh[-1] == '1'):
                    clav = ssh
                    
                    if soften and soften_val:
                        data_c = self._gos_curves[el][ssh](self._Eloss) * self._scaling_factor[el][ssh]
                        sigma = 4 * soften_val / np.sqrt(np.log(256))
                        dat = gaussian_filter1d(data_c, sigma=sigma)
                        
                        if el not in dictio_data_soft:
                            dictio_data_soft[el] = dict()
                        dictio_data_soft[el][clav] = InterpolatedUnivariateSpline(self._Eloss, dat)
                        # Capture variables in closure
                        _el, _clav = el, clav
                        _interp = dictio_data_soft[_el][_clav]
                        func = lambda x, A=1, chem=0: A * _interp(x + chem)
                    else:
                        # Capture variables in closure
                        _el, _ssh = el, ssh
                        _gos = self._gos_curves[_el][_ssh]
                        _scale = self._scaling_factor[_el][_ssh]
                        func = lambda x, A=1, chem=0: A * _gos(x + chem) * _scale
                    
                    dictionary[el]['continuum'][clav] = cp.deepcopy(func)
            
            # Set initial constraints for continuum
            for subsh in dictionary[el]['continuum']:
                dictionary[el]['continuum_init_const'][subsh] = {
                    'A': 1.0,
                    'A_min': 0.0,
                    'vary_A': True,
                    'chem': 0.0,
                    'allow_chem': False
                }
    
    def _add_ELNES(self, spectrum, dictionary, default_compotype, flex, excluded_elements):
        """Add ELNES (white line) components"""
        dob_sshells = ['L', 'M', 'N', 'O']
        
        # Flexibility constraints
        dict_var = {
            'low': [3, 3, 0.1, 0.1],
            'medium': [7, 7, 1, 1.25],
            'high': [15, 15, 1, 3],
            'maximum': [np.inf, np.inf, 1, np.inf]
        }
        
        if flex not in dict_var:
            flex = 'medium'
        
        lista_el = [el for el in self._fitting_elements if el not in excluded_elements]
        
        for el in lista_el:
            dictionary[el]['ELNES'] = dict()
            dictionary[el]['ELNES_init_const'] = dict()
            
            # Get subshells list from dictionary structure
            element_subshells = self._fitting_elements[el]['subshells']
            
            for ssh in element_subshells:
                # Only add ELNES for paired subshells (potential white lines)
                if ssh[0] in dob_sshells and ssh[-1] != '1':
                    center = self._gos_curves[el][ssh].get_knots()[0]
                    
                    # Determine component parameters
                    cen, sigm, amp = self._determine_compo_parameters(
                        spectrum, default_compotype, center
                    )
                    
                    dictionary[el]['ELNES'][ssh] = {
                        'type_compo': default_compotype,
                        'center': cen,
                        'sigma': sigm,
                        'amplitude': amp
                    }
                    
                    # Set constraints
                    dictionary[el]['ELNES_init_const'][ssh] = {
                        'center_min': cen - dict_var[flex][0],
                        'center_max': cen + dict_var[flex][1],
                        'sigma_min': 0.5,
                        'sigma_max': sigm + sigm * dict_var[flex][3],
                        'amplitude_min': 0,
                        'amplitude_max': np.inf
                    }
    
    def _determine_compo_parameters(self, spectrum, tipo, center):
        """Determine initial parameters for ELNES components"""
        # Find index closest to center energy
        idx = np.searchsorted(self._Eloss, center)
        
        # Estimate amplitude from spectrum value
        if idx < len(spectrum):
            amp = spectrum[idx] * 0.1  # Start with 10% of signal
        else:
            amp = np.max(spectrum) * 0.1
        
        # Estimate sigma (width)
        sigm = 5.0  # Default 5 eV width
        
        return center, sigm, amp
    
    def create_model(self, name_area='default', flex='medium'):
        """
        Create composite lmfit model from components.
        
        Args:
            name_area: Label for model area
            flex: Constraint flexibility
        """
        from lmfit import Model
        from lmfit.models import GaussianModel, LorentzianModel, PseudoVoigtModel, SplitLorentzianModel
        
        print(f"NLLS Model: create_model() called for area '{name_area}'")
        print(f"  - Available areas in _models_components: {list(self._models_components.keys())}")
        
        if name_area not in self._models_components:
            error_msg = f"No components found for area '{name_area}'. Available areas: {list(self._models_components.keys())}"
            print(f"NLLS Model ERROR: {error_msg}")
            _logger.error(error_msg)
            raise ValueError(error_msg)
        
        dictionary = self._models_components[name_area]
        print(f"  - Elements in dictionary: {list(dictionary.keys())}")
        
        mod_cont_list = []
        mod_elnes_list = []
        params_cont_list = []
        params_elnes_list = []
        
        # Build continuum components
        for el in dictionary:
            for subsh in dictionary[el]['continuum']:
                pref = f'{el}{subsh}_cont_'
                mod = Model(dictionary[el]['continuum'][subsh], prefix=pref, nan_policy='omit')
                pars = mod.make_params()
                
                # Set parameter values and constraints
                pars[f'{pref}A'].value = dictionary[el]['continuum_init_const'][subsh]['A']
                pars[f'{pref}A'].min = dictionary[el]['continuum_init_const'][subsh]['A_min']
                pars[f'{pref}A'].vary = dictionary[el]['continuum_init_const'][subsh]['vary_A']
                pars[f'{pref}chem'].value = dictionary[el]['continuum_init_const'][subsh]['chem']
                pars[f'{pref}chem'].vary = dictionary[el]['continuum_init_const'][subsh]['allow_chem']
                
                mod_cont_list.append(mod)
                params_cont_list.append(pars)
            
            # Build ELNES components if they exist
            if 'ELNES' in dictionary[el]:
                for subsh in dictionary[el]['ELNES']:
                    tipo = dictionary[el]['ELNES'][subsh]['type_compo']
                    pref = f'{el}{subsh}_'
                    
                    # Select model type
                    if tipo == 'gaussian':
                        mod = GaussianModel(prefix=pref)
                    elif tipo == 'lorentzian':
                        mod = LorentzianModel(prefix=pref)
                    elif tipo == 'pseudovoigt':
                        mod = PseudoVoigtModel(prefix=pref)
                    elif tipo == 'splitlorentzian':
                        mod = SplitLorentzianModel(prefix=pref)
                    else:
                        mod = GaussianModel(prefix=pref)
                    
                    pars = mod.make_params()
                    
                    # Set parameter values and constraints
                    for key in ['center', 'sigma', 'amplitude']:
                        if key in dictionary[el]['ELNES'][subsh]:
                            pars[f'{pref}{key}'].value = dictionary[el]['ELNES'][subsh][key]
                            pars[f'{pref}{key}'].min = dictionary[el]['ELNES_init_const'][subsh][f'{key}_min']
                            pars[f'{pref}{key}'].max = dictionary[el]['ELNES_init_const'][subsh][f'{key}_max']
                    
                    mod_elnes_list.append(mod)
                    params_elnes_list.append(pars)
        
        # Create composite model
        if not mod_cont_list:
            _logger.error("No continuum components to create model")
            raise ValueError("No continuum components found")
        
        self._models[name_area] = mod_cont_list[0]
        for mod in mod_cont_list[1:]:
            self._models[name_area] += mod
        
        for mod in mod_elnes_list:
            self._models[name_area] += mod
        
        # Make parameters
        self._pars[name_area] = self._models[name_area].make_params()
        
        # Apply ELNES parameter values and constraints
        for pars in params_elnes_list:
            for par in pars:
                self._pars[name_area][par].value = pars[par].value
                self._pars[name_area][par].min = pars[par].min
                self._pars[name_area][par].max = pars[par].max
        
        # Apply continuum parameter values and constraints
        for pars in params_cont_list:
            for par in pars:
                self._pars[name_area][par].value = pars[par].value
                self._pars[name_area][par].min = pars[par].min
                self._pars[name_area][par].max = pars[par].max
                self._pars[name_area][par].vary = pars[par].vary
        
        _logger.info(f"Created composite model for area '{name_area}'")
    
    def fit_reference(self, name_area='default'):
        """
        Fit the reference spectrum for a given area.
        
        Args:
            name_area: Label for reference area
        """
        print(f"NLLS Model: fit_reference() called for area '{name_area}'")
        print(f"  - Available areas in _ref_spectra: {list(self._ref_spectra.keys())}")
        print(f"  - Available areas in _models: {list(self._models.keys())}")
        print(f"  - Available areas in _pars: {list(self._pars.keys())}")
        
        if name_area not in self._ref_spectra:
            error_msg = f"Missing reference spectrum for area '{name_area}'"
            print(f"NLLS Model ERROR: {error_msg}")
            _logger.error(error_msg)
            raise ValueError(error_msg)
        
        if name_area not in self._models:
            error_msg = f"Missing model for area '{name_area}'"
            print(f"NLLS Model ERROR: {error_msg}")
            _logger.error(error_msg)
            raise ValueError(error_msg)
        
        if name_area not in self._pars:
            error_msg = f"Missing parameters for area '{name_area}'"
            print(f"NLLS Model ERROR: {error_msg}")
            _logger.error(error_msg)
            raise ValueError(error_msg)
        
        spectrum = self._ref_spectra[name_area]
        model = self._models[name_area]
        params = self._pars[name_area]
        
        self._ref_results[name_area] = model.fit(
            spectrum,
            params=params,
            x=self._Eloss
        )
        
        _logger.info(f"Reference fit complete for area '{name_area}'")
    
    def multifit_area(self, name_area='default', progress_callback=None):
        """
        Fit all pixels in the dataset for a given area.
        
        Args:
            name_area: Label for reference area
            progress_callback: Optional callback function(current, total) for progress updates
        """
        try:
            array_area = self._ref_matrices.get(name_area, 
                                                np.ones(self._ds.ElectronCount.data.shape[:-1]))
        except:
            array_area = np.ones(self._ds.ElectronCount.data.shape[:-1])
        
        dimx, dimy = array_area.shape
        self._results[name_area] = []
        
        total_pixels = int(np.sum(array_area))
        current_pixel = 0
        
        for i in range(dimx):
            # Start each row with reference parameters (closer than previous pixel)
            paramet = self._ref_results[name_area].params
            self._results[name_area].append([])
            
            for j in range(dimy):
                if array_area[i, j] == 1:
                    # Fit this pixel
                    y = self._ds.sel(x=j, y=i).ElectronCount.data
                    res = self._models[name_area].fit(y, params=paramet, x=self._Eloss)
                    self._results[name_area][i].append(res)
                    
                    # Update parameters for next pixel (assumes continuity)
                    paramet = res.params
                    
                    # Progress callback
                    current_pixel += 1
                    if progress_callback:
                        progress_callback(current_pixel, total_pixels)
                else:
                    # Pixel outside fitting range
                    self._results[name_area][i].append(None)
        
        _logger.info(f"Multifit complete for area '{name_area}' ({total_pixels} pixels)")
    
    def get_element_maps(self, name_area='default'):
        """
        Extract elemental abundance maps from multifit results.
        
        Returns:
            dict: Dictionary with element_subshell keys and 2D arrays of relative cross-sections
        """
        if name_area not in self._results or not self._results[name_area]:
            return {}
        
        maps = {}
        dimx = len(self._results[name_area])
        dimy = len(self._results[name_area][0]) if dimx > 0 else 0
        
        # Get all continuum parameter names
        for el in self._fitting_elements:
            element_subshells = self._fitting_elements[el]['subshells']
            
            # For each subshell, find the continuum amplitude parameter
            for ssh in element_subshells:
                # Check for paired subshells
                if ssh[-1] in ['5', '4']:
                    key = f'{ssh[0]}54'
                elif ssh[-1] in ['3', '2']:
                    key = f'{ssh[0]}32'
                else:
                    key = ssh
                
                param_name = f'{el}{key}_cont_A'
                
                # Create map if not already exists
                if param_name not in maps:
                    maps[f'{el}_{key}'] = np.zeros((dimx, dimy))
                
                # Extract values from results
                for i in range(dimx):
                    for j in range(dimy):
                        if self._results[name_area][i][j] is not None:
                            result = self._results[name_area][i][j]
                            if param_name in result.params:
                                maps[f'{el}_{key}'][i, j] = result.params[param_name].value
        
        return maps
    
    def get_fit_quality_map(self, name_area='default'):
        """
        Extract fit quality (reduced chi-square) map.
        
        Returns:
            np.ndarray: 2D array of reduced chi-square values
        """
        if name_area not in self._results or not self._results[name_area]:
            return None
        
        dimx = len(self._results[name_area])
        dimy = len(self._results[name_area][0]) if dimx > 0 else 0
        
        chi2_map = np.zeros((dimx, dimy))
        
        for i in range(dimx):
            for j in range(dimy):
                if self._results[name_area][i][j] is not None:
                    chi2_map[i, j] = self._results[name_area][i][j].redchi
                else:
                    chi2_map[i, j] = np.nan
        
        return chi2_map
    
    def get_reference_fit(self, name_area='default'):
        """
        Get reference spectrum and its fit.
        
        Returns:
            tuple: (energy_loss, data, best_fit) or (None, None, None)
        """
        if name_area not in self._ref_results:
            return None, None, None
        
        result = self._ref_results[name_area]
        return self._Eloss, self._ref_spectra[name_area], result.best_fit