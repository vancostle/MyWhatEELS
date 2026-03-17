import panel as pn
from typing import TYPE_CHECKING
from collections.abc import Mapping

from whateels.errors.dm.data import DMPlotCreationError
from whateels.helpers.constants import HTML_ROOT
from ..visualizer_factory import VisualizerFactory
from whateels.state import CacheManager

if TYPE_CHECKING:
    from ...view import FittingView
    from ...model import FittingModel
    from ...controller import FittingController
    from xarray import Dataset

class LayoutManager:
    """
    Manager class responsible for handling all layout operations in the WhatEELS application.
    
    This class encapsulates all UI layout management functionality, including:
    - Main layout state management (loading, error, content, placeholder states)
    - Sidebar component management
    - Float panel operations
    
    By separating layout concerns from the main Controller, we achieve better
    code organization and single responsibility principle.
    """
    
    def __init__(self, view: "FittingView", controller: "FittingController", model: "FittingModel"):
        """
        Initialize the LayoutManager with a reference to the View.
        
        Args:
            view: The View instance that contains the UI components to manage
        """
        self._view = view
        self._controller = controller
        self._model = model

        # Store all dataset information
        self._all_dataset_info: list[pn.viewable.Viewable] = []
        self._max_energy_range = [float('inf'), float('-inf')]
        self._plots_tab = None
        self._chosen_visualizers: list = []
        
    def add_component_to_sidebar_layout(self, component: pn.viewable.Viewable):
        """Add a component to the sidebar and track it as the last dataset info component."""
        self._view.left_sidebar.append(component)
        self._view.dataset_info = component

    def add_best_fit_component_to_sidebar_layout(self, component: pn.viewable.Viewable):
        """Add the best-fit summary card to the left sidebar and keep a reference to it."""
        self._view.left_sidebar.append(component)
        self._view.best_fit_component = component

    def remove_best_fit_component_from_sidebar(self):
        """Remove the best fit component from the sidebar, if present."""
        best_fit_component = getattr(self._view, "best_fit_component", None)
        if best_fit_component is None:
            return
        if best_fit_component in self._view.left_sidebar:
            self._view.left_sidebar.remove(best_fit_component)
        self._view.best_fit_component = None

    def remove_dataset_info_from_sidebar(self):
        """Remove the last dataset info component from the sidebar, if present."""
        if self._view.dataset_info is None:
            return
        if self._view.dataset_info in self._view.left_sidebar:
            self._view.left_sidebar.remove(self._view.dataset_info)
            self._view.dataset_info = None
            
    def create_tab_and_dataset_info(self, all_datasets: list["Dataset"]) -> None:
        """
        Create visualizations for all datasets and setup tabbed UI interface.
        
        Args:
            all_datasets: List of processed datasets to visualize
                         
        Raises:
            DMPlotCreationError: When visualization creation fails
        """
        DATASET_TYPE = 'dataset_type'
        IMAGE_NAME_ATTRIBUTE = 'image_name'
        NOT_AVAILABLE = 'N/A'
        ACTIVE = 'active'
        STRETCH_BOTH = 'stretch_both'

        app_state = CacheManager.get_cached_app_state()

        try:
            # Clear previous dataset info panels to prevent caching old data
            self._all_dataset_info.clear()
            
            visualizer_factory = VisualizerFactory(self._model, self._controller)
            self._plots_tab = pn.Tabs(sizing_mode=STRETCH_BOTH)
            for dataset in all_datasets:
                dataset_type = dataset.attrs.get(DATASET_TYPE, NOT_AVAILABLE)
                image_name = dataset.attrs.get(IMAGE_NAME_ATTRIBUTE, NOT_AVAILABLE)

                # Create plots using the factory
                chosen_visualizer = visualizer_factory.choose_visualizer(str(dataset_type), dataset)
                self._chosen_visualizers.append(chosen_visualizer)
                if chosen_visualizer is None:
                    return
                visualizer_plots = chosen_visualizer.create_plots()
                
                self._plots_tab.append((image_name, visualizer_plots))
                
                self._all_dataset_info.append(chosen_visualizer.create_dataset_info())
                
            self._plots_tab.param.watch(self._on_tab_with_visualizers_change, ACTIVE, onlychanged=False)
            app_state.plot_dataset = app_state.all_datasets[app_state.selected_tab_index_dataset]  # Set initial dataset to plot based on selected tab index
            
            # Update UI
            self._controller.base_layout.update_main(self._plots_tab)
            self.remove_dataset_info_from_sidebar()
            self.add_component_to_sidebar_layout(self._all_dataset_info[0])

        except Exception as e:
            raise DMPlotCreationError(e)
    def get_energy_range(self) -> list[float]:
        """Get the maximum energy range across all datasets."""
        state = CacheManager.get_cached_app_state()
        selected_index = state.selected_tab_index_dataset
        return state.all_datasets[selected_index].coords[self._model.constants.ELOSS].values

    
    def get_active_dataset(self):
        """Return the dataset currently selected by the active tab index."""
        state = CacheManager.get_cached_app_state()
        selected_index = state.selected_tab_index_dataset
        return state.all_datasets[selected_index]

    def _on_tab_with_visualizers_change(self, event):
        """Handle tab changes by updating sidebar with selected dataset info."""

        # Get the selected tab index
        selected_tab_index = event.new

        state = CacheManager.get_cached_app_state()

        state.selected_tab_index_dataset = selected_tab_index  # Update shared state

        state.quantification_elements = []

        state.plot_dataset = state.all_datasets[selected_tab_index]

        # Update sidebar with the corresponding dataset info
        self._controller.layout.remove_dataset_info_from_sidebar()
        self._controller.layout.add_component_to_sidebar_layout(self._all_dataset_info[selected_tab_index])

    def add_new_component_input(self, element_input_view: pn.viewable.Viewable):
        """Add a new element input component to the sidebar."""
        self._view.right_sidebar.append(element_input_view)

    def update_plot(self, fitting_results=None):
        """Refresh the main spectrum plot and optionally overlay fitting results.

        When `fitting_results` is `None`, the plot is reset to the base spectrum/ROI state
        and any existing best-fit sidebar card is removed. Otherwise, this method stores the
        fit in shared state, draws the fitted curve, and updates the best-fit information card.
        """
        state = CacheManager.get_cached_app_state()
        if fitting_results is None:
            self._chosen_visualizers[0].update_plot()
            self.remove_best_fit_component_from_sidebar()
        else:
            y_fit = fitting_results.best_fit if hasattr(fitting_results, 'best_fit') else fitting_results
            self._chosen_visualizers[0].update_plot()
            self._chosen_visualizers[0].plot_fitting(
                state.plot_dataset.coords['Eloss'].values,
                y_fit
            )
            best_fit_component = self.create_best_fit_info(fitting_results)
            self.remove_best_fit_component_from_sidebar()
            self.add_best_fit_component_to_sidebar_layout(best_fit_component)

    def create_best_fit_info(self, fitting_results):
        """Build a metadata-like Panel card with fit parameters and summary statistics.

        The card intentionally mirrors the existing dataset-info styling so users can read
        acquisition metadata and fitting metadata with the same visual structure.
        """
        STRETCH_WIDTH = "stretch_width"
        DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
        DATASET_INFO_CLASS = ["dataset-info", "animated"]
        TITLE = "<h5 class=\"dataset-info-title\">Best Fit Information</h5>"
        NOT_AVAILABLE = "N/A"
        MARGIN_ZERO = 0
        SPACER_HEIGHT_SMALL = 5
        SPACER_HEIGHT_MEDIUM = 10
        HTML_FILE = 'metadata_info.html'
        READ_MODE = 'r'
        UTF_8 = 'utf-8'

        def _format_value(value):
            if value is None:
                return NOT_AVAILABLE
            try:
                if isinstance(value, bool):
                    return str(value)
                if isinstance(value, (int, float)):
                    return f"{float(value):.6g}"
            except Exception:
                pass
            return str(value)

        def _extract_named_values(result_obj):
            values = {}
            if result_obj is None:
                return values

            if isinstance(result_obj, Mapping):
                if isinstance(result_obj.get('best_values'), Mapping):
                    values.update(result_obj['best_values'])
                elif isinstance(result_obj.get('params'), Mapping):
                    for key, param in result_obj['params'].items():
                        values[key] = getattr(param, 'value', param)
                else:
                    for key, val in result_obj.items():
                        if key in {'best_fit', 'model'}:
                            continue
                        if isinstance(val, (str, int, float, bool)) or val is None:
                            values[key] = val

            if hasattr(result_obj, 'best_values') and isinstance(result_obj.best_values, Mapping):
                values.update(result_obj.best_values)

            if not values and hasattr(result_obj, 'params'):
                try:
                    params = result_obj.params
                    if isinstance(params, Mapping):
                        for key, param in params.items():
                            values[key] = getattr(param, 'value', param)
                except Exception:
                    pass

            return values

        def _extract_stats(result_obj):
            stats = {}
            for key in ('chisqr', 'redchi', 'aic', 'bic', 'nfev', 'nvarys'):
                if isinstance(result_obj, Mapping) and key in result_obj:
                    stats[key] = result_obj.get(key)
                elif hasattr(result_obj, key):
                    stats[key] = getattr(result_obj, key)
            return stats

        dataset = self.get_active_dataset()
        attrs = dataset.attrs if dataset is not None else {}

        rows = [
            ('shape', attrs.get('shape', NOT_AVAILABLE)),
            ('beam_energy', attrs.get('beam_energy', NOT_AVAILABLE)),
            ('convergence_angle', attrs.get('convergence_angle', NOT_AVAILABLE)),
            ('collection_angle', attrs.get('collection_angle', NOT_AVAILABLE)),
        ]

        parameter_values = _extract_named_values(fitting_results)
        stats_values = _extract_stats(fitting_results)

        if parameter_values:
            rows.append(('n_params', len(parameter_values)))
            rows.extend((f"param.{name}", value) for name, value in parameter_values.items())
        else:
            rows.append(('n_params', 0))

        rows.extend((f"fit.{name}", value) for name, value in stats_values.items())

        # Reuse the same metadata button HTML to preserve styling parity with dataset info cards.
        metadata_html_path = HTML_ROOT / HTML_FILE
        with open(metadata_html_path, READ_MODE, encoding=UTF_8) as f:
            metadata_button_html = f.read()

        metadata_button = pn.pane.HTML(metadata_button_html, margin=MARGIN_ZERO)

        header = pn.Row(
            pn.pane.HTML(TITLE, sizing_mode=STRETCH_WIDTH, margin=MARGIN_ZERO),
            metadata_button,
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_HEADER_CLASS,
            margin=MARGIN_ZERO
        )

        info_rows = [
            pn.Row(
                pn.pane.HTML(f"<strong>{label}:</strong>"),
                pn.pane.Str(_format_value(value)),
                sizing_mode=STRETCH_WIDTH
            )
            for label, value in rows
        ]

        return pn.Column(
            header,
            pn.Spacer(height=SPACER_HEIGHT_SMALL),
            *info_rows,
            pn.Spacer(height=SPACER_HEIGHT_MEDIUM),
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_CLASS
        )

    def plot_energy_map(self):
        """Plot the model-computed energy map over the currently selected image.

        Raises:
            DMPlotCreationError: If there is no selected dataset, no fitting results,
                or no available energy map.
        """
        app_state = CacheManager.get_cached_app_state()
        
        if app_state.plot_dataset is None:
            raise DMPlotCreationError("No dataset selected for plotting energy map.")
        if app_state.fitting_results is None:
            raise DMPlotCreationError("No fitting results available for plotting energy map.")
        energy_map = self._model.get_energy_map()
        if energy_map is None:
            raise DMPlotCreationError("No energy map available to plot.")
        self._chosen_visualizers[0].plot_energy_map(energy_map)

    def plot_image(self):
        """Restore the visualizer image view (without energy-map overlay)."""
        self._chosen_visualizers[0].plot_image()

