"""
NLLS View

Provides the user interface for NLLS fitting operations.
Adapted from interactive_NLLS_SImages.py and interactive_NLLS_SLines.py.
"""

from whateels.base.mvc import BaseView
from whateels.helpers.nlls_library.database.elements import elements
import panel as pn
import param


class NLLSView(BaseView):
    """
    NLLS View class for displaying UI components.
    
    Provides widgets for element selection, model configuration,
    and fitting controls.
    """
    
    def __init__(self, model):
        super().__init__(model, css_files=None)
        
        self._model = model
        
        # Create UI components
        self._create_widgets()
        
        # Initialize subshells for the first element
        if self.element_selector.value:
            self.update_subshells(self.element_selector.value)
        
    def _create_widgets(self):
        """Create all UI widgets for NLLS operations"""
        
        # Get list of available elements from database
        available_elements = sorted(elements.keys())
        
        # Element selection widgets
        self.element_selector = pn.widgets.Select(
            name='Element',
            options=available_elements,
            value=available_elements[0] if available_elements else None,
            width=200
        )
        
        self.subshell_selector = pn.widgets.MultiChoice(
            name='Subshells',
            options=[],  # Will be populated when element is selected
            width=300
        )
        
        self.add_element_button = pn.widgets.Button(
            name='Add Element',
            button_type='primary',
            width=150
        )
        
        # Model creation controls
        self.create_model_button = pn.widgets.Button(
            name='Create Model',
            button_type='success',
            width=200,
            disabled=True
        )
        
        self.fit_references_button = pn.widgets.Button(
            name='Fit Reference Spectra',
            button_type='default',
            width=200,
            disabled=True
        )
        
        self.multifit_button = pn.widgets.Button(
            name='Run MultiFit',
            button_type='default',
            width=200,
            disabled=True
        )
        
        # Status/info displays
        self.status_text = pn.pane.Markdown(
            '### NLLS Fitting\n\nSelect elements and subshells to begin.',
            width=400,
            styles={'background': '#f0f0f0', 'padding': '10px', 'border-radius': '5px'}
        )
        
        self.selected_elements_text = pn.pane.Markdown(
            '**Selected Elements:** None',
            width=400
        )
        
        # Progress indicator
        self.progress_bar = pn.indicators.Progress(
            name='Fitting Progress',
            value=0,
            max=100,
            visible=False,
            width=400
        )
        
    def build_sidebar(self):
        """Build the sidebar with element selection controls"""
        return pn.Column(
            '## Element Selection',
            self.element_selector,
            self.subshell_selector,
            self.add_element_button,
            pn.layout.Divider(),
            self.selected_elements_text,
            pn.layout.Divider(),
            '## Model Controls',
            self.create_model_button,
            self.fit_references_button,
            self.multifit_button,
            pn.layout.Divider(),
            self.progress_bar,
            sizing_mode='stretch_width'
        )
    
    def build_main_content(self):
        """Build the main content area with status and results"""
        self.results_container = pn.Column(
            sizing_mode='stretch_both'
        )
        
        return pn.Column(
            self.status_text,
            pn.layout.Divider(),
            self.results_container,
            sizing_mode='stretch_both'
        )
    
    def display_results(self, element_maps, chi2_map, eloss, ref_spectrum, ref_fit):
        """
        Display fitting results with maps and plots.
        
        Args:
            element_maps: Dictionary of elemental abundance maps
            chi2_map: Reduced chi-square map
            eloss: Energy loss axis
            ref_spectrum: Reference spectrum data
            ref_fit: Reference fitted spectrum
        """
        import holoviews as hv
        from holoviews import opts
        hv.extension('bokeh')
        
        plots = []
        
        # Reference spectrum fit
        if eloss is not None and ref_spectrum is not None and ref_fit is not None:
            ref_plot = hv.Curve((eloss, ref_spectrum), 'Energy Loss (eV)', 'Intensity', label='Data') * \
                       hv.Curve((eloss, ref_fit), label='Fit')
            ref_plot = ref_plot.opts(
                width=800, height=300, tools=['hover'], 
                title='Reference Spectrum Fit', show_legend=True
            )
            plots.append(('### Reference Spectrum Fit', pn.pane.HoloViews(ref_plot)))
        
        # Element maps
        if element_maps:
            map_plots = []
            for label, map_data in element_maps.items():
                img = hv.Image(map_data, ['x', 'y'], label).opts(
                    opts.Image(width=300, height=300, cmap='viridis', 
                              colorbar=True, tools=['hover'], title=label)
                )
                map_plots.append(pn.pane.HoloViews(img))
            
            if map_plots:
                plots.append(('### Elemental Abundance Maps', pn.Row(*map_plots, scroll=True)))
        
        # Chi-square map
        if chi2_map is not None:
            chi2_img = hv.Image(chi2_map, ['x', 'y'], 'Reduced χ²').opts(
                opts.Image(width=400, height=400, cmap='hot', 
                          colorbar=True, tools=['hover'], title='Fit Quality (Reduced χ²)')
            )
            plots.append(('### Fit Quality', pn.pane.HoloViews(chi2_img)))
        
        # Update results container
        result_components = []
        for title, plot in plots:
            result_components.append(pn.pane.Markdown(title))
            result_components.append(plot)
            result_components.append(pn.layout.Divider())
        
        self.results_container.clear()
        self.results_container.extend(result_components)
    
    def update_status(self, message: str, level: str = 'info'):
        """
        Update the status message.
        
        Args:
            message: Status message to display
            level: Message level ('info', 'success', 'warning', 'error')
        """
        colors = {
            'info': '#e3f2fd',
            'success': '#e8f5e9',
            'warning': '#fff3e0',
            'error': '#ffebee'
        }
        
        self.status_text.object = f'### {message}'
        self.status_text.styles = {
            'background': colors.get(level, '#f0f0f0'),
            'padding': '10px',
            'border-radius': '5px'
        }
    
    def show_progress(self, value: int, max_value: int = 100):
        """
        Update and show the progress bar.
        
        Args:
            value: Current progress value
            max_value: Maximum progress value
        """
        self.progress_bar.max = max_value
        self.progress_bar.value = value
        self.progress_bar.visible = True
    
    def hide_progress(self):
        """Hide the progress bar"""
        self.progress_bar.visible = False
        self.progress_bar.value = 0
    
    def update_subshells(self, element: str):
        """
        Update available subshells based on selected element.
        
        Args:
            element: Selected element symbol
        """
        if element and element in elements:
            atomic_props = elements[element].get('Atomic_properties', {})
            binding_energies = atomic_props.get('Binding_energies', {})
            
            if binding_energies:
                subshells = sorted(binding_energies.keys())
                self.subshell_selector.options = subshells
                self.subshell_selector.value = []
            else:
                self.subshell_selector.options = []
                self.subshell_selector.value = []
        else:
            self.subshell_selector.options = []
            self.subshell_selector.value = []
    
    def update_selected_elements_display(self, fitting_elements: dict):
        """
        Update the display of selected elements.
        
        Args:
            fitting_elements: Dictionary of fitting elements from model
        """
        if not fitting_elements:
            self.selected_elements_text.object = '**Selected Elements:** None'
        else:
            elements_list = []
            for el, data in fitting_elements.items():
                subshells = ', '.join(data['subshells'])
                elements_list.append(f"- **{el}**: {subshells}")
            
            self.selected_elements_text.object = '**Selected Elements:**\n' + '\n'.join(elements_list)
            
            # Enable create model button if elements are selected
            self.create_model_button.disabled = False