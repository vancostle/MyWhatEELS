import panel as pn, param

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class _SVMSettingsParams(param.Parameterized):
    min_c = param.Number(
        default=0.1,
        label="min C",
        doc="Minimum C used for SVM evaluation grid.",
    )
    max_c = param.Number(
        default=10.0,
        label="max C",
        doc="Maximum C used for SVM evaluation grid.",
    )


class SVMSettingsModal(pn.Column):

    _STRETCH_WIDTH = "stretch_width"

    def __init__(
        self,
        custom_page: "GeneralPageTemplate",
        title="Configure SVM settings",
        on_close=None,
        initial_values: dict | None = None,
        **kwargs,
    ):
        self._params = _SVMSettingsParams()

        if initial_values:
            self._params.min_c = float(initial_values.get("min_c", self._params.min_c))
            self._params.max_c = float(initial_values.get("max_c", self._params.max_c))

        self._custom_page = custom_page
        self._on_close = on_close

        min_c_input = self._create_float_input(
            name=type(self._params).param.min_c.label,
            value=self._params.min_c,
            assign=lambda v: setattr(self._params, "min_c", v),
        )
        max_c_input = self._create_float_input(
            name=type(self._params).param.max_c.label,
            value=self._params.max_c,
            assign=lambda v: setattr(self._params, "max_c", v),
        )

        close_button = pn.widgets.Button(
            name="Okay.",
            button_type="primary",
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
        )
        close_button.on_click(self._close)

        super().__init__(
            pn.pane.Markdown(f"## {title}", margin=0, styles={"padding": "0"}),
            pn.Spacer(height=10),
            pn.Row(
                min_c_input,
                max_c_input,
                sizing_mode=self._STRETCH_WIDTH,
            ),
            pn.Spacer(height=10),
            close_button,
            **kwargs,
        )

    def _create_float_input(self, name: str, value: float, assign) -> pn.widgets.FloatInput:
        widget = pn.widgets.FloatInput(
            name=name,
            value=float(value),
            step=0.1,
            sizing_mode=self._STRETCH_WIDTH,
        )

        def validate(event):
            try:
                assign(float(event.new))
            except Exception:
                widget.value = event.old

        widget.param.watch(validate, "value")
        return widget

    def _close(self, event):
        params = self._get_params()
        if self._on_close:
            self._on_close(params)
        self.visible = False
        self._custom_page.close_modal()

    def _get_params(self) -> dict:
        return {
            "min_c": float(self._params.min_c),
            "max_c": float(self._params.max_c),
        }