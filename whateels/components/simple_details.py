import panel as pn

class SimpleDetails(pn.Column):
    
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(
        self, 
        title: str, 
        content: pn.Column,
        expanded: bool = False,
        button_type_on_expand: str = 'success',
        button_type_on_collapse: str = 'primary',
        **params
    ) -> None:
        
        self._title = title

        self._button_header = pn.widgets.Button(
            name=str("\u25B2 " if expanded else "\u25BC ") + title,
            button_type=button_type_on_expand if expanded else button_type_on_collapse,
            on_click=lambda _: self.toggle(),
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
        )
                
        self._content = pn.Column(
            content,
            sizing_mode=self._STRETCH_WIDTH,
            styles={
                'padding': '10px',
                'transition': 'height 0.3s ease',
            },
            visible=expanded
        )
        
        layout = pn.Column(
            self._button_header,
            self._content,
            sizing_mode=self._STRETCH_BOTH
        )
        
        super().__init__(
            layout,
            **params,
            styles={
                'border-radius': '4px',
                'box-shadow': '0 0 5px #d8d8d8',
                'background-color': '#f7f7f7',
                'overflow': 'visible',
            }
        )
        
    def toggle(self):
        """Toggle the visibility of the details content."""
        if isinstance(self._content.visible, bool):
            self._content.visible = not self._content.visible
        else:
            self._content.visible = True
            
        self._button_header.name = str("\u25B2 " if self._content.visible else "\u25BC ") + self._title
        self._button_header.button_type = (
            'success' if self._content.visible else 'primary'
        )
