import panel as pn

from whateels.helpers import HTML_ROOT

class InfoPanel(pn.Column):
    """ Creates a dataset information panel displaying key metadata attributes. """

    def __init__(
        self,
        title: str = "Dataset Information",
        link: str = "metadata-details",
        information: dict = {"No information available": "None"},
        show_metadata_button: bool = True,
        **params
    ):        
        # Load any provided CSS files (guard avoids duplicate ImportedStyleSheet models)
        if '/assets/css/info_panel.css' not in pn.config.css_files: # type: ignore
            pn.config.css_files.append('/assets/css/info_panel.css') # type: ignore

        self._title = title
        self._link = link
        self._information = information
        self._show_metadata_button = show_metadata_button

        super().__init__(
            self._create_layout(),
            **params
        )
        
    def _create_layout(self) -> pn.Column:
        """
        Create the dataset information layout.
        """
        # File and encoding constants
        HTML_FILE = 'metadata_info.html'
        READ_MODE = 'r'
        UTF_8 = 'utf-8'

        # Panel sizing modes
        STRETCH_WIDTH = "stretch_width"
        
        # CSS classes
        DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
        DATASET_INFO_CLASS = ["dataset-info", "animated"]
        
        # HTML content
        DATASET_INFO_TITLE = f"<span class=\"dataset-info-title\">{self._title}</span>"
        
        # Cabecera de la tarjeta: titulo a la izquierda y el boton circular a la derecha.
        header_items = [pn.pane.HTML(DATASET_INFO_TITLE, sizing_mode=STRETCH_WIDTH, margin=0)]
        if self._show_metadata_button:
            # El icono del boton se carga como HTML para conservar el aspecto exacto del diseno.
            metadata_html_path = HTML_ROOT / HTML_FILE
            with open(metadata_html_path, READ_MODE, encoding=UTF_8) as f:
                metadata_button_html = f.read()
            metadata_button = pn.pane.HTML(metadata_button_html, margin=0)
            header_items.append(metadata_button)
        header = pn.Row(
            *header_items,
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_HEADER_CLASS,
            margin=0,
        )
        
        # Cada fila puede ser texto plano o un widget compacto (como el input editable de Home).
        info_rows = [
            self._create_info_row(key, value, STRETCH_WIDTH)
            for key, value in self._information.items()
        ]

        dataset_info = pn.Column(
            header,
            pn.Column(
                *info_rows,
                sizing_mode=STRETCH_WIDTH,
                margin=0,
                css_classes=["dataset-info-row-wrapper"]
            ),
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_CLASS
        )

        return dataset_info

    def _create_info_row(self, key, value, sizing_mode: str) -> pn.Row:
        if isinstance(value, pn.widgets.TextInput):
            # Use widget.name as the unit suffix (e.g. "kV"), then clear it
            # so Panel doesn't render its own label above the input.
            suffix = value.name
            value.name = ""
            
            value.css_classes = ["dataset-info-editable-input"]
            value.stylesheets = ["""
                :host .bk-input {
                    margin-left: 1rem;
                    text-align: right;
                    height: 20px !important;
                    min-height: 20px;
                    font-size: 12px;
                    font-family: monospace;

                    border: 0 !important;
                    border-bottom: 1px solid transparent !important;
                    background: transparent !important;
                    box-shadow: none !important;
                    outline: none !important;
                    border-radius: 0 !important;
                    padding: 0 !important;
                    max-width: 65px !important;
                }
                :host .bk-input:is(:focus,:hover,:focus-visible) {
                    border-bottom: 1px solid #b63fb5 !important;
                }
                :host .bk-input-container {
                    justify-content: flex-end !important;
                }
            """]
            value.margin = (0, 0, 0, 0)
            
            value_component = pn.Row(
                value,
                pn.widgets.StaticText(value=suffix) if bool(suffix) else None,
                css_classes=["dataset-info-editable-input-wrapper"],
                margin=(0, 0, 0, 0),
                sizing_mode="stretch_width"
            )
        elif isinstance(value, pn.viewable.Viewable):
            value_component = value
        else:
            value_component = pn.pane.HTML(
                str(value),
                css_classes=["dataset-info-value"],
                margin=(0, 0, 0, 0)
            )

        return pn.Row(
            pn.pane.HTML(
                str(f'{key}:'),
                css_classes=["dataset-info-key"],
                margin=(0, 0, 0, 0),
            ),
            value_component,
            sizing_mode=sizing_mode,
            margin=0,
            css_classes=["dataset-info-row"]
        )
