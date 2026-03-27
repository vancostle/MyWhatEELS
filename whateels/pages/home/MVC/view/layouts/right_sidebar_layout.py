import panel as pn
from whateels.components import SimpleDetails

class HomePageRightSidebar(pn.Column):
    """
    Manages the right sidebar layout for the Home Page View, displaying dataset information.
    """
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model, **kwargs):
        self._model = model

        # Range slider state — populated externally via set_range_slider()
        self._range_slider = None
        self._range_slider_value_watcher = None
        self._range_slider_visible_watcher = None

        # Fitting callback — populated externally via set_fitting_callback()
        self._fitting_callback = None
        self._fitting_switch_watcher = None

        fitting_label = pn.pane.Markdown(
            "## Fitting",
            margin=0,
            styles={'padding' : '0px', 'height': '30px', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
        )
        
        self._fitting_switch = pn.widgets.Switch(
            name="Fitting",
            value=False,
            css_classes=["background-fitting-switch"],
            styles={'height' : '30px', 'max-height' : '30px', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'margin': '0px'}
        )
        
        fitting_switch_container = pn.Row(
            fitting_label,
            self._fitting_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-fitting-container"],
            margin=(0, 0, 8, 0),
            styles={'display': 'flex', 'align-items': 'center', 'justify-content': 'center', 'padding': '0px'}
        )

        # Always-visible container for the range slider
        # self._range_slider_container = pn.Column(
        #     sizing_mode=self._STRETCH_WIDTH,
        #     visible=True,
        # )

        self._multifit_link_pane = pn.pane.HTML(
            self._build_multifit_html(None),
            sizing_mode=self._STRETCH_WIDTH,
            margin=(8, 0, 0, 0),
        )
        
        self._slider_placeholder = None  # Will hold the slider widget directly
        self._simple_details_content = pn.Column(
            fitting_switch_container,
            # slider will be inserted here
            self._multifit_link_pane,
            sizing_mode=self._STRETCH_WIDTH
        )
        fitting_simple_details = SimpleDetails(
            title="Fitting Information",
            content=self._simple_details_content,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        super().__init__(
            pn.Column(
                fitting_simple_details,
                sizing_mode=self._STRETCH_WIDTH,
            ),
            **kwargs
        )
        
    def _build_multifit_html(self, url: str | None) -> str:
        # Only enable the link if fitting is ON and url is not None
        if url and self._fitting_switch.value:
            return (
                f'<a href="{url}" target="_blank" '
                f'class="btn btn-warning" '
                f'style="display:block;text-align:center;width:100%;box-sizing:border-box;">'
                f'Open Multifit</a>'
            )
        return (
            '<a class="btn btn-warning disabled" aria-disabled="true" '
            'style="display:block;text-align:center;width:100%;box-sizing:border-box;opacity:0.5;pointer-events:none;">'
            'Open Multifit</a>'
        )

    def set_fitting_callback(self, callback) -> None:
        """Wire a plot's set_fitting_active method to the fitting switch.
        Resets the switch to OFF (False) to match the plot's initial state.
        """
        if self._fitting_switch_watcher is not None:
            try:
                self._fitting_switch.param.unwatch(self._fitting_switch_watcher)
            except Exception:
                pass
        self._fitting_callback = callback
        self._fitting_switch_watcher = None

        # Reset switch state to OFF when connecting a new plot
        self._fitting_switch.value = False

        if callback is None:
            return
        self._fitting_switch_watcher = self._fitting_switch.param.watch(
            self._on_fitting_switch_changed, 'value'
        )
        # If a range slider is already set, update its enabled state
        if self._range_slider is not None:
            self._update_range_slider_enabled()

    def _on_fitting_switch_changed(self, event) -> None:
        """Forward switch toggle to the active plot and enable/disable range slider and multifit link."""
        if callable(self._fitting_callback):
            self._fitting_callback(event.new)
        self._update_range_slider_enabled()
        self._update_multifit_url()

    def set_range_slider(self, range_slider : pn.widgets.EditableRangeSlider) -> None:
        """Wire an EditableRangeSlider from the active plot into the fitting SimpleDetails.
        The sidebar watches it directly to compute the multifit URL without cross-file callbacks.
        The slider is always visible and only disabled/enabled by the fitting switch.
        """
        # Unwatch the previous slider if any
        if self._range_slider is not None:
            try:
                if self._range_slider_value_watcher is not None:
                    self._range_slider.param.unwatch(self._range_slider_value_watcher)
            except Exception:
                pass

        self._range_slider = range_slider
        self._range_slider_value_watcher = None

        # Remove old slider if present
        if self._slider_placeholder is not None and self._slider_placeholder in self._simple_details_content:
            self._simple_details_content.remove(self._slider_placeholder)
        self._slider_placeholder = None

        if range_slider is None:
            self._multifit_link_pane.object = self._build_multifit_html(None)
            return

        # Insert the slider directly before the multifit link
        self._slider_placeholder = range_slider
        self._simple_details_content.insert(-1, range_slider)

        # Watch value changes → update URL
        self._range_slider_value_watcher = range_slider.param.watch(
            self._update_multifit_url, 'value'
        )

        self._update_range_slider_enabled()
        self._update_multifit_url()

    def _update_range_slider_enabled(self):
        """Enable or disable the range slider based on the fitting switch."""
        if self._range_slider is not None:
            self._range_slider.disabled = not self._fitting_switch.value

    # No longer needed: range slider is always visible

    def _update_multifit_url(self, *args) -> None:
        """Recompute the multifit URL from the current range slider values and update the link."""
        rs = self._range_slider
        if rs is None:
            self._multifit_link_pane.object = self._build_multifit_html(None)
            return
        min_val, max_val = rs.value
        location = getattr(pn.state, 'location', None)
        port = getattr(location, 'port', 5006)
        hostname = getattr(location, 'hostname', 'localhost')
        url = f"http://{hostname}:{port}/multifit-details?values={min_val},{max_val}"
        self._multifit_link_pane.object = self._build_multifit_html(url)

    @property
    def fitting_switch(self) -> pn.widgets.Switch:
        """Switch widget to toggle fitting mode."""
        return self._fitting_switch