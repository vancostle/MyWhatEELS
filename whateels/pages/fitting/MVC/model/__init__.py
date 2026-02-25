from whateels.base.mvc import BaseModel
from whateels.shared_state import AppState
from .constants import Constants
import copy as cp

from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.ndimage import gaussian_filter1d
from lmfit import Model
from lmfit.models import GaussianModel, LorentzianModel, PseudoVoigtModel, SplitLorentzianModel

import numpy as np

class FittingModel(BaseModel):
    def __init__(self):
        super().__init__()
        self._constants = Constants()
        self._app_state = AppState()
        self._controller = 0

        self._spectra = 0 # Reference spectra
        self._models = 0 # Composite models for fitting
        self._pars = 0 # Parameters for fitting
        self._Eloss = 0 # Energy loss axis

    @property
    def constants(self) -> Constants:
        return self._constants
    
    @property
    def app_state(self) -> AppState:
        return self._app_state
    
    def set_controller(self, controller):
        self._controller = controller

    def get_uploaded_filename(self) -> str:
        """
        Get the filename of the currently uploaded dataset from shared state.
        
        Returns:
            str: Uploaded filename, or empty string if none
        """
        return str(self.app_state.filename) if self.app_state.filename is not None else "No file uploaded"
    
    def add_element(self, element_item):
        self._fitting_elements[element_item.element_name_short] = element_item

    def remove_element(self, element_item):
        self._fitting_elements.pop(element_item.element_name_short)
    
    def add_component(self, compo_type, center, flex='medium'):
        dictionary = dict()
        dataset = self.app_state.plot_dataset
        self._Eloss = dataset.coords['Eloss'].values
        self._spectra = AppState().spectra

        print(self._spectra.shape, self._Eloss.shape)
        print(f"NLLS Model: add_component() called")
        dictionary['components'] = []
        dictionary['const'] = []
        dictionary['params'] = []
        # Add ELNES (white line) 
        dict_var = {
            'low': [3, 3, 0.1, 0.1],
            'medium': [7, 7, 1, 1.25],
            'high': [15, 15, 1, 3],
            'maximum': [np.inf, np.inf, 1, np.inf]
        }
        if flex not in dict_var:
            flex = 'medium'

        # Determine component parameters
        cen, sigm, amp = self._determine_compo_parameters(
                        self._spectra, compo_type, center
                    )
                    
        dictionary['components'].append( {
            'type_compo': compo_type,
            'center': cen,
            'sigma': sigm,
            'amplitude': amp
        })
        
        # Set constraints
        dictionary['params'].append({
            'center_min': cen - dict_var[flex][0],
            'center_max': cen + dict_var[flex][1],
            'sigma_min': 0.5,
            'sigma_max': sigm + sigm * dict_var[flex][3],
            'amplitude_min': 0,
            'amplitude_max': np.inf
        })

        mod_list = []
        params_list = []

        for component in dictionary['components']:
            tipo = component['type_compo']
            pref = f'compo_'
                    
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
                if key in dictionary['components'][0]:
                    pars[f'{pref}{key}'].value = component[key]
                    pars[f'{pref}{key}'].min = dictionary['params'][0][f'{key}_min']
                    pars[f'{pref}{key}'].max = dictionary['params'][0][f'{key}_max']

            mod_list.append(mod)
            params_list.append(pars)
        
        self._models = mod_list[0]
        for mod in mod_list[1:]:
            self._models += mod
        # Make parameters
        self._pars = self._models.make_params()
        # Apply parameter values and constraints
        for pars in params_list:
            for par in pars:
                self._pars[par].value = pars[par].value
                self._pars[par].min = pars[par].min
                self._pars[par].max = pars[par].max
        
        print(f"NLLS Model: Component added successfully")

        self.fit_reference()
    
    def _determine_compo_parameters(self,spectrum,compo_type,Eloss_center):
        """This method makes an estimation of the initial parameter values (pre_fit) 
        of a certain component of the model, knowing only the type of component
        and the energy loss (aprox.) of the center for that component

        Args:
            compo_type (str): Type of component to be created/ whose parameters need guessing
                3 categories:
                symetrical-gaussian     : -str- gaussian
                symmetrical-nonGaussian : -str- lorentzian, pseudovoigt
                asymmetrical            : -str- splitlorentzian 
            Eloss_center ([type]): Energy Loss position in which we stimate the center of the component
                e.g. CeM5 - Eloss_center = 884.0 (Ce4+ in non reduced CeO2)
        """
        #If no ZeroLoss was analysed or included, let's guess
        fwhm      = 1.2 * 4  # Standard ELoss resolution ... around 1.2 eV in NonCorrected non FEG
        #fwhm_min = 0.7 * 2  # Going to Cold_FEG ranges of resolution in non monochromated
        #fwhm_max = 2.5 * 2  # Really badly calibrated acquisition or poor instrumentation 
        #Let's analyse the possible cases

        
        e_idx  = np.searchsorted(self._Eloss,Eloss_center) #Positional index E axis
        
        #delta_e = self._Eloss[1]-self._Eloss[1]
        cent = Eloss_center 
        print(self._Eloss[0],self._Eloss[-1],cent,e_idx,self._Eloss.size)
        print(f"Determining component parameters for type '{compo_type}' at Eloss {Eloss_center} eV (index {e_idx})")

        h_eidx = max(0,spectrum[e_idx])
        if compo_type == 'GaussianModel':
            sig = fwhm / np.sqrt(np.log(256))                 # fwhm   = 2*np.sqrt(2*log(2)) * sigma
            amp = h_eidx * max(2E-16,sig) * np.sqrt(2*np.pi)  # height = 1/sqrt(2*pi) * A / max(0,sigma)
            return [cent,sig,amp]
        elif compo_type == 'lorentzian':
            sig = fwhm / 2                                    # sigma  = 2*np.sqrt(2*log(2))
            amp = h_eidx * max(2E-16,sig) * np.pi
            return [cent,sig,amp]             # height = 1/pi * A / max(0,sigma)
        elif compo_type == 'pseudovoigt':
            sig = fwhm / 2                                    # sigma  = 2*np.sqrt(2*log(2))
            factor1 = max(2E-16,(sig*np.sqrt(np.pi/np.log(2))))
            factor2 = max(2E-16,(np.pi*sig))
            amp = 2 * h_eidx * factor1 * factor2 / (factor1 + factor2) 
            #As given by lmfit relation if fraction = 0.5
            return [cent,sig,amp]
        elif compo_type == 'splitlorentzian':
            #We start with a symmetric distrib -sigma = sigma_r = fwhm/2
            sig = fwhm / 2                             # fwhm = sigma + sigma_r
            amp = np.pi*h_eidx*max(2E-16,sig*2) / 2    # h = 2*A/pi/max(0,sigma+sigma_r)
            return [cent,sig,amp]
        else:
            print('NO valid component given')
            raise KeyError

    def delete_component(self,element,name,area_name= 'default'):
        """Method that allows to remove a certain component from the fitting.
        it also removes the constraints from the model dictionary.

        Args:
            element (str): Element to which we have attached this component.
                This helps with the component identification in the inner loop
            name (str): name of the component to be eliminated.
            area_name (str, optional): Label of the area from where we want to remove the component.
                Defaults to 'default'.
        """
        list_to_delete = []
        try:
            dictionary = self.models_components[area_name][element]
        except:
            print('The given element, or name of the area are wrong')
            print('\nCheck those fields and re-run')
            raise
        else:
            for compType in dictionary:
                for key in dictionary[compType]:
                    if name == key:
                        list_to_delete.append((compType,key))
                    else: pass
            for de in list_to_delete:
                dictionary[de[0]].pop(de[1])

    def fit_reference(self):
        """
        Method that carries out the initial fitting for the reference spectra
        of a certain reference area

        Args:
            name_area (str, optional): Label of the reference area selected.
                Defaults to 'default'.
        """
        self.ref_results = self._models.fit(self._spectra, params = self._pars, x = self._Eloss)
        print(self.ref_results.fit_report())
        print(self.ref_results.best_fit.shape)
        self._controller.update_plot(fitting_results = self.ref_results.best_fit)

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
        # primer find peaks
        
        #determinar les zones

        # determinar model per zona

        # fe

        
        print(f"NLLS Model: create_components() called for area '{name_area}'")
        print(f"  - Elements to fit: {list(self._fitting_elements.keys())}")
        print(f"  - Excluded elements: {excluded_elements}")
        print(f"  - Spectrum shape: {spectrum.shape}")
        
        if excluded_elements is None:
            excluded_elements = []
        
        self._models_components[name_area] = dict()
        self._ref_spectra[name_area] = cp.deepcopy(spectrum)
        dictionary = self._models_components[name_area]
        
        print(f"NLLS Model: Adding ELNES components...")
        # Add ELNES (white line) components
        self._add_ELNES(spectrum, dictionary, default_compo_type, flex, excluded_elements)
        
        # Add reference matrix for default area
        if name_area == 'default':
            ref = np.ones(self._ds.ElectronCount.values.shape[:-1]) # fix: dataset not in model
            self._ref_matrices[name_area] = ref
        
        print(f"NLLS Model: Components created successfully for area '{name_area}'")
        
        _logger.info(f"Created components for area '{name_area}'")

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