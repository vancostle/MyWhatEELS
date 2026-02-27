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

        self._app_state.spectra = None
        self._app_state.fitting_results = None  # Initialize fitting results in shared state
        self._app_state.is_multifit = False  # Initialize multifit flag in shared state

        self._spectra = 0 # Reference spectra
        self._models = 0 # Composite models for fitting
        self._pars = 0 # Parameters for fitting
        self._Eloss = 0 # Energy loss axis

        self.dictionary = dict()
        self.dictionary['components'] = []
        self.dictionary['const'] = []
        self.dictionary['params'] = []

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
    
    def is_multifit_available(self) -> bool:
        """
        Check if multifit data is available in the application state.
        
        Returns:
            bool: True if multifit data exists, False otherwise
        """
        return self.app_state.multifit is not None
    
    def add_component(self, component_item, flex='low'):
        dataset = self.app_state.plot_dataset
        self._Eloss = dataset.coords['Eloss'].values
        self._spectra = AppState().spectra

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
                        self._spectra, component_item.compo_type, component_item.energy_center, component_item.energy_range
                    )
        
        component_item.set_parameters(cen, sigm, amp)
        component_item.set_center_range(cen - dict_var[flex][0], cen + dict_var[flex][1],)
        component_item.set_sigma_range(0.5, sigm + sigm * dict_var[flex][3])
        component_item.set_amplitude_range(0, np.inf)

        self.dictionary['components'].append(component_item)
        
        print(f"NLLS Model: Component added successfully")

        self.create_model()  # Recreate model with new component
        self.fit_reference()  # Refit reference spectrum with updated model

    def create_model(self):
        if not self.dictionary['components']:
            print("NLLS Model: No components to create model")
            return
        mod_list = []
        self._spectra = AppState().spectra

        for idx, component in enumerate(self.dictionary['components']):
            tipo = component.compo_type
            pref = f'compo_{idx}_'
                    
            # Select model type
            if tipo == 'GaussianModel':
                mod = GaussianModel(prefix=pref)
            elif tipo == 'LorentzianModel':
                mod = LorentzianModel(prefix=pref)
            elif tipo == 'PseudoVoigtModel':
                mod = PseudoVoigtModel(prefix=pref)
            elif tipo == 'SplitLorentzianModel':
                mod = SplitLorentzianModel(prefix=pref)
            else:
                mod = GaussianModel(prefix=pref)

            mod_list.append(mod)
        
        self._models = mod_list[0]
        for mod in mod_list[1:]:
            self._models += mod
        # Make parameters
        self._pars = self._models.make_params()
        # Apply parameter values and constraints
        for idx, component in enumerate(self.dictionary['components']):
            pref = f'compo_{idx}_'
            self._pars[f'{pref}center'].value = component.energy_center
            self._pars[f'{pref}center'].min = component.center_range[0]
            self._pars[f'{pref}center'].max = component.center_range[1]
            self._pars[f'{pref}sigma'].value = component.sigma
            self._pars[f'{pref}sigma'].min = component.sigma_range[0]
            self._pars[f'{pref}sigma'].max = component.sigma_range[1]
            self._pars[f'{pref}amplitude'].value = component.amplitude
            self._pars[f'{pref}amplitude'].min = component.amplitude_range[0]
            self._pars[f'{pref}amplitude'].max = component.amplitude_range[1]
        
        
    
    def _determine_compo_parameters(self,spectrum,compo_type,Eloss_center, energy_range):
        """This method makes an estimation of the initial parameter values (pre_fit) 
        of a certain component of the model, knowing only the type of component
        and the energy loss (aprox.) of the center for that component

        Args:
            compo_type (str): Type of component to be created/ whose parameters need guessing
                3 categories:
                symetrical-gaussian     : -str- GaussianModel
                symmetrical-nonGaussian : -str- LorentzianModel, PseudoVoigtModel
                asymmetrical            : -str- SplitLorentzianModel 
            Eloss_center ([type]): Energy Loss position in which we stimate the center of the component
                e.g. CeM5 - Eloss_center = 884.0 (Ce4+ in non reduced CeO2)
        """
        #If no ZeroLoss was analysed or included, let's guess
        #fwhm      = 1.2 * 4  # Standard ELoss resolution ... around 1.2 eV in NonCorrected non FEG
        #fwhm_min = 0.7 * 2  # Going to Cold_FEG ranges of resolution in non monochromated
        #fwhm_max = 2.5 * 2  # Really badly calibrated acquisition or poor instrumentation 
        #Let's analyse the possible cases

        fwhm  = (energy_range[1] - energy_range[0]) / 2  # Estimate FWHM based on energy range of component]

        
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
        elif compo_type == 'LorentzianModel':
            sig = fwhm / 2                                    # sigma  = 2*np.sqrt(2*log(2))
            amp = h_eidx * max(2E-16,sig) * np.pi
            return [cent,sig,amp]             # height = 1/pi * A / max(0,sigma)
        elif compo_type == 'PseudoVoigtModel':
            sig = fwhm / 2                                    # sigma  = 2*np.sqrt(2*log(2))
            factor1 = max(2E-16,(sig*np.sqrt(np.pi/np.log(2))))
            factor2 = max(2E-16,(np.pi*sig))
            amp = 2 * h_eidx * factor1 * factor2 / (factor1 + factor2) 
            #As given by lmfit relation if fraction = 0.5
            return [cent,sig,amp]
        elif compo_type == 'SplitLorentzianModel':
            #We start with a symmetric distrib -sigma = sigma_r = fwhm/2
            sig = fwhm / 2                             # fwhm = sigma + sigma_r
            amp = np.pi*h_eidx*max(2E-16,sig*2) / 2    # h = 2*A/pi/max(0,sigma+sigma_r)
            return [cent,sig,amp]
        else:
            print('NO valid component given')
            raise KeyError
    
    def remove_component(self, component_item):
        self.dictionary['components'] = [comp for comp in self.dictionary['components'] if comp != component_item]
        if not self.dictionary['components']:
            self._controller.update_plot(fitting_results=None)  # Clear fitting results if no components remain
            self.app_state.fitting_results = None  # Clear fitting results in shared state as well
        self.create_model()  # Recreate model with updated components
        self.fit_reference()

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

        self._controller.update_plot(fitting_results = self.ref_results.best_fit)