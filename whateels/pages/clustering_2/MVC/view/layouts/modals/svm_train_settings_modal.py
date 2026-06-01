import panel as pn, param

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class _SVMTrainSettingsParams(param.Parameterized):
    test_size = param.Number(
        default=0.25,
        label="test_size",
        doc="Fraction of the dataset reserved for test split.",
    )
    probability = param.Boolean(
        default=False,
        label="Probality",
        doc="Whether to enable probability estimates in SVM.",
    )


class SVMTrainSettingsModal(pn.Column):

    _STRETCH_WIDTH = "stretch_width"

    def __init__(
        self,
        custom_page: "GeneralPageTemplate",
        title="Configure SVM train settings",
        on_close=None,
        initial_values: dict | None = None,
        **kwargs,
    ):
        self._params = _SVMTrainSettingsParams()

        if initial_values:
            self._params.test_size = float(initial_values.get("test_size", self._params.test_size))
            self._params.probability = bool(initial_values.get("probability", self._params.probability))

        self._custom_page = custom_page
        self._on_close = on_close

        test_size_input = self._create_test_size_input()
        probability_input = self._create_probability_input()

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
            pn.Column(
                test_size_input,
                probability_input,
                sizing_mode=self._STRETCH_WIDTH,
                styles={"gap": "10px"},
            ),
            pn.Spacer(height=10),
            close_button,
            **kwargs,
        )

    def _create_test_size_input(self) -> pn.widgets.FloatInput:
        test_size = pn.widgets.FloatInput(
            name=type(self._params).param.test_size.label,
            value=float(self._params.test_size),
            step=0.01,
            start=0.01,
            end=1.0,
            sizing_mode=self._STRETCH_WIDTH,
        )

        def validate_test_size(event):
            try:
                value = float(event.new)
                if 0 < value <= 1:
                    self._params.test_size = value
                else:
                    raise ValueError
            except Exception:
                test_size.value = event.old

        test_size.param.watch(validate_test_size, "value")
        return test_size

    def _create_probability_input(self) -> pn.widgets.Select:
        probability = pn.widgets.Select(
            name=type(self._params).param.probability.label,
            options=[True, False],
            value=bool(self._params.probability),
            sizing_mode=self._STRETCH_WIDTH,
        )

        def on_probability_change(event):
            self._params.probability = bool(event.new)

        probability.param.watch(on_probability_change, "value")
        return probability

    def _close(self, event):
        params = self._get_params()
        if self._on_close:
            self._on_close(params)
        self.visible = False
        self._custom_page.close_modal()

    def _get_params(self) -> dict:
        return {
            "test_size": float(self._params.test_size),
            "probability": bool(self._params.probability),
        }