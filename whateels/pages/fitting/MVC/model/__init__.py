from whateels.base.mvc import BaseModel
from whateels.state import CacheManager
from .constants import Constants

from lmfit.models import GaussianModel, LorentzianModel, PseudoVoigtModel, SplitLorentzianModel

import numpy as np

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.state import AppState
    from ...MVC import FittingController
    from ..model.component_item import ComponentItem

class FittingModel(BaseModel):
    """Model responsible for component management, lmfit model assembly, and fitting outputs."""

    def __init__(self):
        """Initialize model constants, shared state fields, and component registry."""
        super().__init__()
        self._constants = Constants()
        self._app_state = CacheManager.get_cached_app_state()
        # Removed controller reference for MVC purity

        self._app_state.spectra = None
        self._app_state.fitting_results = None
        self._app_state.is_multifit = False

        self._spectra = 0
        self._models = 0
        self._pars = 0
        self._Eloss = 0

        self.dictionary = dict()
        self.dictionary['components'] = []
        self.dictionary['const'] = []
        self.dictionary['params'] = []

    @property
    def constants(self) -> Constants:
        return self._constants
    
    @property
    def app_state(self) -> "AppState":
        return self._app_state
    


    def get_uploaded_filename(self) -> str:
        """
        Get the filename of the currently uploaded dataset from shared state.
        
        Returns:
            str: Uploaded filename, or empty string if none
        """
        return str(self._app_state.filename) if self._app_state.filename is not None else "No file uploaded"
    
    def is_multifit_available(self) -> bool:
        """
        Backward-compatible alias for preprocessed data availability.
        
        Returns:
            bool: True if preprocessed data exists, False otherwise
        """
        return self.is_preprocessed_data_available()

    def is_preprocessed_data_available(self) -> bool:
        """Check if Home-published preprocessed dataset is available."""
        return self._app_state.preprocessed_plot_dataset is not None
    
    def add_component(self, component_item: "ComponentItem", flex='low'):
        """Add a component, estimate initial params, rebuild model, and refit."""
        dataset = self._app_state.plot_dataset
        self._Eloss = getattr(dataset, 'coords', {}).get('Eloss', {}).values if dataset is not None else None
        
        self._spectra = self._app_state.spectra
        if self._spectra is None:
            raise ValueError("Fitting Model: No spectra data available to add component")

        is_using_preprocessed = (
            self._app_state.preprocessed_plot_dataset is not None
            and dataset is self._app_state.preprocessed_plot_dataset
        )
        print(
            "[FittingModel:add_component] source ",
            f"using_preprocessed={is_using_preprocessed}, dataset_id={id(dataset)}, "
            f"spectra_min={float(np.nanmin(np.asarray(self._spectra)))}, "
            f"spectra_max={float(np.nanmax(np.asarray(self._spectra)))}"
        )
        dict_var = {
            'Low': [3, 3, 0.1, 0.1, 0.5, 2],
            'Medium': [7, 7, 1, 1.25, 0, 3],
            'High': [15, 15, 1, 3, 0, 5],
            'Maximum': [np.inf, np.inf, 1, np.inf, 0, np.inf]
        }
        if flex not in dict_var:
            flex = 'Medium'

        # Estimate component parameters from the current spectrum and selected window.
        cen, sigm, amp = self._determine_compo_parameters(
            self._spectra, component_item.compo_type, component_item.energy_center, component_item.energy_range
        )

        print(
            "[FittingModel:add_component] guessed values ",
            f"model={component_item.compo_type}, center={cen}, sigma={sigm}, amplitude={amp}, "
            f"energy_center_input={component_item.energy_center}, energy_range={component_item.energy_range}"
        )

        center_min = cen - dict_var[flex][0]
        center_max = cen + dict_var[flex][1]

        sigma_min = 0.5
        sigma_max = sigm + sigm * dict_var[flex][3]

        amp_min_raw = amp * dict_var[flex][4]
        amp_max_raw = amp * dict_var[flex][5]

        print(
            "[FittingModel:add_component] raw amplitude bounds ",
            f"amp_min_raw={amp_min_raw}, amp_max_raw={amp_max_raw}, flexibility={flex}"
        )

        amp_min = amp_min_raw
        amp_max = amp_max_raw

        component_item.set_parameters(cen, sigm, amp)
        component_item.set_center_range(center_min, center_max)
        component_item.set_sigma_range(sigma_min, sigma_max)
        component_item.set_amplitude_range(amp_min, amp_max)

        self.dictionary['components'].append(component_item)

        self.create_model()
        self.fit_reference()

    def create_model(self):
        """Build a composite lmfit model and parameter bounds from registered components."""
        if not self.dictionary['components']:
            print("NLLS Model: No components to create model")
            return
        mod_list = []
        self._spectra = self._app_state.spectra

        for idx, component in enumerate(self.dictionary['components']):
            tipo = component.compo_type
            pref = f'compo_{idx}_'
                    
            # Select lmfit model class for each registered component.
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
        # Create parameter set and apply initial values and bounds.
        self._pars = self._models.make_params()
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
        """Estimate initial center/sigma/amplitude values for a fitting component.

        Args:
            compo_type (str): Type of component to be created/ whose parameters need guessing
                3 categories:
                symmetrical-gaussian     : -str- GaussianModel
                symmetrical-nonGaussian : -str- LorentzianModel, PseudoVoigtModel
                asymmetrical            : -str- SplitLorentzianModel
            Eloss_center ([type]): Energy-loss position used to estimate component center
                e.g. CeM5 - Eloss_center = 884.0 (Ce4+ in non reduced CeO2)
        """
        # Approximate FWHM from the selected component energy window.
        fwhm  = (energy_range[1] - energy_range[0]) / 2

        if self._Eloss is None:
            raise ValueError("Energy axis is not initialized for component parameter estimation")

        eloss = np.asarray(self._Eloss)
        spec = np.asarray(spectrum)
        if spec.ndim != 1:
            spec = np.ravel(spec)

        # Center index from user-selected energy center.
        e_idx = int(np.searchsorted(eloss, Eloss_center))
        e_idx = int(np.clip(e_idx, 0, len(spec) - 1))

        cent = Eloss_center

        # Use local peak inside selected energy range (more robust on preprocessed signals
        # where the center sample can be negative after preprocessing).
        e_min, e_max = float(energy_range[0]), float(energy_range[1])
        if e_min > e_max:
            e_min, e_max = e_max, e_min
        window_mask = (eloss >= e_min) & (eloss <= e_max)

        if np.any(window_mask):
            window_spec = spec[window_mask]
        else:
            lo = max(0, e_idx - 3)
            hi = min(len(spec), e_idx + 4)
            window_spec = spec[lo:hi]

        finite_window = window_spec[np.isfinite(window_spec)]
        if finite_window.size == 0:
            h_eidx = max(0.0, float(spec[e_idx]))
        else:
            h_eidx = max(0.0, float(np.max(finite_window)))

        if compo_type == 'GaussianModel':
            sig = fwhm / np.sqrt(np.log(256))
            amp = h_eidx * max(2E-16,sig) * np.sqrt(2*np.pi)
            return [cent,sig,amp]
        elif compo_type == 'LorentzianModel':
            sig = fwhm / 2
            amp = h_eidx * max(2E-16,sig) * np.pi
            return [cent,sig,amp]
        elif compo_type == 'PseudoVoigtModel':
            sig = fwhm / 2
            factor1 = max(2E-16,(sig*np.sqrt(np.pi/np.log(2))))
            factor2 = max(2E-16,(np.pi*sig))
            amp = 2 * h_eidx * factor1 * factor2 / (factor1 + factor2) 
            # Follows lmfit pseudo-Voigt relation for fraction ~= 0.5.
            return [cent,sig,amp]
        elif compo_type == 'SplitLorentzianModel':
            # Start from a symmetric shape: sigma == sigma_r == fwhm/2.
            sig = fwhm / 2
            amp = np.pi*h_eidx*max(2E-16,sig*2) / 2
            return [cent,sig,amp]
        else:
            print('NO valid component given')
            raise KeyError
    
    def remove_component(self, component_item):
        """Remove a component and refit, or clear fitting results if none remain. Returns True if plot should be updated."""
        self.dictionary['components'] = [comp for comp in self.dictionary['components'] if comp != component_item]
        if not self.dictionary['components']:
            print("NLLS Model: No components remaining after deletion")
            self._app_state.fitting_results = None
            self.ref_results = None
            return True  # Signal to controller to update plot
        self.create_model()
        self.fit_reference()
        return True  # Signal to controller to update plot

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
        Fit the current reference spectrum using the composed model and parameters.
        Returns the fit results.
        """
        self.ref_results = self._models.fit(self._spectra, params = self._pars, x = self._Eloss)
        return self.ref_results

    def get_energy_map(self):
        """Compute a per-pixel energy map by integrating selected windows with fit profile support."""

        fitting_results = self._app_state.fitting_results
        if fitting_results is None:
            print("NLLS Model: No fitting results available to generate energy map")
            return None

        dataset = self._app_state.plot_dataset
        if dataset is None or not hasattr(dataset, 'ElectronCount'):
            print("NLLS Model: No ElectronCount data available to generate energy map")
            return None

        Eloss = np.asarray(dataset.coords['Eloss'].values)
        e_count = np.asarray(dataset.ElectronCount.values)
        fit = np.asarray(fitting_results)

        if e_count.ndim != 3:
            print(f"NLLS Model: Expected ElectronCount with 3 dims (y, x, E), got shape={e_count.shape}")
            return None

        if fit.ndim != 1:
            fit = np.ravel(fit)

        n_energy = e_count.shape[-1]
        if fit.size != n_energy:
            x_old = np.linspace(0.0, 1.0, fit.size)
            x_new = np.linspace(0.0, 1.0, n_energy)
            fit = np.interp(x_new, x_old, fit)

        fit = np.where(np.isfinite(fit), fit, 0.0)
        e_count = np.where(np.isfinite(e_count), e_count, 0.0)

        components = self.dictionary.get('components', [])
        energy_mask = np.zeros(n_energy, dtype=bool)

        if Eloss.size == n_energy and components:
            for component in components:
                energy_range = getattr(component, 'energy_range', None)
                if energy_range is None or len(energy_range) < 2:
                    continue

                e_min = float(energy_range[0])
                e_max = float(energy_range[1])
                if e_min > e_max:
                    e_min, e_max = e_max, e_min

                energy_mask |= (Eloss >= e_min) & (Eloss <= e_max)

        if not np.any(energy_mask):
            print("NLLS Model: No valid component windows found; integrating full energy range")
            energy_mask[:] = True

        selected_e_count = e_count[..., energy_mask]
        selected_fit = fit[energy_mask]

        # For each pixel, add fitting profile in selected windows and integrate over energy.
        energy_map = np.sum(selected_e_count + selected_fit[np.newaxis, np.newaxis, :], axis=-1)

        return energy_map 

    