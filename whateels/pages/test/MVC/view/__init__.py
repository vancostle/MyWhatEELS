import panel as pn

from whateels.components import ResizableColumns

class View:
    
    def __init__(self):
        resizable_columns = ResizableColumns(
            left_column=pn.Column(
                "# LEFT Area", "This is the left content area.",
                styles={'border': '2px solid green', 'padding': '0px', 'border-radius': '5px'}
            ),
            right_column=pn.Column(
                "# RIGHT Area", "This is the right content area.",
                styles={'border': '2px solid orange', 'padding': '10px', 'border-radius': '5px'}
            ),
            sizing_mode='stretch_both',
        )
        self._main_container_layout = pn.Column(resizable_columns)
        self._sidebar_layout = pn.Column()
        
    @property
    def main(self):
        return self._main_container_layout
    
    @property
    def sidebar(self):
        return self._sidebar_layout
