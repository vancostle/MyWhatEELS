import panel as pn, param

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.templates import GeneralPageTemplate


class _SVMTrainSettingsParams(param.Parameterized):
    kernel = param.String(
        default="rbf",
        label="kernel",
        doc="Kernel selected in the SVM section.",
    )
    test_size = param.Number(
        default=0.25,
        label="test_size",
        doc="Fraction of the dataset reserved for test split.",
    )
    probability = param.Boolean(
        default=False,
        label="Probability",
        doc="Whether to enable probability estimates in SVM.",
    )
    gamma = param.String(
        default="scale",
        label="gamma",
        doc="Kernel coefficient for 'rbf', 'poly' and 'sigmoid'.",
    )
    coef0 = param.Number(
        default=0.0,
        label="coef0",
        doc="Independent term used by 'poly' and 'sigmoid'.",
    )
    degree = param.Integer(
        default=3,
        label="degree",
        doc="Degree used only by the 'poly' kernel.",
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
            self._params.kernel = str(initial_values.get("kernel", self._params.kernel))
            self._params.test_size = float(initial_values.get("test_size", self._params.test_size))
            self._params.probability = bool(initial_values.get("probability", self._params.probability))
            self._params.gamma = str(initial_values.get("gamma", self._params.gamma))
            self._params.coef0 = float(initial_values.get("coef0", self._params.coef0))
            self._params.degree = int(initial_values.get("degree", self._params.degree))

        self._custom_page = custom_page
        self._on_close = on_close

        test_size_input = self._create_test_size_input()
        probability_input = self._create_probability_input()
        self._gamma_input = self._create_gamma_input()
        self._coef0_input = self._create_coef0_input()
        self._degree_input = self._create_degree_input()
        self._advanced_container = pn.Column(sizing_mode=self._STRETCH_WIDTH, styles={"gap": "10px"})
        self._refresh_kernel_fields()

        close_button = pn.widgets.Button(
            name="Save & Close",
            button_type="success",
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
                self._advanced_container,
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

    def _create_gamma_input(self) -> pn.widgets.TextInput:
        gamma = pn.widgets.TextInput(
            name=type(self._params).param.gamma.label,
            value=str(self._params.gamma),
            placeholder="scale | auto | float",
            sizing_mode=self._STRETCH_WIDTH,
        )

        def on_gamma_change(event):
            value = str(event.new).strip().lower()
            if value in {"", "scale", "auto"}:
                self._params.gamma = "scale" if value == "" else value
                gamma.value = self._params.gamma
                return

            try:
                parsed = float(value)
                if parsed <= 0:
                    raise ValueError
                self._params.gamma = str(parsed)
                gamma.value = self._params.gamma
            except Exception:
                gamma.value = event.old

        gamma.param.watch(on_gamma_change, "value")
        return gamma

    def _create_coef0_input(self) -> pn.widgets.FloatInput:
        coef0 = pn.widgets.FloatInput(
            name=type(self._params).param.coef0.label,
            value=float(self._params.coef0),
            step=0.1,
            sizing_mode=self._STRETCH_WIDTH,
        )

        def on_coef0_change(event):
            try:
                self._params.coef0 = float(event.new)
            except Exception:
                coef0.value = event.old

        coef0.param.watch(on_coef0_change, "value")
        return coef0

    def _create_degree_input(self) -> pn.widgets.IntInput:
        degree = pn.widgets.IntInput(
            name=type(self._params).param.degree.label,
            value=int(self._params.degree),
            step=1,
            start=1,
            sizing_mode=self._STRETCH_WIDTH,
        )

        def on_degree_change(event):
            try:
                value = int(event.new)
                if value < 1:
                    raise ValueError
                self._params.degree = value
            except Exception:
                degree.value = event.old

        degree.param.watch(on_degree_change, "value")
        return degree

    def _refresh_kernel_fields(self) -> None:
        kernel = str(self._params.kernel).lower()
        advanced_fields = []

        if kernel in {"rbf", "poly", "sigmoid"}:
            advanced_fields.append(self._gamma_input)
        if kernel in {"poly", "sigmoid"}:
            advanced_fields.append(self._coef0_input)
        if kernel == "poly":
            advanced_fields.append(self._degree_input)

        self._advanced_container.objects = advanced_fields

    def set_selected_kernel(self, kernel: str) -> None:
        self._params.kernel = str(kernel).lower()
        self._refresh_kernel_fields()

    def _close(self, event):
        params = self._get_params()
        if self._on_close:
            self._on_close(params)
        self.visible = False
        self._custom_page.close_modal()

    def _get_params(self) -> dict:
        return {
            "kernel": str(self._params.kernel),
            "test_size": float(self._params.test_size),
            "probability": bool(self._params.probability),
            "gamma": str(self._params.gamma),
            "coef0": float(self._params.coef0),
            "degree": int(self._params.degree),
        }
