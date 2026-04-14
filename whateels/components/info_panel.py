import panel as pn

from whateels.helpers import CSS_ROOT, HTML_ROOT, LoadCSS

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
        
        # Spacing
        SPACER_HEIGHT_SMALL = 5
        SPACER_HEIGHT_MEDIUM = 10
        MARGIN_ZERO = 0

        # Optionally load metadata button HTML
        header_items = [pn.pane.HTML(DATASET_INFO_TITLE, sizing_mode=STRETCH_WIDTH, margin=MARGIN_ZERO)]
        if self._show_metadata_button:
            metadata_html_path = HTML_ROOT / HTML_FILE
            with open(metadata_html_path, READ_MODE, encoding=UTF_8) as f:
                metadata_button_html = f.read()
            metadata_button = pn.pane.HTML(metadata_button_html, margin=MARGIN_ZERO)
            header_items.append(metadata_button)
        header = pn.Row(
            *header_items,
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_HEADER_CLASS,
            margin=MARGIN_ZERO
        )
        
        # Dynamically generate info rows from _information_keys and _information_values
        info_rows = [
            pn.Row(
                pn.Row(
                    pn.pane.HTML(
                        str(f'{key}:'),
                        css_classes=["dataset-info-key"],
                    ),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.HTML(
                    str(value), 
                    css_classes=["dataset-info-value"]
                ),
                sizing_mode=STRETCH_WIDTH,
                margin=(0, 6, 0, 6)
            )
            for key, value in self._information.items()
        ]

        dataset_info = pn.Column(
            header,
            pn.Spacer(height=SPACER_HEIGHT_SMALL),
            *info_rows,
            pn.Spacer(height=SPACER_HEIGHT_MEDIUM),
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_CLASS
        )

        return dataset_info