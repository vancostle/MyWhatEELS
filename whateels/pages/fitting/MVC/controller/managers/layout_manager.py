import panel as pn
from typing import TYPE_CHECKING
from collections.abc import Mapping

from whateels.errors.dm.data import DMPlotCreationError
from whateels.helpers.constants import HTML_ROOT
from ..visualizer_factory import VisualizerFactory
from whateels.state import CacheManager
from ...view.components.component_item_view import ComponentItemView
from ...view.plots.nlls_multifit_results_plot import NLLSMultifitResultsPlot
from ...view.plots.nlls_derived_results_plot import NLLSDerivedResultsPlot

if TYPE_CHECKING:
    from ...view import FittingView
    from ...model import FittingModel
    from ...controller import FittingController
    from xarray import Dataset


class _StableAdditiveColumn(pn.Column):
    """Keep the scroll viewport stable while direct children are appended.

    Panel normally infers ``min_height`` by summing fixed-height children every
    time ``objects`` changes.  That is useful for ordinary columns, but it makes
    a scroll viewport grow and invalidates every responsive Bokeh plot already
    mounted inside it.  This column deliberately keeps the explicit viewport
    sizing mode and lets CSS overflow handle the additive content height.
    """

    def _compute_sizing_mode(self, children, props):
        computed = super()._compute_sizing_mode(children, props)
        computed.pop("min_height", None)
        if self.sizing_mode is not None:
            computed["sizing_mode"] = self.sizing_mode
        return computed


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

    _ADDITIVE_STACK_STYLES = {
        "box-sizing": "border-box",
        "display": "flex",
        "flex-direction": "column",
        "height": "100%",
        "min-height": "0",
        "min-width": "0",
        "overflow-x": "hidden",
        # Keep the scrollbar lane present before the first overflow. Responsive
        # Bokeh plots retain the same width when analyses are prepended.
        "overflow-y": "scroll",
        "scrollbar-gutter": "stable",
        "padding": "0 8px 8px 8px",
        "align-items": "stretch",
        "position": "relative",
        # Adding a result at the visual top must not let the browser's scroll
        # anchoring move the already visible Bokeh canvases.
        "overflow-anchor": "none",
    }
    _DERIVED_VISUAL_ORDER_BASE = -2_000_000
    _NLLS_VISUAL_ORDER_BASE = -1_000_000
    _SOURCE_VISUAL_ORDER = 0
    
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
        self._plot_stacks: list[pn.Column] = []
        self._nlls_result_views: list[list[NLLSMultifitResultsPlot]] = []
        self._nlls_derived_views: list[list[NLLSDerivedResultsPlot]] = []
        self._nlls_run_sequence = 0
        self._nlls_analysis_sequence = 0
        
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
            self.clear_nlls_result_plots()
            self._chosen_visualizers.clear()
            self._plot_stacks.clear()
            self._nlls_result_views.clear()
            self._nlls_derived_views.clear()
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
                base_plot_wrapper = pn.Column(
                    visualizer_plots,
                    sizing_mode=STRETCH_BOTH,
                    min_height=600,
                    margin=0,
                    css_classes=["fitting-source-plots"],
                    styles={
                        "box-sizing": "border-box",
                        "flex": "0 0 100%",
                        "height": "100%",
                        "max-height": "100%",
                        "min-width": "0",
                        # The Bokeh axes/colorbar are child panels of the figure.
                        # Paint containment clipped them when the responsive
                        # frame needed a few extra pixels after a stack move.
                        "contain": "layout",
                        "isolation": "isolate",
                        "order": str(self._SOURCE_VISUAL_ORDER),
                    },
                )
                # Keep one append-only physical child list. CSS order changes
                # presentation without replacing live plot models/callbacks.
                plot_stack = _StableAdditiveColumn(
                    base_plot_wrapper,
                    sizing_mode=STRETCH_BOTH,
                    min_height=0,
                    margin=0,
                    scroll=True,
                    css_classes=["fitting-additive-plots"],
                    styles=dict(self._ADDITIVE_STACK_STYLES),
                )
                self._plot_stacks.append(plot_stack)
                self._nlls_result_views.append([])
                self._nlls_derived_views.append([])
                self._plots_tab.append((image_name, plot_stack))
                
                self._all_dataset_info.append(chosen_visualizer.create_dataset_info())
                
            self._plots_tab.param.watch(self._on_tab_with_visualizers_change, ACTIVE, onlychanged=False)
            app_state.plot_dataset = app_state.all_datasets[app_state.selected_tab_index_dataset]  # Set initial dataset to plot based on selected tab index
            
            # Update UI
            self._controller.base_layout.update_main(self._plots_tab)
            self.remove_dataset_info_from_sidebar()
            self.add_component_to_sidebar_layout(self._all_dataset_info[0])

        except Exception as e:
            raise DMPlotCreationError(e)

    @property
    def nlls_result_views(self) -> tuple[NLLSMultifitResultsPlot, ...]:
        """Return all currently rendered NLLS runs in visual top-to-bottom order."""
        return tuple(
            view
            for views in self._nlls_result_views
            for view in reversed(views)
        )

    def add_nlls_result_plot(
        self,
        results,
        *,
        dataset_index: int | None = None,
    ) -> NLLSMultifitResultsPlot:
        """Publish a new run without remounting older results/source plots."""
        if not self._plot_stacks:
            raise DMPlotCreationError("No Fitting plot stack is available for NLLS results.")
        if dataset_index is None:
            dataset_index = int(getattr(self._plots_tab, "active", 0) or 0)
        if not 0 <= int(dataset_index) < len(self._plot_stacks):
            raise DMPlotCreationError(
                f"Invalid Fitting dataset index for NLLS results: {dataset_index}"
            )

        self._nlls_run_sequence += 1
        result_view = NLLSMultifitResultsPlot(
            results,
            run_number=self._nlls_run_sequence,
        )
        index = int(dataset_index)
        self._nlls_result_views[index].append(result_view)
        controls = self._multifit_controls()
        try:
            # Apply shared state before the view obtains a Bokeh model.  The
            # append is then the only document mutation seen by existing plots.
            if controls is not None:
                controls.register(result_view)
            self._append_additive_view(
                self._plot_stacks[index],
                result_view,
                order=self._NLLS_VISUAL_ORDER_BASE - self._nlls_run_sequence,
            )
        except Exception:
            if controls is not None:
                controls.unregister(result_view)
            self._nlls_result_views[index].remove(result_view)
            result_view.cleanup()
            raise
        return result_view

    def add_nlls_derived_result_plot(
        self,
        results,
        *,
        dataset_index: int | None = None,
    ) -> NLLSDerivedResultsPlot:
        """Publish a derived map without remounting runs/source plots."""
        if not self._plot_stacks:
            raise DMPlotCreationError("No Fitting plot stack is available for NLLS analysis.")
        if dataset_index is None:
            dataset_index = int(getattr(self._plots_tab, "active", 0) or 0)
        index = int(dataset_index)
        if not 0 <= index < len(self._plot_stacks):
            raise DMPlotCreationError(f"Invalid Fitting dataset index: {dataset_index}")
        self._nlls_analysis_sequence += 1
        view = NLLSDerivedResultsPlot(
            results,
            sequence=self._nlls_analysis_sequence,
        )
        self._nlls_derived_views[index].append(view)
        controls = self._multifit_controls()
        try:
            if controls is not None:
                controls.register_derived(view)
            self._append_additive_view(
                self._plot_stacks[index],
                view,
                order=(
                    self._DERIVED_VISUAL_ORDER_BASE
                    - self._nlls_analysis_sequence
                ),
            )
        except Exception:
            if controls is not None:
                controls.unregister_derived(view)
            self._nlls_derived_views[index].remove(view)
            view.cleanup()
            raise
        return view

    @staticmethod
    def _append_additive_view(
        stack: pn.Column,
        view: pn.viewable.Viewable,
        *,
        order: int,
    ) -> None:
        """Append physically while presenting the new fixed block first."""
        view.styles = {**(view.styles or {}), "order": str(int(order))}
        stack.append(view)
        stack.scroll_position = 0

    def _multifit_controls(self):
        """Return the Results-tab block that hosts the run controls, if it exists."""
        return getattr(self._view, "elemental_multifit_controls", None)

    def clear_nlls_result_plots(self, dataset_index: int | None = None) -> None:
        """Remove interactive run views and release their HoloViews streams."""
        if dataset_index is None:
            indices = range(len(self._nlls_result_views))
        elif 0 <= int(dataset_index) < len(self._nlls_result_views):
            indices = (int(dataset_index),)
        else:
            return
        controls = self._multifit_controls()
        for index in indices:
            plot_stack = (
                self._plot_stacks[index]
                if index < len(self._plot_stacks)
                else None
            )
            for result_view in tuple(self._nlls_result_views[index]):
                if plot_stack is not None and result_view in plot_stack.objects:
                    plot_stack.remove(result_view)
                if controls is not None:
                    controls.unregister(result_view)
                result_view.cleanup()
            self._nlls_result_views[index].clear()
            if index < len(self._nlls_derived_views):
                for derived_view in tuple(self._nlls_derived_views[index]):
                    if plot_stack is not None and derived_view in plot_stack.objects:
                        plot_stack.remove(derived_view)
                    if controls is not None:
                        controls.unregister_derived(derived_view)
                    derived_view.cleanup()
                self._nlls_derived_views[index].clear()
            if plot_stack is not None:
                plot_stack.scroll_position = 0
        if dataset_index is None:
            self._nlls_run_sequence = 0
            self._nlls_analysis_sequence = 0
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

    def clear_component_inputs_from_sidebar(self) -> None:
        """Remove all component editor cards from the right sidebar."""

        to_remove = [
            item for item in list(self._view.right_sidebar)
            if isinstance(item, ComponentItemView)
        ]
        for item in to_remove:
            if item in self._view.right_sidebar:
                self._view.right_sidebar.remove(item)

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
            # Use the NaN-stripped axis stored during fit_reference() so x and y_fit
            # have the same length. Fall back to the full axis only when unavailable.
            if hasattr(self._model, '_fit_eloss') and self._model._fit_eloss is not None:
                x_plot = self._model._fit_eloss
            else:
                x_plot = state.plot_dataset.coords['Eloss'].values
            self._chosen_visualizers[0].update_plot()
            self._chosen_visualizers[0].plot_fitting(
                x_plot,
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

    def reset_for_data_source_change(self):
        """Hard-reset derived fitting outputs after switching raw/preprocessed source."""
        self.remove_best_fit_component_from_sidebar()
        self.clear_nlls_result_plots()
        if not self._chosen_visualizers:
            return

        visualizer = self._chosen_visualizers[0]
        if hasattr(visualizer, 'reset_for_data_source_change'):
            visualizer.reset_for_data_source_change()
        else:
            visualizer.plot_image()
            visualizer.update_plot()

