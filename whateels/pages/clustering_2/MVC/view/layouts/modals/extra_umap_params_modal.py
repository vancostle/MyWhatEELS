
import panel as pn, param

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate
    
class _ExtraUmapParams(param.Parameterized):
    n_components = param.Integer(
        default=2,
        label="n_components",
        doc="Number of components for UMAP embedding."
    )
    metric = param.String(
        default="euclidean",
        label="metric",
        doc="Distance metric for UMAP."
    )
    random_state = param.Integer(
        default=2,
        label="random_state",
        doc="Random state for UMAP."
    )

class ExtraUmapParamsModal(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(
        self,
        custom_page : "GeneralPageTemplate",
        title="Title",
        on_close=None,
        **kwargs
    ):
        self._params = _ExtraUmapParams()
        
        self._custom_page = custom_page
        self._on_close = on_close
    
        n_components_input : pn.widgets.IntInput = self._create_n_components_input()
        metric_input : pn.widgets.Select = self._create_metric_input()
        random_state_input : pn.widgets.IntInput = self._create_random_state_input()
        
        close_button = pn.widgets.Button(
            name="Save & Close",
            button_type="success",
            sizing_mode="stretch_width",
            margin=0
        )

        close_button.on_click(self._close)
        
        super().__init__(
            pn.pane.Markdown(f"## {title}", margin=0, styles={"padding" : "0"}),
            pn.Spacer(height=10),
            pn.Column(
                n_components_input,
                metric_input,
                random_state_input,
                sizing_mode="stretch_both",
                styles={"gap": "10px"}
            ),
            pn.Spacer(height=10),
            close_button,
            **kwargs
        )
        
    def _close(self, event):
        params = self._get_params()
        if self._on_close:
            self._on_close(params)
        self.visible = False
        self._custom_page.close_modal()
        
    def _create_n_components_input(self) -> pn.widgets.IntInput:
        n_components = pn.widgets.IntInput(
            name=type(self._params).param.n_components.label,
            value=type(self._params).param.n_components.default,
            step=1,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        def validate_n_components(event):
            value = event.new
            try:
                int_value = int(value)
                if int_value >= 1:
                    self._params.n_components = int_value
                else:
                    raise ValueError
            except ValueError:
                n_components.value = event.old
        
        n_components.param.watch(validate_n_components, 'value')
        
        return n_components
    
    def _create_metric_input(self) -> pn.widgets.Select:
        metric = pn.widgets.Select(
            name=type(self._params).param.metric.label,
            options=["euclidean", "manhattan", "chebyshev", "minkowski", "cosine"],
            value=type(self._params).param.metric.default,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        def on_metric_change(event):
            value = event.new
            self._params.metric = value
        
        metric.param.watch(on_metric_change, 'value')
        
        return metric
    
    def _create_random_state_input(self) -> pn.widgets.IntInput:
        random_state = pn.widgets.IntInput(
            name=type(self._params).param.random_state.label,
            value=type(self._params).param.random_state.default,
            step=1,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        def validate_random_state(event):
            value = event.new
            try:
                int_value = int(value)
                if int_value >= 0:
                    self._params.random_state = int_value
                else:
                    raise ValueError
            except ValueError:
                random_state.value = event.old
                
        random_state.param.watch(validate_random_state, 'value')
        
        return random_state
    
    def _get_params(self) -> dict:
        return {
            "n_components": self._params.n_components,
            "metric": self._params.metric,
            "random_state": self._params.random_state
        }
