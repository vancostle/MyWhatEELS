import panel as pn


class SVMTrainingPlaceholder(pn.Column):
    """Loading placeholder shown while SVM training is running."""

    def __init__(self, message: str = "Training SVM model...", details: str = "", **kwargs):
        spinner = pn.indicators.LoadingSpinner(
            value=True,
            size=50,
            color="success",
        )

        content = [
            pn.Row(
                spinner,
                sizing_mode="stretch_width",
                margin=0,
                styles={"justify-content": "center"},
            ),
            pn.pane.Markdown(
                f"### {message}",
                align="center",
                margin=0,
                styles={"text-align": "center"},
            ),
        ]

        if details:
            content.append(
                pn.pane.Markdown(
                    details,
                    align="center",
                    margin=0,
                    styles={"text-align": "center", "opacity": "0.8"},
                )
            )

        super().__init__(
            *content,
            align="center",
            css_classes=["umap-embedding-placeholder", "animated-in"],
            styles={
                "border-radius": "5px",
                "display": "flex",
                "flex-direction": "column",
                "justify-content": "center",
                "align-items": "center",
                "box-sizing": "border-box",
                "height": "100%",
                "min-height": "220px",
            },
            **kwargs,
        )
