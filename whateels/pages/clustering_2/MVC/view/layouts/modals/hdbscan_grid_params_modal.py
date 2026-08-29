import panel as pn, param

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class _HDBSCANGridParams(param.Parameterized):
    min_cluster_size_min = param.Integer(
        default=100,
        label="min min_cluster_size",
        doc="Minimum min_cluster_size for HDBSCAN grid evaluation."
    )
    min_cluster_size_max = param.Integer(
        default=900,
        label="max min_cluster_size",
        doc="Maximum min_cluster_size for HDBSCAN grid evaluation."
    )
    min_samples_min = param.Integer(
        default=1,
        label="min min_samples",
        doc="Minimum min_samples for HDBSCAN grid evaluation."
    )
    min_samples_max = param.Integer(
        default=8,
        label="max min_samples",
        doc="Maximum min_samples for HDBSCAN grid evaluation."
    )
    step = param.Integer(
        default=100,
        label="step",
        doc="Step used to sweep min_cluster_size in HDBSCAN grid evaluation."
    )


class HDBSCANGridParamsModal(pn.Column):

    _STRETCH_WIDTH = 'stretch_width'

    def __init__(
        self,
        custom_page: "GeneralPageTemplate",
        title="Configure HDBSCAN grid for evaluation",
        on_close=None,
        initial_values: dict | None = None,
        **kwargs
    ):
        self._params = _HDBSCANGridParams()

        if initial_values:
            self._params.min_cluster_size_min = int(
                initial_values.get("min_cluster_size_min", self._params.min_cluster_size_min)
            )
            self._params.min_cluster_size_max = int(
                initial_values.get("min_cluster_size_max", self._params.min_cluster_size_max)
            )
            self._params.min_samples_min = int(
                initial_values.get("min_samples_min", self._params.min_samples_min)
            )
            self._params.min_samples_max = int(
                initial_values.get("min_samples_max", self._params.min_samples_max)
            )
            self._params.step = int(initial_values.get("step", self._params.step))

        self._custom_page = custom_page
        self._on_close = on_close

        min_cluster_size_min_input = self._create_positive_int_input(
            name=type(self._params).param.min_cluster_size_min.label,
            value=self._params.min_cluster_size_min,
            assign=lambda v: setattr(self._params, "min_cluster_size_min", v),
        )
        min_cluster_size_max_input = self._create_positive_int_input(
            name=type(self._params).param.min_cluster_size_max.label,
            value=self._params.min_cluster_size_max,
            assign=lambda v: setattr(self._params, "min_cluster_size_max", v),
        )
        min_samples_min_input = self._create_positive_int_input(
            name=type(self._params).param.min_samples_min.label,
            value=self._params.min_samples_min,
            assign=lambda v: setattr(self._params, "min_samples_min", v),
        )
        min_samples_max_input = self._create_positive_int_input(
            name=type(self._params).param.min_samples_max.label,
            value=self._params.min_samples_max,
            assign=lambda v: setattr(self._params, "min_samples_max", v),
        )
        step_input = self._create_step_input()

        close_button = pn.widgets.Button(
            name="Save & Close",
            button_type="success",
            sizing_mode="stretch_width",
            margin=0,
        )
        close_button.on_click(self._close)

        super().__init__(
            pn.pane.Markdown(f"## {title}", margin=0, styles={"padding": "0"}),
            pn.Spacer(height=10),
            pn.GridBox(
                min_cluster_size_min_input,
                min_cluster_size_max_input,
                min_samples_min_input,
                min_samples_max_input,
                ncols=2,
                sizing_mode="stretch_width",
                styles={"gap": "10px"},
            ),
            pn.Spacer(height=10),
            step_input,
            pn.Spacer(height=10),
            close_button,
            **kwargs,
        )

    def _close(self, event):
        params = self._get_params()
        if self._on_close:
            self._on_close(params)
        self.visible = False
        self._custom_page.close_modal()

    def _create_positive_int_input(self, name: str, value: int, assign) -> pn.widgets.IntInput:
        widget = pn.widgets.IntInput(
            name=name,
            value=value,
            step=1,
            sizing_mode=self._STRETCH_WIDTH,
        )

        def validate(event):
            new_value = event.new
            try:
                int_value = int(new_value)
                if int_value >= 1:
                    assign(int_value)
                else:
                    raise ValueError
            except ValueError:
                widget.value = event.old

        widget.param.watch(validate, 'value')
        return widget

    def _create_step_input(self) -> pn.widgets.IntInput:
        step = pn.widgets.IntInput(
            name=type(self._params).param.step.label,
            value=self._params.step,
            step=1,
            sizing_mode=self._STRETCH_WIDTH,
        )

        def validate_step(event):
            value = event.new
            try:
                int_value = int(value)
                if int_value >= 1:
                    self._params.step = int_value
                else:
                    raise ValueError
            except ValueError:
                step.value = event.old

        step.param.watch(validate_step, 'value')
        return step

    def _get_params(self) -> dict:
        return {
            "min_cluster_size_min": self._params.min_cluster_size_min,
            "min_cluster_size_max": self._params.min_cluster_size_max,
            "min_samples_min": self._params.min_samples_min,
            "min_samples_max": self._params.min_samples_max,
            "step": self._params.step,
        }
