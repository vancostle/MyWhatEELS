import panel as pn

class NoneDMFileUploadedPlaceholder(pn.Column):
    
    def __init__(
        self,
        **kwargs
    ):
        super().__init__(
            pn.pane.Markdown(
                "## Upload a .pkl file containing a previously computed UMAP embedding to begin.",
                align='center',
                styles={
                    'color': '#999',
                    'font-weight': '300',
                    'margin-top': '40px'
                }
            ),
            sizing_mode='stretch_both',
            align='center',
            styles={
                'display': 'flex',
                'justify-content': 'center',
                'align-items': 'center',
            },
            **kwargs
        )